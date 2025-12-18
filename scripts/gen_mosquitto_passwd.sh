#!/bin/sh
set -eu

BASE_DIR=$(cd "$(dirname "$0")/.." && pwd)
CONF_DIR="$BASE_DIR/mosquitto/conf"

USER_NAME=${1:-operator}
USER_PASS=${2:-operator123}

mkdir -p "$CONF_DIR"

PYTHONWARNINGS=ignore python3 - <<PY > "$CONF_DIR/passwd"
import crypt
import sys

user = "${USER_NAME}"
password = "${USER_PASS}"

hashed = crypt.crypt(password, crypt.mksalt(crypt.METHOD_SHA512))
print(f"{user}:{hashed}")
PY

chmod 600 "$CONF_DIR/passwd"

echo "Mosquitto passwd generated for user '$USER_NAME' in $CONF_DIR/passwd"
