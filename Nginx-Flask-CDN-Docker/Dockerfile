# FROM [イメージ] [タグ]
# Docker Hub (https://hub.docker.com/) 参照
FROM ubuntu:25.10

# 環境変数を compose.yml から受け取る
ARG WS
ARG USER_NAME
ARG ENTRY_DIR
ARG ENTRY_POINT

# 環境変数を設定
# 1000以上推奨
ENV USER_ID=1001
ENV GROUP_ID=1001
ENV USER_NAME=${USER_NAME}

# | パッケージ | 用途 |
# | --- | --- |
# | nginx | CDN本体 (リバースプロキシ + キャッシュ) |
# | gettext-base | `envsubst` (nginx.conf.template に .env の値を埋め込む) |
# | curl | ヘルスチェック・動作確認 |
# | tzdata | `TZ` を有効にする |
# | nano iproute2 iputils-ping | デバッグ用 |

RUN apt update && \
    apt upgrade -y && \
    DEBIAN_FRONTEND=noninteractive apt install -y \
    nginx gettext-base curl tzdata nano iproute2 iputils-ping && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -m -s /bin/bash -u ${USER_ID} ${USER_NAME} && \
    mkdir -p /${ENTRY_DIR}/${WS} && \
    chown -R ${USER_NAME}:${USER_NAME} /${ENTRY_DIR}

COPY ${ENTRY_POINT} /${ENTRY_DIR}/${ENTRY_POINT}
RUN chmod +x /${ENTRY_DIR}/${ENTRY_POINT}

WORKDIR /${ENTRY_DIR}/${WS}
