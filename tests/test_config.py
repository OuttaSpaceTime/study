"""Tests for scripts.config — the per-machine flashcard-mcp location.

The path differs per machine and must never be committed, so it is resolved
from FLASHCARD_MCP_DIR in the environment or in a gitignored .env.local.
"""

import re
from pathlib import Path

import pytest

from scripts import config


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv("FLASHCARD_MCP_DIR", raising=False)
    monkeypatch.delenv("FLASHCARD_MASTER_DB", raising=False)


def _env_file(tmp_path: Path, body: str) -> Path:
    path = tmp_path / ".env.local"
    path.write_text(body)
    return path


def test_load_env_file_ignores_comments_blanks_and_quotes(tmp_path):
    env = _env_file(tmp_path, '# a comment\n\nFLASHCARD_MCP_DIR="/opt/fc"\nOTHER=x\n')
    assert config.load_env_file(env) == {"FLASHCARD_MCP_DIR": "/opt/fc", "OTHER": "x"}


def test_load_env_file_missing_returns_empty(tmp_path):
    assert config.load_env_file(tmp_path / "nope") == {}


def test_dir_reads_env_file(tmp_path):
    env = _env_file(tmp_path, "FLASHCARD_MCP_DIR=/home/felix/Code/Misc/flashcard-mcp\n")
    assert config.flashcard_mcp_dir(env) == Path("/home/felix/Code/Misc/flashcard-mcp")


def test_dir_prefers_environment_over_env_file(tmp_path, monkeypatch):
    env = _env_file(tmp_path, "FLASHCARD_MCP_DIR=/from/file\n")
    monkeypatch.setenv("FLASHCARD_MCP_DIR", "/from/environ")
    assert config.flashcard_mcp_dir(env) == Path("/from/environ")


def test_dir_expands_tilde(tmp_path):
    env = _env_file(tmp_path, "FLASHCARD_MCP_DIR=~/Code/flashcard-mcp\n")
    assert config.flashcard_mcp_dir(env) == Path.home() / "Code/flashcard-mcp"


def test_dir_unset_raises_naming_the_env_file(tmp_path):
    env = tmp_path / ".env.local"
    with pytest.raises(RuntimeError) as excinfo:
        config.flashcard_mcp_dir(env)
    assert "FLASHCARD_MCP_DIR" in str(excinfo.value)
    assert str(env) in str(excinfo.value)


def test_master_db_derives_from_dir(tmp_path):
    env = _env_file(tmp_path, "FLASHCARD_MCP_DIR=/opt/fc\n")
    assert config.master_db(env) == Path("/opt/fc/prisma/master.db")


def test_master_db_override_wins(tmp_path, monkeypatch):
    env = _env_file(tmp_path, "FLASHCARD_MCP_DIR=/opt/fc\n")
    monkeypatch.setenv("FLASHCARD_MASTER_DB", "/tmp/other.db")
    assert config.master_db(env) == Path("/tmp/other.db")


def test_repo_env_file_is_at_repo_root():
    assert config.ENV_FILE == config.REPO_ROOT / ".env.local"
    assert (config.REPO_ROOT / "AGENTS.md").exists()


HARDCODED_HOME = re.compile(r"/home/[a-z]+/[\w./-]*flashcard-mcp")

GUARDED_FILES = [
    ".mcp.json",
    "scripts/ankisync/master.py",
    "scripts/deck/client.py",
    "scripts/flashcard-mcp-server",
    "wiki-viewer/lib/flashcards.ts",
    "wiki-viewer/lib/calibration.ts",
    "wiki-viewer/lib/flashcard-path.ts",
]


@pytest.mark.parametrize("relpath", GUARDED_FILES)
def test_no_machine_specific_path_is_committed(relpath):
    """A path baked into one laptop's home dir breaks every other machine."""
    path = config.REPO_ROOT / relpath
    assert path.exists(), f"{relpath} is missing"
    found = HARDCODED_HOME.findall(path.read_text())
    assert not found, f"{relpath} hardcodes {found}; resolve via .env.local instead"


def test_deck_client_resolves_db_through_config(monkeypatch, tmp_path):
    """The deck server gets its database from config.master_db(), nowhere else."""
    from scripts.deck import client

    started = {}

    class Stop(Exception):
        pass

    def fake_popen(argv, cwd, env, **_):
        started.update(argv=argv, cwd=cwd, env=env)
        raise Stop

    fc = tmp_path / "fc"
    (fc / "node_modules" / ".bin").mkdir(parents=True)
    (fc / "src" / "app").mkdir(parents=True)
    (fc / "node_modules" / ".bin" / "tsx").write_text("")
    (fc / "src" / "app" / "server.ts").write_text("")
    (fc / "prisma").mkdir()
    (fc / "prisma" / "master.db").write_text("")
    monkeypatch.setenv("FLASHCARD_MCP_DIR", str(fc))
    monkeypatch.delenv("FLASHCARD_MASTER_DB", raising=False)
    monkeypatch.setattr(client.subprocess, "Popen", fake_popen)
    with pytest.raises(Stop):
        client.DeckClient().start()
    assert started["env"]["DATABASE_URL"] == f"file:{(fc / 'prisma' / 'master.db').resolve()}"
    assert started["cwd"] == fc


def test_deck_client_names_env_local_when_the_dir_is_unset(monkeypatch, tmp_path):
    from scripts.deck import client

    monkeypatch.delenv("FLASHCARD_MCP_DIR", raising=False)
    monkeypatch.setattr(config, "ENV_FILE", tmp_path / "none")
    monkeypatch.setattr(client, "flashcard_mcp_dir", lambda: config.flashcard_mcp_dir(tmp_path / "none"))
    with pytest.raises(client.DeckError, match="FLASHCARD_MCP_DIR"):
        client.DeckClient().start()
