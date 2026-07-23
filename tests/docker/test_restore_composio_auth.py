"""Unit tests for docker/restore_composio_auth.sh (no Docker required)."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "docker" / "restore_composio_auth.sh"


def _run(env: dict[str, str], hermes_home: Path) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged.update(env)
    merged["HERMES_HOME"] = str(hermes_home)
    return subprocess.run(
        [str(SCRIPT)],
        env=merged,
        capture_output=True,
        text=True,
        check=False,
    )


def test_skips_when_api_key_unset(tmp_path: Path) -> None:
    r = _run({}, tmp_path)
    assert r.returncode == 0
    assert "Skipping" in r.stdout
    assert not (tmp_path / "home" / ".composio" / "user_data.json").exists()


def test_writes_user_data_json(tmp_path: Path) -> None:
    r = _run(
        {
            "COMPOSIO_API_KEY": "uak_test_key",
            "COMPOSIO_ORG_ID": "org_abc",
            "COMPOSIO_TEST_USER_ID": "pg-test-user",
        },
        tmp_path,
    )
    assert r.returncode == 0
    target = tmp_path / "home" / ".composio" / "user_data.json"
    assert target.exists()
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["api_key"] == "uak_test_key"
    assert data["base_url"] == "https://backend.composio.dev"
    assert data["org_id"] == "org_abc"
    assert data["test_user_id"] == "pg-test-user"


def test_skips_rewrite_when_key_unchanged(tmp_path: Path) -> None:
    env = {
        "COMPOSIO_API_KEY": "uak_same",
        "COMPOSIO_ORG_ID": "org_1",
    }
    first = _run(env, tmp_path)
    assert first.returncode == 0
    target = tmp_path / "home" / ".composio" / "user_data.json"
    mtime = target.stat().st_mtime

    second = _run(env, tmp_path)
    assert second.returncode == 0
    assert "up to date" in second.stdout
    assert target.stat().st_mtime == mtime


def test_rewrites_when_key_changes(tmp_path: Path) -> None:
    _run({"COMPOSIO_API_KEY": "uak_old"}, tmp_path)
    target = tmp_path / "home" / ".composio" / "user_data.json"
    assert json.loads(target.read_text())["api_key"] == "uak_old"

    r = _run({"COMPOSIO_API_KEY": "uak_new"}, tmp_path)
    assert r.returncode == 0
    assert json.loads(target.read_text())["api_key"] == "uak_new"


@pytest.mark.parametrize("script_path", [SCRIPT])
def test_script_is_executable(script_path: Path) -> None:
    assert os.access(script_path, os.X_OK)
