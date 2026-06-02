#!/usr/bin/env python3
"""Set ``stt.enabled: true`` in ``$HERMES_HOME/config.yaml`` (round-trip YAML).

Used by ``docker/stage2-hook.sh`` when ``HERMES_ENSURE_STT_ENABLED`` is truthy so
operators can enable inbound voice transcription on a persisted volume without
bind-mounting a hand-edited config on first deploy.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    home = Path(os.environ.get("HERMES_HOME", "/opt/data"))
    path = home / "config.yaml"
    if not path.is_file():
        return 0

    from ruamel.yaml import YAML

    y = YAML()
    y.preserve_quotes = True
    with path.open(encoding="utf-8") as f:
        data = y.load(f)
    if data is None:
        data = {}

    stt = data.get("stt")
    if not isinstance(stt, dict):
        stt = {}
        data["stt"] = stt

    if stt.get("enabled") is True:
        return 0

    stt["enabled"] = True
    with path.open("w", encoding="utf-8") as f:
        y.dump(data, f)
    print("Updated config.yaml: stt.enabled = true", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
