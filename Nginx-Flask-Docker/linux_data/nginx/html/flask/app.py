"""
### app.py

nginx から `/` 以下をリバースプロキシされる Flask アプリ。
メモリ使用量(ゲージ)とCPU使用率(ゲージ)を表示する。

| パス | メソッド | 説明 |
| --- | --- | --- |
| `/` | GET | トップページ(`templates/index.html`)。ゲージの初回描画を含む |
| `/partials/gauges` | GET | ゲージ部分のHTML断片(`static/js/index.js` が定期的に取得して差し替える) |
| `/api/health` | GET | ヘルスチェック(JSON) |
| `/api/echo` | POST | 受け取った JSON をそのまま返す |
| `/static/*` | GET | nginx が `html/static` から直接配信(Flaskは関与しない)。CDN(`Nginx-Flask-CDN-Docker`)経由ならCDNがキャッシュする |

| 項目 | 内容 |
| --- | --- |
| 配置 | `/${ENTRY_DIR}/${WS}/nginx/html/flask/` |
| 起動 | `start.sh` が gunicorn 経由で起動する(`app:app`) |
| 反映 | コード変更後は `docker compose restart` |

#### 構成

| ファイル | 役割 |
| --- | --- |
| `app.py` | ルーティング・静的ファイルのURL生成(このファイル) |
| `metrics.py` | `psutil` によるメモリ・CPUの取得 |
| `gauge.py` | ゲージ(SVG)の座標計算 |
| `templates/index.html` | ページ全体 |
| `templates/_gauges.html` | ゲージ部分(`index.html` からの include と `/partials/gauges` で共用) |

#### 定数

| 名前 | 値 | 説明 |
| --- | --- | --- |
| `REFRESH_SEC` | `5` | ブラウザがゲージを更新する間隔(秒) |
| `STATIC_DIR` | `html/static` の絶対パス | 静的ファイルの実体。内容ハッシュ(`?v=`)の計算元 |

#### 静的ファイルのURL

テンプレートでは `static_url('css/index.css')` のように書く。`/static/css/index.css?v=(内容ハッシュ)` になる。

| 項目 | 内容 |
| --- | --- |
| 相対パス | CDNがあってもなくても、ブラウザはアクセス中のホストから取得する (CDNがあれば、そこでキャッシュされる) |
| `?v=` | ファイル内容のハッシュ。ファイルを書き換えるとURLが変わるため、CDN・ブラウザに1年キャッシュさせても古いファイルが残らない |
"""

import hashlib
from pathlib import Path

from flask import Flask, jsonify, make_response, render_template, request

from gauge import build_gauge
from metrics import read_cpu, read_memory

REFRESH_SEC = 5
STATIC_DIR = (Path(__file__).resolve().parent.parent / "static").resolve()

app = Flask(__name__)

# {パス: ((更新時刻ns, サイズ), ハッシュ)}。ファイルが変わった時だけ再計算する
_asset_versions = {}


def _asset_version(filename):
    """
    #### 静的ファイルの内容ハッシュ(先頭10桁)を返す

    | 引数 | 型 | 説明 |
    | --- | --- | --- |
    | `filename` | `str` | `html/static` からの相対パス (例: `css/index.css`) |

    | 戻り値 | 型 | 説明 |
    | --- | --- | --- |
    | ハッシュ | `str` | MD5の先頭10桁。ファイルが無い・`STATIC_DIR` の外を指す場合は空文字 |
    """
    path = (STATIC_DIR / filename).resolve()
    if STATIC_DIR not in path.parents or not path.is_file():
        return ""

    stat = path.stat()
    stamp = (stat.st_mtime_ns, stat.st_size)
    cached = _asset_versions.get(path)
    if cached and cached[0] == stamp:
        return cached[1]

    digest = hashlib.md5(path.read_bytes(), usedforsecurity=False).hexdigest()[:10]
    _asset_versions[path] = (stamp, digest)
    return digest


def _static_url(filename):
    """
    #### 静的ファイルのURLを作る (テンプレートの `static_url()`)

    | 引数 | 型 | 説明 |
    | --- | --- | --- |
    | `filename` | `str` | `html/static` からの相対パス (例: `css/index.css`) |

    | 戻り値 | 型 | 説明 |
    | --- | --- | --- |
    | URL | `str` | `/static/${filename}?v=${内容ハッシュ}`。ファイルが無い場合は `?v=` 無し |
    """
    url = f"/static/{filename}"
    version = _asset_version(filename)
    return f"{url}?v={version}" if version else url


@app.context_processor
def _inject_static_helpers():
    """
    #### 全テンプレートで使える関数を追加する

    | 引数 | 型 | 説明 |
    | --- | --- | --- |
    | なし | - | - |

    | 戻り値 | 型 | 説明 |
    | --- | --- | --- |
    | テンプレート変数 | `dict` | `static_url`: 静的ファイルのURLを作る関数 (`_static_url`) |
    """
    return {"static_url": _static_url}


def _gauge_context():
    """
    #### ゲージ部分のテンプレート変数を作る

    | 引数 | 型 | 説明 |
    | --- | --- | --- |
    | なし | - | - |

    | 戻り値 | 型 | 説明 |
    | --- | --- | --- |
    | テンプレート変数 | `dict` | `memory` `memory_gauge` `cpu` `cpu_gauge` (`templates/_gauges.html` 参照) |
    """
    memory = read_memory()
    cpu = read_cpu()
    return {
        "memory": memory,
        "memory_gauge": build_gauge(memory.percent),
        "cpu": cpu,
        "cpu_gauge": build_gauge(cpu.percent),
    }


@app.route("/")
def index():
    """
    #### トップページを返す

    | 引数 | 型 | 説明 |
    | --- | --- | --- |
    | なし | - | - |

    | 戻り値 | 型 | 説明 |
    | --- | --- | --- |
    | HTML | `str` | `templates/index.html` を描画した結果(ゲージ込み) |
    """
    return render_template("index.html", refresh_sec=REFRESH_SEC, **_gauge_context())


@app.route("/partials/gauges")
def gauges():
    """
    #### ゲージ部分のHTML断片を返す

    | 引数 | 型 | 説明 |
    | --- | --- | --- |
    | なし | - | - |

    | 戻り値 | 型 | 説明 |
    | --- | --- | --- |
    | レスポンス | `Response` | `templates/_gauges.html` を描画した結果。`Cache-Control: no-store` 付き |
    """
    response = make_response(render_template("_gauges.html", **_gauge_context()))
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/api/health")
def health():
    """
    #### ヘルスチェック

    | 引数 | 型 | 説明 |
    | --- | --- | --- |
    | なし | - | - |

    | 戻り値 | 型 | 説明 |
    | --- | --- | --- |
    | レスポンス | `Response` | `{"status": "ok"}` の JSON |
    """
    return jsonify(status="ok")


@app.route("/api/echo", methods=["POST"])
def echo():
    """
    #### リクエストボディの JSON をそのまま返す

    | 引数 | 型 | 説明 |
    | --- | --- | --- |
    | リクエストボディ | `JSON` | 任意の JSON(関数の引数は無し) |

    | 戻り値 | 型 | 説明 |
    | --- | --- | --- |
    | レスポンス | `Response` | 受け取った JSON(不正な場合は `{}`) |
    """
    return jsonify(request.get_json(silent=True) or {})
