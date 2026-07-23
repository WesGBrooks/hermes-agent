# Railway Deployment Notes

This branch stays close to upstream Hermes while carrying a small Railway-specific
deployment patch. Deploy Railway from the long-lived `railway` branch.

## Recommended branch flow

- Keep `main` tracking `upstream/main` (NousResearch/hermes-agent).
- Deploy Railway from `railway`.
- After upstream updates: merge or rebase `main`, then rebase `railway` onto `main`.

```bash
git fetch upstream
git switch main && git merge upstream/main && git push origin main
git switch railway && git rebase main
# resolve conflicts if any, then:
git push origin railway --force-with-lease
```

Verify the Dockerfile has no active `VOLUME` instruction (Railway rejects it):

```bash
rg -n '^[[:space:]]*VOLUME' Dockerfile
```

That command should print nothing. Mount a Railway Volume at `/opt/data` for persistence.

## Profile persistence (read this before every deploy)

Hermes profiles, Telegram tokens, sessions, and gateway state all live on the
**Railway Volume** mounted at `/opt/data` (`HERMES_HOME`). The container image
is disposable; only `/opt/data` survives redeploys.

| Path on volume | What breaks if it is missing |
|----------------|------------------------------|
| `/opt/data/profiles/<name>/` | Named profiles vanish; per-profile Telegram/Discord configs disappear |
| `/opt/data/.env` | Default-profile API keys and `TELEGRAM_BOT_TOKEN` |
| `/opt/data/config.yaml` | Gateway platforms, models, `terminal.cwd` |
| `/opt/data/gateway_state.json` | Gateway may not auto-start after restart |
| `/opt/data/platforms/pairing/` | Messaging platform pairing state |

**Required Railway settings**

1. Attach a **Volume** to the service with mount path **`/opt/data`** (not `~/.hermes`, not `/data`).
2. Do **not** set `HERMES_HOME` to another path unless you also move the volume mount.
3. Keep `HERMES_HOME=/opt/data` (baked into the image — override only if the volume mount moves).

**After each deploy, verify in Railway logs or SSH**

```bash
railway ssh --service hermes-agent
ls -la /opt/data/profiles/
hermes profile list
hermes gateway status
tail -n 30 /opt/data/logs/container-boot.log
```

On boot, `docker/stage2-hook.sh` logs how many profile directories it found, e.g.
`[stage2] Found 3 profile(s) under /opt/data/profiles`. If that line shows `0` but
you expect profiles, the volume is not mounted correctly or points at an empty disk.

**Why Telegram disconnected last time**

The usual cause is a redeploy that started with an **empty** `/opt/data` because:

- the Railway Volume was not attached to the new service/revision, or
- the mount path changed away from `/opt/data`, or
- a fresh volume was created instead of reusing the existing one.

Hermes then seeds a blank `config.yaml` and `.env` on first boot. That looks like
“profiles are gone” even though the old data may still exist on the previous volume.

Before redeploying, note the volume name in Railway → Service → Volumes. After
deploy, confirm the same volume is still bound to `/opt/data`.

## Container runtime (s6-overlay)

Upstream Hermes Docker images use **s6-overlay** (`ENTRYPOINT /init` +
`main-wrapper.sh`), not the legacy `tini` + `entrypoint.sh` stack. Railway bootstrap
(STT flag, private context repos, volume permissions) runs in `docker/stage2-hook.sh`
during cont-init, before `hermes gateway` starts.

The image defaults to **`CMD ["gateway"]`** so the service starts as the always-on
messaging gateway.

## Railway service setup

- Builder: Dockerfile (`railway.json` points at repo-root `Dockerfile`)
- Volume mount: `/opt/data` → `HERMES_HOME`
- Secrets: model provider key(s) (e.g. `OPENROUTER_API_KEY`) plus messaging tokens
- Optional: `HERMES_ENSURE_STT_ENABLED=1` to enable `stt.enabled` on the volume
- Context repos: `GITHUB_FAMILY_CONTEXT_TOKEN`, `GITHUB_WORK_CONTEXT_TOKEN`

### Web dashboard (`HERMES_DASHBOARD=1`)

The supervised dashboard binds `0.0.0.0:9119` by default. On a public bind, Hermes
**requires** a registered auth provider — it will crash-loop without one.

**Recommended for Railway (username/password):** set these service variables:

| Variable | Purpose |
|----------|---------|
| `HERMES_DASHBOARD` | `1` to start the dashboard |
| `HERMES_DASHBOARD_BASIC_AUTH_USERNAME` | Login username |
| `HERMES_DASHBOARD_BASIC_AUTH_PASSWORD` | Login password |
| `HERMES_DASHBOARD_BASIC_AUTH_SECRET` | Stable session signing key (`openssl rand -base64 32`) |

Optional: `HERMES_DASHBOARD_PUBLIC_URL` if Railway’s public URL should be used for OAuth redirects (OIDC / Nous providers).

**Alternatives:**

- **Nous Portal OAuth:** `HERMES_DASHBOARD_OAUTH_CLIENT_ID=agent:…` (and optional `HERMES_DASHBOARD_PORTAL_URL`)
- **Self-hosted OIDC:** `HERMES_DASHBOARD_OIDC_ISSUER` + `HERMES_DASHBOARD_OIDC_CLIENT_ID`
- **Gateway only (no dashboard):** leave `HERMES_DASHBOARD` unset
- **Insecure (not recommended on the public internet):** `HERMES_DASHBOARD_INSECURE=1` — exposes API keys and sessions to anyone who can reach the port

Use Railway SSH for first-time setup or checks:

```bash
railway ssh --service hermes-agent
hermes gateway setup
hermes gateway status
```

Do not commit API keys. Use Railway variables or `/opt/data/.env`.

## Composio CLI (Google / workspace integrations without MCP)

The Composio CLI reads `~/.composio/user_data.json` for session context. On
Railway the API key must **not** live in that file on the persistent volume —
store it only as a Railway variable and let boot rehydrate the file.

| Variable | Purpose |
|----------|---------|
| `COMPOSIO_API_KEY` | `uak_…` user API key (required for restore) |
| `COMPOSIO_ORG_ID` | Organization id written into `user_data.json` |
| `COMPOSIO_TEST_USER_ID` | Test user id for CLI flows (e.g. `pg-test-…`) |
| `COMPOSIO_BASE_URL` | Optional; defaults to `https://backend.composio.dev` |
| `COMPOSIO_WEB_URL` | Optional; defaults to `https://platform.composio.dev` |

On every container start, `docker/restore_composio_auth.sh` (via
`stage2-hook.sh`) writes `/opt/data/home/.composio/user_data.json` when the
file is missing or the key changed. If `COMPOSIO_API_KEY` is unset, the hook
does nothing.

**One-time cleanup** if a key was previously written to the volume by hand:

```bash
railway ssh --service hermes-agent
rm -f /opt/data/home/.composio/user_data.json
exit
```

Then restart or redeploy so the restore hook recreates the file from env vars.

Do not commit `user_data.json` or copy a volume-local `restore-auth.sh` into
git — the image ships `docker/restore_composio_auth.sh`.

## Private context repos

On startup, `docker/sync_context_repos.sh` syncs into the persistent volume:

```text
/opt/data/workspace/repos/family  # WesGBrooks/brooks-family-os
/opt/data/workspace/repos/work    # lightworks-ventures/org_management
```

## Voice / local STT

The image runs `uv sync` with `--extra voice` (plus `--extra messaging`). Set
`HERMES_ENSURE_STT_ENABLED=1` or edit `stt.enabled` in `/opt/data/config.yaml`, then
restart the service or `/restart` in chat so the gateway reloads config.

## Session storage optimization (upstream Jul 2026)

Upstream Hermes can shrink the sessions SQLite DB by ~60% on average (up to
~78%) via a one-time FTS storage transition. Databases under ~1GB migrate
automatically after update. Larger DBs need a manual kick after deploy:

```bash
railway ssh --service hermes-agent
hermes sessions optimize-storage
```

It continues in the background while the gateway keeps serving. Safe to re-run
if interrupted; check container logs / `hermes sessions` status for progress.

## Cursor cloud agents

Cloud agents on this repo use `.cursor/environment.json`, which runs
`.cursor/scripts/cloud-agent-install.sh` on VM startup. That script installs
the Hermes dev venv and the **Railway CLI** (user-local install to
`~/.railway/bin/railway`).

**Non-interactive auth:** set `RAILWAY_TOKEN` in Cursor cloud-agent secrets
(project or user token from Railway → Account → Tokens). Without it,
`railway login` needs a browser and will not work in headless cloud VMs.

```bash
# After deploy, from a cloud agent or railway ssh:
railway status
railway ssh --service hermes-agent
hermes profile list
```
