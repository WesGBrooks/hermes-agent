#!/bin/bash
# Sync private context repos into the persistent Hermes Railway volume.
#
# Tokens are supplied through Railway variables and passed to git via a
# one-shot HTTP header, so they are not written into .git/config.
set -u

HERMES_HOME="${HERMES_HOME:-/opt/data}"
CONTEXT_REPOS_DIR="${HERMES_CONTEXT_REPOS_DIR:-$HERMES_HOME/workspace/repos}"

mkdir -p "$CONTEXT_REPOS_DIR"

sync_context_repo() {
    local name="$1"
    local url="$2"
    local token_var="$3"
    local access_note="$4"
    local target="$CONTEXT_REPOS_DIR/$name"
    local token="${!token_var:-}"
    local auth_header

    if [ -z "$token" ]; then
        echo "[context-sync] Skipping $name: $token_var is not set"
        return 0
    fi

    echo "[context-sync] Syncing $name ($access_note) into $target"
    auth_header="$(printf 'x-access-token:%s' "$token" | base64 | tr -d '\n')"

    if [ -d "$target/.git" ]; then
        git -C "$target" remote set-url origin "$url" 2>/dev/null || true

        if [ -n "$(git -C "$target" status --porcelain 2>/dev/null)" ]; then
            echo "[context-sync] $name has local changes; fetching only and leaving worktree untouched"
            git -C "$target" \
                -c "http.https://github.com/.extraheader=AUTHORIZATION: basic $auth_header" \
                fetch --prune origin || \
                echo "[context-sync] Warning: fetch failed for $name"
            return 0
        fi

        local branch
        branch="$(git -C "$target" rev-parse --abbrev-ref HEAD 2>/dev/null || printf 'main')"
        git -C "$target" \
            -c "http.https://github.com/.extraheader=AUTHORIZATION: basic $auth_header" \
            pull --ff-only origin "$branch" || \
            echo "[context-sync] Warning: pull failed for $name"
    else
        if [ -e "$target" ]; then
            echo "[context-sync] Warning: $target exists but is not a git repo; skipping $name"
            return 0
        fi

        git -c "http.https://github.com/.extraheader=AUTHORIZATION: basic $auth_header" \
            clone "$url" "$target" || \
            echo "[context-sync] Warning: clone failed for $name"
        if [ -d "$target/.git" ]; then
            git -C "$target" remote set-url origin "$url" 2>/dev/null || true
        fi
    fi
}

sync_context_repo \
    "family" \
    "https://github.com/WesGBrooks/brooks-family-os.git" \
    "GITHUB_FAMILY_CONTEXT_TOKEN" \
    "read/write token"

sync_context_repo \
    "work" \
    "https://github.com/lightworks-ventures/org_management.git" \
    "GITHUB_WORK_CONTEXT_TOKEN" \
    "read-only token"

cat > "$CONTEXT_REPOS_DIR/README.md" <<'EOF'
# Hermes Context Repos

These repos are synced into the persistent Railway volume at container startup.

- `family/` maps to `WesGBrooks/brooks-family-os` and uses `GITHUB_FAMILY_CONTEXT_TOKEN`.
- `work/` maps to `lightworks-ventures/org_management` and uses `GITHUB_WORK_CONTEXT_TOKEN`.

Tokens are Railway variables. Do not commit tokens into any repo.
EOF

exit 0
