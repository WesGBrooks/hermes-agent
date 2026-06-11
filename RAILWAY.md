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
