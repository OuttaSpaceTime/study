"""The one writer of the daily session logs (`logs/MM/YYYY-MM-DD.md`).

Skills, scripts and Omvida all append entries here and nowhere else, so the path,
the `# YYYY-MM-DD` day header, the numbering and the entry shape have one owner.

The log is append-only: an entry is added with a single write and nothing already
in the file is touched. `## Session N` counts every session of any kind that day
(the number is read off the file just before appending), and `## Query N` has its
own sequence. An entry is the header, then one `- **Field:** value` bullet per
field, with a blank line between entries; a multi-line value continues on lines
indented two spaces. That is the dominant shape of the existing logs, which
/progress, /end and /kickoff read.
"""

from __future__ import annotations

import argparse
import fcntl
import re
import sys
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path

from .config import REPO_ROOT

SESSION = re.compile(r"^## Session (\d+)\b", re.M)
QUERY = re.compile(r"^## Query (\d+)\b", re.M)

Fields = Mapping[str, str] | Sequence[tuple[str, str]]


def log_path(repo_root: Path, now: datetime) -> Path:
    """The month folder is zero-padded, and comes from `now`, not from the repo."""
    return repo_root / "logs" / f"{now.month:02d}" / f"{now:%Y-%m-%d}.md"


def _next_number(pattern: re.Pattern[str], text: str) -> int:
    nums = [int(n) for n in pattern.findall(text)]
    return max(nums) + 1 if nums else 1


def next_session_number(text: str) -> int:
    return _next_number(SESSION, text)


def next_query_number(text: str) -> int:
    return _next_number(QUERY, text)


def format_fields(fields: Fields) -> str:
    items = fields.items() if isinstance(fields, Mapping) else fields
    lines: list[str] = []
    for name, value in items:
        first, *rest = str(value).rstrip("\n").split("\n")
        lines.append(f"- **{name}:** {first}")
        lines.extend(f"  {line}" if line else "" for line in rest)
    return "\n".join(lines) + "\n"


def _append(repo_root: Path, now: datetime, counter: re.Pattern[str], header, fields: Fields):
    """Read, number and write under an exclusive lock.

    Agents run in parallel (a Study entry from Omvida while a Change is logged),
    so reading the count and appending must be one step: without the lock two
    writers get the same N, or both write the day header.
    """
    path = log_path(repo_root, now)
    path.parent.mkdir(parents=True, exist_ok=True)
    # "a+" creates the file, reads from 0 after the seek, and always writes at the end.
    with path.open("a+", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            fh.seek(0)
            existing = fh.read()
            n = _next_number(counter, existing)
            if not existing:
                chunk = f"# {now:%Y-%m-%d}\n\n"
            elif existing.endswith("\n\n"):
                chunk = ""
            else:
                chunk = "\n" if existing.endswith("\n") else "\n\n"
            chunk += header(n) + "\n" + format_fields(fields)
            fh.write(chunk)
            fh.flush()
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)
    return path, n


def append_session(
    kind: str,
    fields: Fields,
    now: datetime | None = None,
    repo_root: Path = REPO_ROOT,
    title_suffix: str | None = None,
) -> tuple[Path, int]:
    """Append `## Session N — <Kind>[/<Suffix>] (HH:MM)`; returns the file and N."""
    now = now or datetime.now()
    label = f"{kind}/{title_suffix}" if title_suffix else kind
    return _append(
        repo_root, now, SESSION, lambda n: f"## Session {n} — {label} ({now:%H:%M})", fields
    )


def append_query(
    fields: Fields, now: datetime | None = None, repo_root: Path = REPO_ROOT
) -> tuple[Path, int]:
    """Append `## Query N (HH:MM)`, numbered apart from the sessions."""
    now = now or datetime.now()
    return _append(repo_root, now, QUERY, lambda n: f"## Query {n} ({now:%H:%M})", fields)


_FIELD_LINE = re.compile(r"^([^:\s][^:]*):[ \t]?(.*)$")


def parse_fields(text: str) -> list[tuple[str, str]]:
    """Parse the stdin form: `Name: value` lines, in order.

    A line indented two or more spaces continues the previous field's value (two
    spaces are stripped, deeper indentation is kept, as format_fields writes it).
    Blank lines are ignored. The quoted heredoc it is read from is why this form
    exists: nothing in a value is expanded by the shell.
    """
    fields: list[list[str]] = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        if raw.startswith("  "):
            if not fields:
                raise ValueError(f"continuation line before any field: {raw!r}")
            fields[-1][1] += "\n" + raw[2:]
            continue
        m = _FIELD_LINE.match(raw)
        if not m:
            raise ValueError(f"expected 'Name: value', got {raw!r}")
        fields.append([m.group(1).strip(), m.group(2)])
    return [(name, value) for name, value in fields]


def main(argv: Sequence[str] | None = None, stdin=None) -> int:
    ap = argparse.ArgumentParser(
        prog="log-append",
        description="Append an entry to today's logs/MM/YYYY-MM-DD.md; "
        "path, day header and numbering are handled here. Fields come from stdin "
        "(`Name: value` lines, continuation lines indented two spaces) or --field.",
        epilog="Example: log-append Change <<'EOF'\nFiles: a, b\nChange: did x\n  and y\nEOF",
    )
    ap.add_argument("kind", nargs="?", help="session kind: Study, Flashcard, Change, Kickoff, ...")
    ap.add_argument("--query", action="store_true", help="append a `## Query N` entry instead")
    ap.add_argument("--suffix", help="title suffix, e.g. Refocus gives `Kickoff/Refocus`")
    ap.add_argument(
        "--field", action="append", default=[], metavar="NAME=VALUE",
        help="one field, in order (the shell expands backticks and $ inside double quotes; "
        "prefer stdin for prose)",
    )
    ap.add_argument("--repo-root", type=Path, default=REPO_ROOT, help=argparse.SUPPRESS)  # tests
    args = ap.parse_args(argv)
    if args.query == bool(args.kind):
        ap.error("give a session kind, or --query, not both and not neither")
    fields: list[tuple[str, str]] = []
    for raw in args.field:
        name, sep, value = raw.partition("=")
        if not sep or not name.strip():
            ap.error(f"--field needs NAME=VALUE, got {raw!r}")
        fields.append((name.strip(), value))
    stream = stdin if stdin is not None else sys.stdin
    if not fields and not stream.isatty():
        try:
            fields = parse_fields(stream.read())
        except ValueError as err:
            ap.error(str(err))
    if not fields:
        ap.error("no fields: pipe `Name: value` lines on stdin or pass --field")

    if args.query:
        path, n = append_query(fields, repo_root=args.repo_root)
        anchor = f"Query {n}"
    else:
        path, n = append_session(
            args.kind, fields, repo_root=args.repo_root, title_suffix=args.suffix
        )
        anchor = f"Session {n}"
    print(f"{path.relative_to(args.repo_root)}#{anchor}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
