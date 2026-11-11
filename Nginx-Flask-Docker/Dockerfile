# FROM [イメージ] [タグ]
# Docker Hub (https://hub.docker.com/) 参照
FROM ubuntu:25.10

# 環境変数を compose.yml から受け取る
ARG WS
ARG USER_NAME
ARG PASSWORD
ARG ENTRY_DIR
ARG ENTRY_POINT
ARG LANG

# 環境変数を設定
# 1000以上推奨
ENV USER_ID=1001
ENV GROUP_ID=1001
ENV USER_NAME=${USER_NAME}

# RUN 命令はなるべく1つにまとめる
# コマンドが長くなる場合は \ で改行すること

RUN apt update && \
    apt upgrade -y && \
    apt install -y \
    sudo nano iproute2 iputils-ping language-pack-ja \
    nginx python3 python3-pip python3-psutil && \
    useradd -m -s /bin/bash -u ${USER_ID} ${USER_NAME} && \
    usermod -aG sudo ${USER_NAME} && \
    echo "root:${PASSWORD}" | chpasswd && \
    echo "${USER_NAME}:${PASSWORD}" | chpasswd && \
    mkdir -p /${ENTRY_DIR}/${WS} && \
    chown -R ${USER_NAME}:${USER_NAME} /${ENTRY_DIR} && \
    update-locale LANG=${LANG} && \
    pip install --break-system-packages \
    flask gunicorn

COPY ${ENTRY_POINT} /${ENTRY_DIR}/${ENTRY_POINT}
RUN chmod +x /${ENTRY_DIR}/${ENTRY_POINT}

WORKDIR /${ENTRY_DIR}/${WS}
