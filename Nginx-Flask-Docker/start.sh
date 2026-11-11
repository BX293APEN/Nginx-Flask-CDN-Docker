#!/usr/bin/env bash

set -eu

# アプリを実行するユーザ (DockerfileでENV化された${USER_NAME})
readonly APP_USER="${USER_NAME}"

# パス設定 (絶対パス指定)
readonly NGINX_PREFIX="$(pwd)/nginx"
readonly FLASK_DIR="${NGINX_PREFIX}/html/flask"
readonly RUN_DIR="${NGINX_PREFIX}/run"

# gunicorn の待受アドレス (nginx.conf の proxy_pass と合わせること)
readonly FLASK_HOST="127.0.0.1"
readonly FLASK_PORT="${FLASK_PORT:-5000}"
readonly FLASK_WORKERS="${FLASK_WORKERS:-2}"

# Nginx / gunicorn が書き込みに使う実行時ディレクトリを用意 & 所有者変更
mkdir -p \
    "${RUN_DIR}/tmp/client_body" \
    "${RUN_DIR}/tmp/proxy" \
    "${RUN_DIR}/tmp/fastcgi" \
    "${RUN_DIR}/tmp/uwsgi" \
    "${RUN_DIR}/tmp/scgi"

chown -R "${APP_USER}:${APP_USER}" "${RUN_DIR}"

# Flask (gunicorn) をバックグラウンドで起動
# app:app = flask/app.py の変数 app
gunicorn \
    --daemon \
    --chdir "${FLASK_DIR}" \
    --bind "${FLASK_HOST}:${FLASK_PORT}" \
    --workers "${FLASK_WORKERS}" \
    --user "${APP_USER}" \
    --group "${APP_USER}" \
    --pid "${RUN_DIR}/gunicorn.pid" \
    --access-logfile "${RUN_DIR}/gunicorn_access.log" \
    --error-logfile "${RUN_DIR}/gunicorn_error.log" \
    app:app

# Nginxを起動
nginx -p "${NGINX_PREFIX}" -c "${NGINX_PREFIX}/config/nginx.conf" -g "user ${APP_USER};"

# --- コンテナを起動し続ける ---
while true; do
    sleep 1000
done
