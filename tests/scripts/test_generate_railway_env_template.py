"""Sanity checks for ``scripts/generate_railway_env_template.py``."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GEN_SCRIPT = REPO_ROOT / "scripts" / "generate_railway_env_template.py"


@pytest.fixture(scope="module")
def gen_mod():
    spec = importlib.util.spec_from_file_location("railway_env_gen", GEN_SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_generator_script_exists():
    assert GEN_SCRIPT.is_file(), "expected scripts/generate_railway_env_template.py"


def test_collect_keys_non_empty(gen_mod):
    keys = gen_mod.collect_keys()
    assert len(keys) >= 50
    assert "OPENROUTER_API_KEY" in keys
    assert "TELEGRAM_BOT_TOKEN" in keys


def test_build_template_has_no_duplicate_assignments(gen_mod):
    text = gen_mod.build_template_text()
    names = [
        line[:-1]
        for line in text.splitlines()
        if line.endswith("=") and line[0].isalpha()
    ]
    assert len(names) == len(set(names)), f"duplicates: {sorted({n for n in names if names.count(n) > 1})}"


def test_build_template_core_entries(gen_mod):
    text = gen_mod.build_template_text()
    assert "AUTO-GENERATED" in text
    assert "OPENROUTER_API_KEY=" in text
    assert "DISCORD_BOT_TOKEN=" in text
    assert "HERMES_AUTH_JSON_BOOTSTRAP=" in text
