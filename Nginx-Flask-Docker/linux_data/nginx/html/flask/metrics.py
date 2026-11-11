"""
### metrics.py

`psutil` でメモリ使用量・CPU使用率を取得する。

| 項目 | 内容 |
| --- | --- |
| 取得対象 | コンテナ内の `/proc` が示す値(= Dockerホストのカーネル全体の値) |
| 注意 | `compose.yml` に `mem_limit` 等を設定しても、ここで取れる値はそれらの制限を反映しない |
| 注意 | Docker Desktop (Windows / macOS) ではホストOSではなく、Docker が使うLinux VMの値になる |

#### 定数

| 名前 | 値 | 説明 |
| --- | --- | --- |
| `GIB` | `1024 ** 3` | 1 GiB のバイト数 |
| `CPU_SAMPLE_SEC` | `0.5` | CPU使用率の計測時間(秒)。この間リクエストを処理するワーカーがブロックされる |
"""

from dataclasses import dataclass

import psutil

GIB = 1024 ** 3
CPU_SAMPLE_SEC = 0.5


@dataclass(frozen=True)
class MemoryUsage:
    """
    #### メモリ使用量

    | メンバ | 型 | 説明 |
    | --- | --- | --- |
    | `total_gib` | `float` | 搭載メモリ(GiB) |
    | `used_gib` | `float` | 使用量(GiB)。`total - available` で、`free -h` の `used` に近い値 |
    | `percent` | `float` | 使用率(%)。`used_gib / total_gib * 100` |
    """

    total_gib: float
    used_gib: float
    percent: float


@dataclass(frozen=True)
class CpuUsage:
    """
    #### CPU使用率

    | メンバ | 型 | 説明 |
    | --- | --- | --- |
    | `percent` | `float` | 全コア平均の使用率(%) |
    | `cores` | `int` | 論理コア数 |
    """

    percent: float
    cores: int


def read_memory():
    """
    #### メモリ使用量を取得する

    | 引数 | 型 | 説明 |
    | --- | --- | --- |
    | なし | - | - |

    | 戻り値 | 型 | 説明 |
    | --- | --- | --- |
    | メモリ使用量 | `MemoryUsage` | 取得時点の値 |
    """
    vm = psutil.virtual_memory()
    # percent と used が食い違わないよう、どちらも available から自前で計算する
    used = vm.total - vm.available
    return MemoryUsage(
        total_gib=vm.total / GIB,
        used_gib=used / GIB,
        percent=used / vm.total * 100,
    )


def read_cpu():
    """
    #### CPU使用率を取得する

    | 引数 | 型 | 説明 |
    | --- | --- | --- |
    | なし | - | - |

    | 戻り値 | 型 | 説明 |
    | --- | --- | --- |
    | CPU使用率 | `CpuUsage` | `CPU_SAMPLE_SEC` 秒間の平均使用率 |

    `interval=None` (前回呼び出しからの平均) にしないのは、gunicornのワーカーが複数あり
    ワーカーごとに「前回」が異なってしまうため。ブロッキング計測ならワーカー数に依存しない。
    """
    percent = psutil.cpu_percent(interval=CPU_SAMPLE_SEC)
    return CpuUsage(
        percent=min(100.0, percent),
        cores=psutil.cpu_count() or 1,
    )
