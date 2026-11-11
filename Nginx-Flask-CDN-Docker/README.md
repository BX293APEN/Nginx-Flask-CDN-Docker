# Nginx-Flask-CDN-Docker

`Nginx-Flask-Docker` (origin) の手前に置くCDN。ユーザからのリクエストを全て受け、
`/static/` (CSS / JS / 画像) は `proxy_cache` でキャッシュして返し、ページ・APIはoriginへそのまま中継する。

## 構成

```
ユーザ ── CDN端末:80 ──→ CDN ─┬─ /static/ ─ キャッシュにあれば即返す
                              │             無ければ ─ ORIGIN_HOST:8080 ─→ origin ─→ Flask
                              └─ それ以外 ─ ORIGIN_HOST:8080 ─→ origin ─→ Flask (キャッシュしない)
```

| 項目 | CDN (このプロジェクト) | origin (Nginx-Flask-Docker) |
| --- | --- | --- |
| コンテナ名 | `Docker_Nginx_CDN` | `Docker_Nginx_Flask` |
| ホスト側ポート (.env) | `CDN_PORT` (既定 `80`) | `PORT` (既定 `8080`) |
| 接続してくる相手 | ユーザ | CDN だけ |
| 役割 | 静的ファイルのキャッシュ・gzip圧縮。それ以外は中継 | ページ・APIを返す。静的ファイルの本体を持つ |

## ポート・接続先の設定 (.env)

2つのプロジェクトの `.env` で、次の値を合わせる。

| 設定する場所 | 項目 | 意味 | 既定値 |
| --- | --- | --- | --- |
| CDN の `.env` | `CDN_PORT` | ユーザがCDNに接続するポート | `80` |
| CDN の `.env` | `ORIGIN_HOST` | originのIPアドレスまたはホスト名 | `host.docker.internal` |
| CDN の `.env` | `ORIGIN_PORT` | CDNがoriginに接続するポート | `8080` |
| origin の `.env` | `PORT` | originが公開するポート。**CDN の `ORIGIN_PORT` と同じ値にする** | `8080` |

### 構成ごとの設定例

| 構成 | CDN: `ORIGIN_HOST` | CDN: `CDN_PORT` | CDN: `ORIGIN_PORT` | origin: `PORT` |
| --- | --- | --- | --- | --- |
| 別の端末 (想定構成) | originの端末のIPアドレス (例 `192.168.1.20`) | `80` | `8080` | `8080` |
| 同じ端末 | `host.docker.internal` (既定のまま) | `80` | `8080` | `8080` |
| 同じ端末でポートを変える | `host.docker.internal` | `8000` | `9000` | `9000` |

同じ端末の場合は、`CDN_PORT` と origin の `PORT` が**同じ値にならないように**する (同じポートを2つのコンテナが使えないため)。

## 起動手順

| 順番 | 端末 | 場所 | コマンド |
| --- | --- | --- | --- |
| 1 | origin | `Nginx-Flask-Docker/` | `docker compose up --build -d` |
| 2 | CDN | `Nginx-Flask-CDN-Docker/` (`.env` の `ORIGIN_HOST` を設定済み) | `docker compose up --build -d` |
| 3 | ユーザ | ブラウザ | `http://(CDNのIPアドレス)` (`CDN_PORT` が80以外なら `:ポート` も付ける) |

停止は `docker compose down` (それぞれのプロジェクトで)。

### 別端末で使う時の確認

| 確認 | 内容 |
| --- | --- |
| ファイアウォール | origin の端末で、CDN の端末から `PORT` (既定 8080) への接続を許可する |
| CDN → origin の疎通 | CDN の端末で `curl http://(originのIPアドレス):8080/api/health` が `{"status":"ok"}` を返す |
| 名前解決 | `ORIGIN_HOST` に名前を使う場合は、CDN 起動時に名前解決できること (IPアドレス指定が確実) |

## 動作確認

| 確認したいこと | コマンド | 期待する結果 |
| --- | --- | --- |
| CDNの死活 | `curl http://(CDNのIPアドレス)/healthz` | `ok` |
| origin まで届くか | `curl http://(CDNのIPアドレス)/api/health` | `{"status":"ok"}` |
| キャッシュが効いているか | `curl -sI "http://(CDNのIPアドレス)/static/css/index.css?v=xxxx"` を2回実行 | 1回目 `X-Cache-Status: MISS`、2回目 `HIT` |
| ブラウザ側のキャッシュ | 開発者ツールの Network で再読み込み | CSS / JS が `(disk cache)` になる |
| アクセスログ | `linux_data/nginx/run/access.log` | 行末に `cache=HIT` などが出る |

### `X-Cache-Status` の値

| 値 | 意味 |
| --- | --- |
| `MISS` | キャッシュに無く、originから取得した |
| `HIT` | CDNのキャッシュから返した |
| `EXPIRED` | 期限切れだったので、originから取得し直した |
| `REVALIDATED` | 期限切れだったが、originに確認して変更が無かったのでキャッシュを使った |
| `STALE` / `UPDATING` | originの障害中・更新中なので、期限切れのキャッシュで返した |

## キャッシュの仕組み

| 項目 | 内容 |
| --- | --- |
| 対象 | `/static/` の GET / HEAD のみ。ページ・APIはキャッシュせず、毎回originへ中継する |
| URL | origin の Flask が `static_url()` で `?v=(内容ハッシュ)` を付ける。ファイルを書き換えるとURLが変わる |
| `?v=` あり | `Cache-Control: public, max-age=31536000, immutable` (1年)。ブラウザもCDNも再確認しない |
| `?v=` なし | `Cache-Control: public, max-age=300` (5分)。手で直接開いた場合などの保険 |
| 更新の反映 | origin の `static/` を編集してリロードするだけ。新しいハッシュのURLが使われるので、**キャッシュを消す必要はない** |
| 圧縮 | CDNがgzipで圧縮する (originには圧縮なしで取りに行き、キャッシュは1種類だけ) |
| origin停止中 | キャッシュ済みの静的ファイルは配信を続ける。ページ・APIは `502` になる |

## 設定の変更

| 変更したいこと | 変更する場所 | 反映方法 |
| --- | --- | --- |
| ユーザ側のポート | CDN の `.env` の `CDN_PORT` | CDN を `docker compose up -d` |
| origin の場所・ポート | CDN の `.env` の `ORIGIN_HOST` / `ORIGIN_PORT` と、origin の `.env` の `PORT` | 両方 `docker compose up -d` |
| キャッシュ容量・保持期間 | CDN の `.env` の `CACHE_MAX_SIZE` / `CACHE_INACTIVE` | `docker compose up -d` |
| nginx の細かい設定 | `linux_data/nginx/config/nginx.conf.template` | `docker compose restart` |
| CDNを使わない | CDN を停止し、origin の `.env` の `PORT` を `80` にする | origin を `docker compose up -d` |

## キャッシュを空にする

```
docker compose exec cdn sh -c 'rm -rf /var/cache/cdn/nginx/*'
docker compose restart
```

ボリュームごと消す場合は `docker compose down -v`。

## 注意

| 項目 | 内容 |
| --- | --- |
| HTTPS | このCDNはHTTPのみ |
| 公開範囲 | 認証は無いので、インターネットには公開しないこと |
| origin への直接アクセス | origin の `PORT` はCDN以外からも接続できてしまう。CDNを通さない接続を防ぎたい場合は、origin の端末のファイアウォールでCDNのIPアドレスだけに許可する |
| クライアントIP | origin から見た接続元はCDNのIPアドレスになる。元のIPは `X-Forwarded-For` ヘッダに入っている |
