"""scripts.deck.client's protocol, against a stand-in server that speaks NDJSON as flashcard-mcp's does.

tests/test_deck_contract.py runs the real server; this covers what only a misbehaving one shows.
"""

import os
import sys
import textwrap
import time
from datetime import UTC, datetime

import pytest

from scripts.deck import client as deck_client
from scripts.deck.client import DeckClient, DeckError, iso, parse_dt

SERVER = textwrap.dedent("""
    import json, sys, time
    mode = sys.argv[1]
    if mode == "silent":
        sys.stdin.read(); sys.exit(0)
    if mode == "ignore_eof":
        # A tsx wrapper's node child: it holds the pipes, and neither it nor we exit on EOF.
        import subprocess, time
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        print(json.dumps({"ready": True, "child": child.pid}), flush=True)
        while True:
            time.sleep(1)
    if mode == "crash":
        print("boom: no database", file=sys.stderr); sys.exit(3)
    print(json.dumps({"ready": True}), flush=True)
    if mode == "noise":
        for junk in ("[1, 2]", '"text"', "7", "null"):
            print(junk, flush=True)
    for line in sys.stdin:
        req = json.loads(line)
        if mode == "badbytes":  # an answer that is not text, once a call is waiting
            sys.stdout.buffer.write(b"\\xff\\xfe not utf-8\\n"); sys.stdout.buffer.flush()
            continue
        if req["method"] == "hang":
            time.sleep(60)
        if req["method"] == "fail":
            out = {"id": req["id"], "error": {"message": "nope"}}
        elif req["method"] == "die":
            sys.exit(1)
        else:
            out = {"id": req["id"], "result": {"method": req["method"], "params": req["params"]}}
        print(json.dumps(out), flush=True)
""")


def server(mode="ok", **kw):
    return DeckClient(command=[sys.executable, "-c", SERVER, mode], **kw)


def test_a_call_gets_its_own_answer():
    with server() as deck:
        assert deck.call("echo", a=1) == {"method": "echo", "params": {"a": 1}}
        assert deck.call("echo") == {"method": "echo", "params": {}}


def test_an_error_answer_raises_deck_error_with_its_message():
    with server() as deck, pytest.raises(DeckError, match="nope"):
        deck.call("fail")


def test_calls_from_several_threads_are_each_answered_correctly():
    from concurrent.futures import ThreadPoolExecutor

    with server() as deck, ThreadPoolExecutor(8) as pool:
        out = list(pool.map(lambda i: deck.call("echo", i=i)["params"]["i"], range(40)))
    assert out == list(range(40))


def test_a_server_that_dies_mid_call_raises_instead_of_hanging():
    with server() as deck, pytest.raises(DeckError, match="stopped"):
        deck.call("die")


def test_a_server_that_exits_before_ready_says_why():
    with pytest.raises(DeckError, match="boom: no database"):
        server("crash").start()


def test_a_server_that_never_says_ready_times_out(monkeypatch):
    monkeypatch.setattr(deck_client, "READY_TIMEOUT", 0.3)
    with pytest.raises(DeckError, match="did not start"):
        server("silent").start()


def test_a_wrong_checkout_is_told_to_fix_env_local(monkeypatch, tmp_path):
    monkeypatch.setenv("FLASHCARD_MCP_DIR", str(tmp_path))
    with pytest.raises(DeckError, match=r"\.env\.local"):
        DeckClient().start()


def test_calling_before_start_raises():
    with pytest.raises(DeckError, match="not running"):
        DeckClient().call("echo")


def test_the_typed_helpers_send_the_wire_names_and_parse_what_comes_back(monkeypatch):
    deck = DeckClient()
    sent = []
    monkeypatch.setattr(deck, "call", lambda method, **p: sent.append((method, p)) or [])
    deck.card_records(ids=["a"], inherited_from="p", include_suspended=False)
    deck.review_records(["a"])
    deck.sync_apply(deletions=["x"], scheduler_options={"newPerDay": 5})
    assert sent == [
        ("cardRecords", {"includeSuspended": False, "ids": ["a"], "inheritedFrom": "p"}),
        ("reviewRecords", {"cardIds": ["a"]}),
        ("syncApply", {"_timeout": None, "deletions": ["x"], "schedulerOptions": {"newPerDay": 5}}),
    ]


def test_datetimes_cross_as_iso_utc_and_come_back_aware():
    at = datetime(2026, 9, 2, 12, 0, 1, 250000, tzinfo=UTC)
    assert iso(at) == "2026-09-02T12:00:01.250Z"
    assert parse_dt(iso(at)) == at
    assert parse_dt(None) is None


def test_a_non_object_line_does_not_kill_the_reader():
    with server("noise") as deck:
        assert deck.call("echo", a=1)["params"] == {"a": 1}


def test_an_unreadable_line_fails_the_waiting_call_instead_of_hanging():
    with server("badbytes") as deck, pytest.raises(DeckError, match="unreadable"):
        deck.call("echo")


def test_a_call_that_is_never_answered_times_out_and_the_server_is_killed():
    with server(call_timeout=0.3) as deck:
        started = time.monotonic()
        with pytest.raises(DeckError, match='did not answer "hang" within 0.3s'):
            deck.call("hang")
        assert time.monotonic() - started < 5
        with pytest.raises(DeckError, match="did not answer"):  # later calls fail at once, with the same reason
            deck.call("echo")


def test_a_per_call_timeout_overrides_the_clients():
    with server(call_timeout=60) as deck, pytest.raises(DeckError, match="within 0.2s"):
        deck.call("hang", _timeout=0.2)


def test_close_does_not_hang_on_a_server_that_ignores_eof_and_a_child_that_holds_the_pipe(monkeypatch):
    monkeypatch.setattr(DeckClient, "CLOSE_GRACE", 0.2)
    deck = server("ignore_eof")
    deck.start()
    started = time.monotonic()
    deck.close()
    assert time.monotonic() - started < 5


def test_close_leaves_no_process_of_the_servers_group_behind(monkeypatch):
    monkeypatch.setattr(DeckClient, "CLOSE_GRACE", 0.2)
    deck = server("ignore_eof")
    deck.start()
    pgid = deck._proc.pid
    deck.close()
    time.sleep(0.2)
    with pytest.raises(ProcessLookupError):
        os.killpg(pgid, 0)


def test_a_missing_executable_is_a_deck_error():
    with pytest.raises(DeckError, match="could not start"):
        DeckClient(command=["/no/such/tsx", "server.ts"]).start()


def _checkout(tmp_path, monkeypatch):
    fc = tmp_path / "fc"
    (fc / "node_modules" / ".bin").mkdir(parents=True)
    (fc / "src" / "app").mkdir(parents=True)
    (fc / "node_modules" / ".bin" / "tsx").write_text("")
    (fc / "src" / "app" / "server.ts").write_text("")
    monkeypatch.setenv("FLASHCARD_MCP_DIR", str(fc))
    return fc


def test_a_missing_deck_file_fails_loudly_instead_of_being_created(tmp_path, monkeypatch):
    _checkout(tmp_path, monkeypatch)
    monkeypatch.setenv("FLASHCARD_MASTER_DB", str(tmp_path / "typo.db"))
    with pytest.raises(DeckError, match=r"no deck database at .*typo\.db.*FLASHCARD_MASTER_DB"):
        DeckClient().start()
    assert not (tmp_path / "typo.db").exists()


def test_a_relative_deck_path_is_taken_from_this_processs_cwd_not_the_servers(tmp_path, monkeypatch):
    fc = _checkout(tmp_path, monkeypatch)
    (tmp_path / "here.db").write_text("")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FLASHCARD_MASTER_DB", "here.db")
    seen = {}

    def fake_popen(argv, cwd, env, **_):
        seen.update(cwd=cwd, env=env)
        raise OSError("stop here")

    monkeypatch.setattr(deck_client.subprocess, "Popen", fake_popen)
    with pytest.raises(DeckError, match="could not start"):
        DeckClient().start()
    assert seen["cwd"] == fc and seen["env"]["DATABASE_URL"] == f"file:{tmp_path / 'here.db'}"
