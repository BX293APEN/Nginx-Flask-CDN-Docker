"""
### gauge.py

半円ゲージ(SVG)の描画に必要な座標・色を計算する。

CGI版 (`CGITEST/cgi-bin/main.py`) の `WebCGI.gauge_create` を移植したもの。
CGI版は「座標計算」と「HTML文字列の組み立て」を1つの関数で行っていたが、
こちらは座標計算のみを行い、SVGの描画は `templates/_gauges.html` の `gauge` マクロが担当する。

| 項目 | 内容 |
| --- | --- |
| 座標計算 | `build_gauge` (このモジュール) |
| SVG描画 | `templates/_gauges.html` の `gauge` マクロ |
| 色分け・目盛り | `LEVEL_COLORS` から自動生成する(色の境目に目盛りを打つ。CGI版と同じ流儀) |

#### 定数

| 名前 | 値 | 説明 |
| --- | --- | --- |
| `RADIUS` | `20` | 半円の半径 (viewBox 単位) |
| `MARGIN` | `10` | viewBox の余白 (viewBox 単位) |
| `NEEDLE_RATIO` | `1.15` | 針の長さ / 半径 |
| `TICK_INNER_RATIO` | `0.85` | 目盛り線の内側端 / 半径 |
| `TICK_OUTER_RATIO` | `1.00` | 目盛り線の外側端 / 半径 |
| `HUB_RATIO` | `0.08` | 針の根元の丸の半径 / 半径 |
| `LEVEL_COLORS` | 下表 | 使用率ごとの色分け(上限値は「未満」で判定) |

#### `LEVEL_COLORS` の内訳

| 使用率 | 色 | 意味 |
| --- | --- | --- |
| 60% 未満 | `#009933` | 良好 |
| 60% 以上 80% 未満 | `#FF9900` | 注意 |
| 80% 以上 90% 未満 | `#FF3366` | 警告 |
| 90% 以上 | `#FF0000` | 危険 |
"""

import math
from dataclasses import dataclass
from typing import NamedTuple

RADIUS = 20
MARGIN = 10
NEEDLE_RATIO = 1.15
TICK_INNER_RATIO = 0.85
TICK_OUTER_RATIO = 1.00
HUB_RATIO = 0.08

# (上限値, 色) の並び。最後は必ず `math.inf` にすること
LEVEL_COLORS = (
    (60, "#009933"),
    (80, "#FF9900"),
    (90, "#FF3366"),
    (math.inf, "#FF0000"),
)


class Tick(NamedTuple):
    """
    #### 目盛り線1本分の座標 (viewBox 単位)

    | メンバ | 型 | 説明 |
    | --- | --- | --- |
    | `x1` | `float` | 内側端の X 座標 |
    | `y1` | `float` | 内側端の Y 座標 |
    | `x2` | `float` | 外側端の X 座標 |
    | `y2` | `float` | 外側端の Y 座標 |
    """

    x1: float
    y1: float
    x2: float
    y2: float


@dataclass(frozen=True)
class Gauge:
    """
    #### ゲージ1つ分の描画パラメータ (viewBox 単位)

    | メンバ | 型 | 説明 |
    | --- | --- | --- |
    | `view_width` | `int` | viewBox の幅 (`2 * RADIUS + 2 * MARGIN`) |
    | `view_height` | `int` | viewBox の高さ (`RADIUS + 2 * MARGIN`) |
    | `arc_path` | `str` | 半円の `d` 属性 (背景・値で共用) |
    | `arc_length` | `float` | 半円の弧長 (`π * RADIUS`) |
    | `value_length` | `float` | 値の弧長 (`arc_length * 使用率`) |
    | `stroke_width` | `float` | 弧の線幅 |
    | `color` | `str` | 値の弧の色 |
    | `center_x` | `float` | 針の根元の X 座標 |
    | `center_y` | `float` | 針の根元の Y 座標 |
    | `needle_x` | `float` | 針の先端の X 座標 |
    | `needle_y` | `float` | 針の先端の Y 座標 |
    | `hub_radius` | `float` | 針の根元の丸の半径 |
    | `ticks` | `tuple[Tick, ...]` | 目盛り線 (色の境目 + 両端) |
    """

    view_width: int
    view_height: int
    arc_path: str
    arc_length: float
    value_length: float
    stroke_width: float
    color: str
    center_x: float
    center_y: float
    needle_x: float
    needle_y: float
    hub_radius: float
    ticks: tuple


def pick_color(percent, levels=LEVEL_COLORS):
    """
    #### 値に対応する色を返す

    | 引数 | 型 | 説明 |
    | --- | --- | --- |
    | `percent` | `float` | 現在値 (0〜100) |
    | `levels` | `tuple` | `(上限値, 色)` の並び。既定は `LEVEL_COLORS` |

    | 戻り値 | 型 | 説明 |
    | --- | --- | --- |
    | 色 | `str` | `percent` が最初に「上限値未満」となった行の色 |
    """
    for limit, color in levels:
        if percent < limit:
            return color
    return levels[-1][1]


def _tick(ratio, center_x, center_y):
    """
    #### 割合に対応する目盛り線を作る

    | 引数 | 型 | 説明 |
    | --- | --- | --- |
    | `ratio` | `float` | 半円上の位置 (0.0 = 左端 / 1.0 = 右端) |
    | `center_x` | `float` | 半円の中心 X |
    | `center_y` | `float` | 半円の中心 Y |

    | 戻り値 | 型 | 説明 |
    | --- | --- | --- |
    | 目盛り線 | `Tick` | 半径の `TICK_INNER_RATIO`〜`TICK_OUTER_RATIO` の線分 |
    """
    angle = math.pi * (1 - max(0.0, min(1.0, ratio)))
    cos, sin = math.cos(angle), math.sin(angle)
    r1 = RADIUS * TICK_INNER_RATIO
    r2 = RADIUS * TICK_OUTER_RATIO
    return Tick(
        x1=round(center_x + r1 * cos, 2),
        y1=round(center_y - r1 * sin, 2),
        x2=round(center_x + r2 * cos, 2),
        y2=round(center_y - r2 * sin, 2),
    )


def build_gauge(percent, levels=LEVEL_COLORS):
    """
    #### ゲージの描画パラメータを計算する

    | 引数 | 型 | 説明 |
    | --- | --- | --- |
    | `percent` | `float` | 現在値 (0〜100)。範囲外は端に丸める |
    | `levels` | `tuple` | 色分け定義。既定は `LEVEL_COLORS` (目盛りもここから作る) |

    | 戻り値 | 型 | 説明 |
    | --- | --- | --- |
    | ゲージ | `Gauge` | `templates/_gauges.html` の `gauge` マクロへ渡す値 |
    """
    ratio = max(0.0, min(1.0, percent / 100))

    center_x = RADIUS + MARGIN
    center_y = RADIUS + MARGIN
    arc_length = math.pi * RADIUS

    # 針 (左端 = 0%、右端 = 100%)
    angle = math.pi * (1 - ratio)
    needle_r = RADIUS * NEEDLE_RATIO
    needle_x = center_x + needle_r * math.cos(angle)
    needle_y = center_y - needle_r * math.sin(angle)

    # 目盛り: 0%、色の境目、100%
    scales = [0.0, *[limit for limit, _ in levels if math.isfinite(limit)], 100.0]
    ticks = tuple(_tick(s / 100, center_x, center_y) for s in scales)

    return Gauge(
        view_width=2 * RADIUS + 2 * MARGIN,
        view_height=RADIUS + 2 * MARGIN,
        arc_path=f"M {MARGIN},{center_y} A {RADIUS},{RADIUS} 0 0,1 {2 * RADIUS + MARGIN},{center_y}",
        arc_length=round(arc_length, 2),
        value_length=round(arc_length * ratio, 2),
        stroke_width=MARGIN / 2,
        color=pick_color(percent, levels),
        center_x=center_x,
        center_y=center_y,
        needle_x=round(needle_x, 2),
        needle_y=round(needle_y, 2),
        hub_radius=round(RADIUS * HUB_RATIO, 2),
        ticks=ticks,
    )
