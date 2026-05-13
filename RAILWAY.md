# Railway Deployment Notes

This branch is intended to stay close to upstream Hermes while carrying the
small Railway-specific deployment patch.

## Recommended Branch Flow

- Keep `main` tracking `upstream/main`.
- Deploy Railway from the long-lived `railway` branch.
- Merge `main` into `railway` whenever you want upstream updates.
- Keep Railway-only changes small and obvious: `railway.json`, this note, and
  the Dockerfile runtime patch that removes the unsupported Docker `VOLUME`.

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

Use Railway SSH for first-time interactive setup or verification only:

```bash
railway ssh --service hermes-agent
hermes gateway setup
hermes gateway status
```

Do not put API keys in this repository. Store secrets in Railway variables or in
the mounted `/opt/data/.env` file.
