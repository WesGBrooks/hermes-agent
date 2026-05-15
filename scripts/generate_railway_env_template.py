#!/usr/bin/env python3
"""Regenerate ``railway.env.template`` from Hermes env-var sources of truth.

Sources:
  * ``hermes_cli.config.OPTIONAL_ENV_VARS`` (``password: true`` + Langfuse public keys)
  * ``hermes_cli.config._EXTRA_ENV_KEYS`` (secret-shaped entries)
  * ``website/docs/reference/environment-variables.md`` (credential-shaped table names)
  * Explicit bootstrap / path secrets (see ``collect_keys()``)

Usage:
  python scripts/generate_railway_env_template.py              # write railway.env.template
  python scripts/generate_railway_env_template.py --check      # exit 1 if file would change

Run from the repository root (or any cwd — paths are anchored to the repo).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "railway.env.template"
ENV_DOCS = REPO_ROOT / "website" / "docs" / "reference" / "environment-variables.md"


def collect_keys() -> set[str]:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from hermes_cli.config import OPTIONAL_ENV_VARS, _EXTRA_ENV_KEYS

    keys: set[str] = {
        k for k, v in OPTIONAL_ENV_VARS.items() if v.get("password") is True
    }
    for k in ("HERMES_LANGFUSE_PUBLIC_KEY", "LANGFUSE_PUBLIC_KEY"):
        if k in OPTIONAL_ENV_VARS:
            keys.add(k)

    _extra_pat = re.compile(
        r"(SECRET|PASSWORD|TOKEN|API_KEY|CLIENT_SECRET|_KEY$|ENCRYPT_KEY|VERIFICATION_TOKEN|"
        r"ENCODING_AES|CREDENTIALS|ACCOUNT_SID|AUTH_TOKEN|BOT_ID$|ACCOUNT_ID$)",
        re.I,
    )
    for k in _EXTRA_ENV_KEYS:
        if _extra_pat.search(k):
            if "HOME_CHANNEL" in k or "HOME_ADDRESS" in k or "_CHANNEL_NAME" in k:
                continue
            keys.add(k)

    if ENV_DOCS.is_file():
        md = ENV_DOCS.read_text(encoding="utf-8")
        md_names = set(re.findall(r"\|\s*`([A-Z][A-Z0-9_]+)`\s*\|", md))
        _cred = re.compile(
            r"(API_KEY|_API_KEY|_KEY$|TOKEN|SECRET|PASSWORD|CREDENTIAL|AUTH_TOKEN|_SID$|ACCESS_TOKEN|"
            r"RECOVERY_KEY|WEBHOOK_SECRET|CLIENT_SECRET|ENCRYPT_KEY|VERIFICATION_TOKEN|BOT_TOKEN|APP_TOKEN|"
            r"FAL_KEY|HF_TOKEN|INCOMING_WEBHOOK|GRAPH_ACCESS_TOKEN|CLIENT_STATE|OIDC_TOKEN|"
            r"SERVICE_ACCOUNT_JSON|APPLICATION_CREDENTIALS|HASS_TOKEN|AUTH_JSON_BOOTSTRAP|"
            r"SESSION_KEY|ACCOUNT_SID|AUTH_TOKEN)",
            re.I,
        )
        for k in md_names:
            if _cred.search(k):
                keys.add(k)

    keys.add("HERMES_AUTH_JSON_BOOTSTRAP")
    keys.add("GOOGLE_APPLICATION_CREDENTIALS")
    for k in ("QQ_APP_ID", "DINGTALK_CLIENT_ID", "FEISHU_APP_ID"):
        keys.add(k)

    keys.discard("HERMES_REDACT_SECRETS")
    keys.discard("SMS_INSECURE_NO_SIGNATURE")
    for k in list(keys):
        if k.endswith("_BASE_URL"):
            keys.discard(k)
    return keys


def _section_for(name: str) -> str:
    if name == "HERMES_AUTH_JSON_BOOTSTRAP":
        return "Bootstrap & automation"
    if name.startswith(
        (
            "OPENROUTER_",
            "OPENAI_",
            "ANTHROPIC",
            "GOOGLE_API",
            "GEMINI_",
            "NOUS_",
            "AI_GATEWAY",
            "HF_",
            "OLLAMA_",
            "XAI_",
            "MISTRAL_",
            "DEEPSEEK_",
            "NVIDIA_",
            "DASHSCOPE_",
            "AZURE_",
            "LM_",
            "GLM_",
            "ZAI_",
            "Z_AI_",
            "KIMI_",
            "ARCEE",
            "GMI_",
            "MINIMAX_",
            "STEPFUN_",
            "XIAOMI_",
            "TOKENHUB_",
            "OPENCODE_",
            "CLAUDE_CODE",
            "HERMES_GEMINI_CLIENT",
            "HERMES_QWEN",
            "KILOCODE_",
            "ALIBABA_",
            "AUXILIARY_",
        )
    ):
        return "LLM / inference providers"
    if name in {"COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"}:
        return "Copilot / GitHub auth"
    if name.startswith(("TERMINAL_SSH_KEY", "DAYTONA_", "VERCEL_TOKEN", "VERCEL_OIDC_TOKEN")):
        return "Terminal & sandbox"
    if name.startswith(("HERMES_LANGFUSE", "LANGFUSE_", "TINKER_", "WANDB_")):
        return "Observability & RL"
    if name in {
        "FAL_KEY",
        "VOICE_TOOLS_OPENAI_KEY",
        "ELEVENLABS_API_KEY",
        "GROQ_API_KEY",
    } or name.startswith("CAMOFOX_SESSION_KEY"):
        return "Image / voice / media"
    if name in {
        "TELEGRAM_BOT_TOKEN",
        "DISCORD_BOT_TOKEN",
        "SLACK_BOT_TOKEN",
        "SLACK_APP_TOKEN",
        "MATTERMOST_TOKEN",
        "MATRIX_ACCESS_TOKEN",
        "MATRIX_PASSWORD",
        "MATRIX_RECOVERY_KEY",
        "LINE_CHANNEL_ACCESS_TOKEN",
        "LINE_CHANNEL_SECRET",
        "BLUEBUBBLES_PASSWORD",
        "HASS_TOKEN",
        "QQ_CLIENT_SECRET",
        "QQ_APP_ID",
    }:
        return "Messaging — core tokens"
    if name in {
        "TELEGRAM_WEBHOOK_SECRET",
        "WEBHOOK_SECRET",
        "API_SERVER_KEY",
        "GATEWAY_PROXY_KEY",
        "MSGRAPH_WEBHOOK_CLIENT_STATE",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_ACCOUNT_SID",
        "TEAMS_INCOMING_WEBHOOK_URL",
        "TEAMS_GRAPH_ACCESS_TOKEN",
    }:
        return "Messaging — webhooks & shared secrets"
    if name.startswith(("DINGTALK_", "FEISHU_", "WECOM_", "WEIXIN_", "EMAIL_PASSWORD")):
        return "Messaging — enterprise / regional"
    if name == "DINGTALK_CLIENT_ID":
        return "Messaging — enterprise / regional"
    if name.startswith(("GOOGLE_CHAT_SERVICE_ACCOUNT", "GOOGLE_APPLICATION_CREDENTIALS", "MSGRAPH_CLIENT")):
        return "GCP / Google (credentials paths or JSON)"
    if name.startswith(("TEAMS_CLIENT", "IRC_", "SUDO_PASSWORD")) or name == "TOOL_GATEWAY_USER_TOKEN":
        return "Other documented secrets"
    return "Tool APIs & search"


_SECTION_ORDER = [
    "LLM / inference providers",
    "Copilot / GitHub auth",
    "Tool APIs & search",
    "Image / voice / media",
    "Terminal & sandbox",
    "Observability & RL",
    "Messaging — core tokens",
    "Messaging — webhooks & shared secrets",
    "Messaging — enterprise / regional",
    "GCP / Google (credentials paths or JSON)",
    "Other documented secrets",
    "Bootstrap & automation",
]


def build_template_text(keys: set[str] | None = None) -> str:
    if keys is None:
        keys = collect_keys()
    sections: dict[str, list[str]] = {h: [] for h in _SECTION_ORDER}
    for k in keys:
        sections[_section_for(k)].append(k)

    lines = [
        "# AUTO-GENERATED — do not edit by hand.",
        "#",
        "# Regenerate:",
        "#   python scripts/generate_railway_env_template.py",
        "#",
        "# Hermes on Railway — API keys, tokens, and shared secrets (empty values).",
        "# Sources: hermes_cli.config.OPTIONAL_ENV_VARS (password: true),",
        "# _EXTRA_ENV_KEYS (secret-shaped), website/docs/reference/environment-variables.md,",
        "# and explicit bootstrap vars. See scripts/generate_railway_env_template.py.",
        "#",
        "# Set values in the Railway web UI or another secret manager — never commit secrets.",
        "# Hermes reads process environment before ~/.hermes/.env (get_env_value).",
        "#",
        "# Canonical docs: website/docs/reference/environment-variables.md",
        "#",
    ]
    for title in _SECTION_ORDER:
        names = sorted(set(sections[title]))
        if not names:
            continue
        lines.append("")
        lines.append("# " + "=" * 72)
        lines.append(f"# {title}")
        lines.append("# " + "=" * 72)
        for name in names:
            lines.append(f"{name}=")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--check",
        action="store_true",
        help="exit with status 1 if the template would change (does not write)",
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"output path (default: {DEFAULT_OUTPUT})",
    )
    args = p.parse_args(argv)
    keys = collect_keys()
    text = build_template_text(keys)
    out: Path = args.output
    if args.check:
        if not out.is_file():
            print(f"error: missing {out} — run without --check to create it", file=sys.stderr)
            return 1
        existing = out.read_text(encoding="utf-8")
        if existing != text:
            print(
                "railway.env.template is out of date.\n"
                "Regenerate from the repo root with:\n"
                "  python scripts/generate_railway_env_template.py",
                file=sys.stderr,
            )
            return 1
        print(f"{out} is up to date ({len(keys)} variables)")
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"Wrote {out} ({len(keys)} variables)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
