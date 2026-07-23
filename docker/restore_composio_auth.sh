#!/bin/sh
# Rehydrate Composio CLI user_data.json from env secrets at container boot.
#
# COMPOSIO_API_KEY is the Railway variable (uak_...). Optional companions:
# COMPOSIO_BASE_URL, COMPOSIO_WEB_URL, COMPOSIO_ORG_ID, COMPOSIO_TEST_USER_ID.
# Writes under $HERMES_HOME/home/.composio/ (Composio's COMPOSIO_CACHE_DIR
# default when HOME=/opt/data/home).
set -u

HERMES_HOME="${HERMES_HOME:-/opt/data}"
COMPOSIO_DIR="${COMPOSIO_CACHE_DIR:-$HERMES_HOME/home/.composio}"
TARGET="$COMPOSIO_DIR/user_data.json"

if [ -z "${COMPOSIO_API_KEY:-}" ]; then
    echo "[composio-auth] Skipping: COMPOSIO_API_KEY is not set"
    exit 0
fi

_read_existing_key() {
    python3 - "$1" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as fh:
        data = json.load(fh)
    print(data.get("api_key") or "")
except Exception:
    print("")
PY
}

need_write=0
if [ ! -f "$TARGET" ]; then
    need_write=1
else
    existing_key="$(_read_existing_key "$TARGET" 2>/dev/null || printf '')"
    if [ "$existing_key" != "$COMPOSIO_API_KEY" ]; then
        need_write=1
    fi
fi

if [ "$need_write" -eq 0 ]; then
    echo "[composio-auth] user_data.json is up to date"
    exit 0
fi

mkdir -p "$COMPOSIO_DIR"

export COMPOSIO_TARGET="$TARGET"
if ! python3 <<'PY'
import json
import os
import sys

target = os.environ["COMPOSIO_TARGET"]
payload = {
    "api_key": os.environ["COMPOSIO_API_KEY"],
    "base_url": os.environ.get("COMPOSIO_BASE_URL", "https://backend.composio.dev"),
    "web_url": os.environ.get("COMPOSIO_WEB_URL", "https://platform.composio.dev"),
}
org_id = os.environ.get("COMPOSIO_ORG_ID", "")
test_user_id = os.environ.get("COMPOSIO_TEST_USER_ID", "")
if org_id:
    payload["org_id"] = org_id
if test_user_id:
    payload["test_user_id"] = test_user_id

with open(target, "w", encoding="utf-8") as fh:
    json.dump(payload, fh, indent=2)
    fh.write("\n")
PY
then
    echo "[composio-auth] Warning: failed to write user_data.json" >&2
    exit 0
fi

chmod 600 "$TARGET" 2>/dev/null || true
echo "[composio-auth] Wrote $TARGET"
exit 0
