"""The only way Python reaches the flashcard deck: flashcard-mcp's app server over stdio.

master.db belongs to flashcard-mcp, which alone knows what its columns mean (the
tombstone and cascade on a delete, which stability a non-New card may hold, the
content rules). anki-sync, the card-quality gate and the sweep used to open the file
and run SQL of their own, and each had to re-derive those rules; now they ask the deck
SDK (`flashcard-mcp/src/sdk/`) through the app server's NDJSON protocol:

    -> {"id": 1, "method": "cardRecords", "params": {...}}
    <- {"id": 1, "result": ...}  or  {"id": 1, "error": {"message": ...}}

with one `{"ready": true}` line first. One spawn costs about a second of tsx, so a
caller opens one client per run (`with DeckClient() as deck:`).

`scripts/config.py#master_db()` stays the one place that resolves the database file;
this turns it into the server's `DATABASE_URL`. Datetimes cross the wire as ISO-8601
UTC strings and come back here as aware datetimes.
"""

import contextlib
import itertools
import json
import os
import signal
import subprocess
import threading
from collections.abc import Iterable
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.config import ENV_FILE, flashcard_mcp_dir, master_db

READY_TIMEOUT = 20  # seconds for the server to open the database and say it is ready
CALL_TIMEOUT = 120  # seconds a call may take before the server is taken for wedged


class DeckError(Exception):
    """The deck refused a call, or could not be reached."""


def parse_dt(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value).astimezone(UTC)


def iso(value: datetime) -> str:
    """A datetime as the server reads one: ISO-8601, UTC, millisecond precision."""
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class CardRecord:
    """A card as `cardRecords` returns it (flashcard-mcp's src/core/card-records.ts)."""

    id: str
    deck_id: str
    deck: str
    front: str
    back: str
    tags: tuple[str, ...]
    type: str
    exercise: str | None  # a code card's exercise JSON exactly as stored
    suspended: bool
    due: datetime
    stability: float
    difficulty: float
    reps: int
    lapses: int
    state: int  # ts-fsrs: 0 new, 1 learning, 2 review, 3 relearning
    last_review: datetime | None
    interval: float
    inherited_from: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_wire(cls, r: dict[str, Any]) -> "CardRecord":
        return cls(
            id=r["id"],
            deck_id=r["deckId"],
            deck=r["deck"],
            front=r["front"],
            back=r["back"],
            tags=tuple(r["tags"]),
            type=r["type"],
            exercise=r["exercise"],
            suspended=r["suspended"],
            due=parse_dt(r["due"]),
            stability=r["stability"],
            difficulty=r["difficulty"],
            reps=r["reps"],
            lapses=r["lapses"],
            state=r["state"],
            last_review=parse_dt(r["lastReview"]),
            interval=r["interval"],
            inherited_from=r["inheritedFrom"],
            created_at=parse_dt(r["createdAt"]),
            updated_at=parse_dt(r["updatedAt"]),
        )


@dataclass(frozen=True)
class ReviewRecord:
    card_id: str
    reviewed_at: datetime
    rating: int
    response_ms: int | None
    state: int | None  # the card's state before the review; None on old rows

    @classmethod
    def from_wire(cls, r: dict[str, Any]) -> "ReviewRecord":
        return cls(r["cardId"], parse_dt(r["reviewedAt"]), r["rating"], r["responseMs"], r["state"])


def server_command(directory: Path) -> list[str]:
    return [str(directory / "node_modules" / ".bin" / "tsx"), str(directory / "src" / "app" / "server.ts")]


class DeckClient:
    """One app-server process, spoken to over its stdin/stdout. Safe to call from several threads."""

    CLOSE_GRACE = 5  # seconds the server gets to exit on its own once stdin is closed

    def __init__(self, command: list[str] | None = None, cwd: Path | None = None,
                 call_timeout: float = CALL_TIMEOUT) -> None:
        """`command` and `cwd` replace the flashcard-mcp app server; for tests of the protocol itself."""
        self._command = command
        self._cwd = cwd
        self._call_timeout = call_timeout
        self._proc: subprocess.Popen | None = None
        self._reader: threading.Thread | None = None
        self._pending: dict[int, Future] = {}
        self._ids = itertools.count(1)
        self._write_lock = threading.Lock()
        self._stderr: list[str] = []
        self._died: DeckError | None = None

    def __enter__(self) -> "DeckClient":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def start(self) -> None:
        env = {**os.environ, "NODE_NO_WARNINGS": "1"}
        if self._command is not None:
            argv, directory = self._command, self._cwd
        else:
            try:
                directory = flashcard_mcp_dir()
                db = master_db().resolve()  # against this process's cwd, not the server's
            except RuntimeError as e:  # FLASHCARD_MCP_DIR unset: the message already names .env.local
                raise DeckError(str(e)) from None
            argv = server_command(directory)
            if not Path(argv[0]).exists() or not Path(argv[1]).exists():
                raise DeckError(
                    f"no flashcard-mcp app server at {directory} (is FLASHCARD_MCP_DIR in {ENV_FILE} right, "
                    "and `npm install` run there?)"
                )
            if not db.is_file():
                # The server would create an empty deck at a wrong path and report an empty collection.
                raise DeckError(
                    f"no deck database at {db} (check FLASHCARD_MCP_DIR in {ENV_FILE}, "
                    "or FLASHCARD_MASTER_DB if it is set)"
                )
            env["DATABASE_URL"] = f"file:{db}"
        try:
            # Its own session, so a kill reaches tsx's node child too (killpg) and not just the wrapper.
            self._proc = subprocess.Popen(
                argv, cwd=directory, env=env, text=True, bufsize=1, start_new_session=True,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
        except OSError as e:  # no node, no tsx, an unusable cwd
            raise DeckError(f"could not start the deck server ({e})") from None
        # stderr is drained so a chatty child never blocks on a full pipe; the tail explains a crash.
        threading.Thread(target=self._drain_stderr, args=(self._proc,), daemon=True).start()
        ready: Future = Future()
        self._reader = threading.Thread(target=self._read, args=(self._proc, ready), daemon=True)
        self._reader.start()
        try:
            ready.result(timeout=READY_TIMEOUT)
        except Exception as e:
            self.close()
            raise DeckError(f"the deck server did not start ({str(e) or 'timed out'}){self._stderr_tail()}") from None

    def _drain_stderr(self, proc: subprocess.Popen) -> None:
        with contextlib.closing(proc.stderr):
            for line in proc.stderr:
                self._stderr.append(line.rstrip())
                del self._stderr[:-20]

    def _stderr_tail(self) -> str:
        tail = "\n".join(self._stderr[-5:])
        return f"\n{tail}" if tail else ""

    def _read(self, proc: subprocess.Popen, ready: Future) -> None:
        """Route responses to their callers. Owns stdout, so only it closes it: closing a pipe another
        thread is blocked reading waits on that thread's lock, and a grandchild holding the pipe open
        would make that forever."""
        failure: DeckError | None = None
        try:
            with contextlib.closing(proc.stdout):
                for line in proc.stdout:
                    try:
                        msg = json.loads(line)
                    except ValueError:
                        continue
                    if not isinstance(msg, dict):
                        continue
                    if msg.get("ready"):
                        if not ready.done():
                            ready.set_result(True)
                        continue
                    future = self._pending.pop(msg.get("id"), None)
                    if future is None or future.done():
                        continue
                    if "error" in msg:
                        error = msg["error"]
                        future.set_exception(DeckError(error.get("message", "unknown error")
                                                       if isinstance(error, dict) else str(error)))
                    else:
                        future.set_result(msg.get("result"))
        except Exception as e:  # noqa: BLE001 (whatever it was, nothing waiting may be left hanging)
            failure = DeckError(f"the deck server sent something unreadable ({e})")
            self._kill(proc)
        # The pipe closed: the server exited. Nothing still waiting will be answered.
        died = failure or DeckError(f"the deck server stopped{self._stderr_tail()}")
        if self._died is None:
            self._died = died
        if not ready.done():
            ready.set_exception(self._died)
        for future in list(self._pending.values()):
            if not future.done():
                future.set_exception(self._died)
        self._pending.clear()

    @staticmethod
    def _kill(proc: subprocess.Popen) -> None:
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(proc.pid, signal.SIGKILL)

    def call(self, method: str, _timeout: float | None = None, **params: Any) -> Any:
        """One request; `_timeout` seconds (default: the client's) before it fails and the server is killed."""
        if self._died is not None:
            raise self._died
        proc = self._proc
        if proc is None or proc.poll() is not None:
            raise DeckError("the deck server is not running")
        request_id = next(self._ids)
        future: Future = Future()
        self._pending[request_id] = future
        if self._died is not None:  # the reader finished between the check above and the registration
            self._pending.pop(request_id, None)
            raise self._died
        line = json.dumps({"id": request_id, "method": method, "params": params})
        try:
            with self._write_lock:
                proc.stdin.write(line + "\n")
                proc.stdin.flush()
        except (OSError, ValueError) as e:
            self._pending.pop(request_id, None)
            raise DeckError(f"the deck server is gone ({e})") from None
        timeout = self._call_timeout if _timeout is None else _timeout
        try:
            return future.result(timeout=timeout)
        except FutureTimeout:
            # A server that stopped answering is wedged: kill it, and every later call fails fast
            # with this reason instead of waiting out its own timeout.
            self._pending.pop(request_id, None)
            error = DeckError(f'the deck did not answer "{method}" within {timeout:g}s')
            self._died = self._died or error
            self._kill(proc)
            raise error from None

    def close(self) -> None:
        proc, self._proc = self._proc, None
        reader, self._reader = self._reader, None
        if proc is None:
            return
        with contextlib.suppress(OSError, ValueError):
            proc.stdin.close()  # the server exits when its stdin closes
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=self.CLOSE_GRACE)
        self._kill(proc)  # also what a wrapper that exited leaves behind: its node child
        proc.wait()
        if reader is not None:
            reader.join(timeout=5)

    # ---- typed helpers: what callers actually use ----

    def card_records(
        self,
        ids: Iterable[str] | None = None,
        inherited_from: str | None = None,
        include_suspended: bool = True,
    ) -> list[CardRecord]:
        params: dict[str, Any] = {"includeSuspended": include_suspended}
        if ids is not None:
            params["ids"] = list(ids)
        if inherited_from is not None:
            params["inheritedFrom"] = inherited_from
        return [CardRecord.from_wire(r) for r in self.call("cardRecords", **params)]

    def review_records(self, card_ids: Iterable[str] | None = None) -> list[ReviewRecord]:
        params = {} if card_ids is None else {"cardIds": list(card_ids)}
        return [ReviewRecord.from_wire(r) for r in self.call("reviewRecords", **params)]

    def tombstones(self) -> set[str]:
        """Ids of cards deleted here."""
        return set(self.call("tombstones"))

    def sync_apply(
        self,
        *,
        schedules: list[dict] | None = None,
        reviews: list[dict] | None = None,
        imports: list[dict] | None = None,
        deletions: list[str] | None = None,
        scheduler_options: dict | None = None,
        timeout: float | None = None,
    ) -> dict:
        """Apply an anki-sync plan in one transaction; entries are the wire shapes, datetimes via `iso`.

        `timeout` overrides the client's call timeout, for a plan that may take long."""
        params: dict[str, Any] = {}
        for name, value in (("schedules", schedules), ("reviews", reviews), ("imports", imports),
                            ("deletions", deletions), ("schedulerOptions", scheduler_options)):
            if value is not None:
                params[name] = value
        return self.call("syncApply", _timeout=timeout, **params)
