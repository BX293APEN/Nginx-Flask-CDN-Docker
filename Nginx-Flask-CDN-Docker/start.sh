#!/usr/bin/env bash

set -eu

# nginx のワーカーを動かすユーザ (DockerfileでENV化された${USER_NAME})
readonly APP_USER="${USER_NAME}"

# パス設定 (絶対パス指定)
readonly NGINX_PREFIX="$(pwd)/nginx"
readonly RUN_DIR="${NGINX_PREFIX}/run"
readonly TEMPLATE="${NGINX_PREFIX}/config/nginx.conf.template"
readonly CONF="${RUN_DIR}/nginx.conf"

# キャッシュの置き場所 (compose.yml の名前付きボリューム cdn_cache)
# bind mount (Windows / macOS では遅い) を避けるため、ホストのフォルダではなくボリュームを使う
readonly CACHE_DIR="/var/cache/cdn"

# テンプレートに埋め込む値 (compose.yml の environment / .env から渡される)
export ORIGIN_HOST="${ORIGIN_HOST:-host.docker.internal}"
export ORIGIN_PORT="${ORIGIN_PORT:-8080}"
export CACHE_MAX_SIZE="${CACHE_MAX_SIZE:-1g}"
export CACHE_INACTIVE="${CACHE_INACTIVE:-7d}"

# nginx が書き込みに使う実行時ディレクトリを用意 & 所有者変更
mkdir -p \
    "${RUN_DIR}/tmp/client_body" \
    "${RUN_DIR}/tmp/proxy" \
    "${RUN_DIR}/tmp/fastcgi" \
    "${RUN_DIR}/tmp/uwsgi" \
    "${RUN_DIR}/tmp/scgi" \
    "${CACHE_DIR}/nginx"

chown -R "${APP_USER}:${APP_USER}" "${RUN_DIR}" "${CACHE_DIR}"

# nginx.conf を生成する
# 第1引数で埋め込む変数を限定する (nginx自身の $uri などを envsubst に消されないため)
envsubst '${ORIGIN_HOST} ${ORIGIN_PORT} ${CACHE_MAX_SIZE} ${CACHE_INACTIVE}' \
    < "${TEMPLATE}" > "${CONF}"

# 設定ファイルの文法チェック (失敗したらここでコンテナが止まり、ログに原因が出る)
nginx -t -p "${NGINX_PREFIX}" -c "${CONF}" -g "user ${APP_USER};"

# Nginxを起動 (フォアグラウンドで動かし続けるため、sleepのループは不要)
exec nginx -p "${NGINX_PREFIX}" -c "${CONF}" -g "user ${APP_USER}; daemon off;"
