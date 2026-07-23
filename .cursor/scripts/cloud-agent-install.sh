#!/usr/bin/env bash
# Cursor cloud-agent bootstrap: Hermes dev deps + Railway CLI.
# Idempotent — safe to re-run on every VM startup after git pull.
set -euo pipefail

export PATH="${HOME}/.local/bin:${HOME}/.railway/bin:${PATH}"
export UV_NO_CONFIG=1

cd "$(dirname "$0")/../.."

echo "[cloud-agent-install] Hermes Python environment"
if [ ! -d .venv ]; then
  uv venv .venv --python 3.11
fi
# shellcheck disable=SC1091
source .venv/bin/activate
uv pip install -e ".[all,dev]"

echo "[cloud-agent-install] Railway CLI"
if command -v railway >/dev/null 2>&1; then
  echo "[cloud-agent-install] railway already on PATH: $(command -v railway)"
else
  # User-local install to ~/.railway/bin (no sudo). Prefer over npm -g, which
  # fails on cloud VMs without write access to /usr/lib/node_modules.
  bash <(curl -fsSL https://railway.com/install.sh) -y
  export PATH="${HOME}/.railway/bin:${PATH}"
fi

railway --version
echo "[cloud-agent-install] complete"
