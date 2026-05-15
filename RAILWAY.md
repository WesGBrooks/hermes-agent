# Railway Deployment Notes

This branch is intended to stay close to upstream Hermes while carrying the
small Railway-specific deployment patch.

## Recommended Branch Flow

- Keep `main` tracking `upstream/main`.
- Deploy Railway from the long-lived `railway` branch.
- Merge `main` into `railway` whenever you want upstream updates.
- Keep Railway-only changes small and obvious: `railway.json`, `railway.env.template`,
  this note, and the Dockerfile runtime patch that removes the unsupported Docker `VOLUME`.

Suggested sync:

```bash
git fetch upstream
git switch main
git merge upstream/main
git switch railway
git merge main
git push origin main railway
```

After each sync, verify the Dockerfile still has no active `VOLUME` instruction:

```bash
rg -n '^[[:space:]]*VOLUME' Dockerfile
```

That command should print nothing. Railway persistence should be configured as a
Railway Volume mounted at `/opt/data`.

## Railway Service Setup

Use the `hermes-agent` service in the `hermes` Railway project and configure it
to deploy from the `railway` branch of this fork.

Required service configuration:

- Builder: Dockerfile
- Dockerfile path: `Dockerfile`
- Volume mount: `/opt/data`
- Required secrets: at least one model provider key, usually `OPENROUTER_API_KEY`
- Required messaging credentials: for example `TELEGRAM_BOT_TOKEN`,
  `DISCORD_BOT_TOKEN`, or Slack credentials

The Docker image defaults to `hermes gateway`, so the container starts as the
always-on messaging gateway. The entrypoint bootstraps `/opt/data` with
`config.yaml`, `.env`, sessions, logs, skills, and other Hermes state.

### Environment variables (Railway dashboard)

`railway.json` only configures build and deploy; Railway config-as-code does not
embed secret values. Put API keys and tokens in **Railway → Service → Variables**.

- **Checklist:** `railway.env.template` is **auto-generated**. It lists Hermes
  credential-style variable *names* (LLM keys, messaging tokens, tool APIs,
  webhooks, Langfuse, bootstrap JSON, etc.). It is derived from
  `OPTIONAL_ENV_VARS` (`password: true`), `_EXTRA_ENV_KEYS`, and
  `website/docs/reference/environment-variables.md`. Open it, copy the lines you
  need into the Railway **RAW** variables editor, and set values in the
  UI—never commit real secrets. WhatsApp pairing still lives in the volume under
  `HERMES_HOME` (session files), not in this list.
- **Regenerate:** From the repo root, run
  `python scripts/generate_railway_env_template.py` after changing
  `hermes_cli/config.py` env metadata, the environment-variables reference doc, or
  the generator script itself; commit the updated `railway.env.template`. CI runs
  `.github/workflows/railway-env-template.yml` on `main` and `railway` when those
  paths change: it executes `python scripts/generate_railway_env_template.py --check`
  and a small pytest module.
- **Precedence:** Hermes reads **process environment first**, then
  `HERMES_HOME/.env` (`get_env_value()` in `hermes_cli/config.py`). Railway
  injects the process environment, so dashboard variables override the
  first-boot `.env` seeded from `.env.example` under `/opt/data`.
- **Rotations:** Update values in Railway when keys change; that triggers a new
  deploy with the updated secrets while your image build can stay unchanged.

For stable Telegram webhooks, point `TELEGRAM_WEBHOOK_URL` at your service’s
public hostname (Railway networking) instead of churning preview URLs in git.

Use Railway SSH for first-time interactive setup or verification only:

```bash
railway ssh --service hermes-agent
hermes gateway setup
hermes gateway status
```

Do not put API keys in this repository. Store secrets in Railway variables or in
the mounted `/opt/data/.env` file.
