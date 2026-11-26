"""Session logs have one writer: path, day header, numbering and entry shape."""

import io
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest

from scripts.session_log import (
    append_query,
    append_session,
    format_fields,
    log_path,
    main,
    next_query_number,
    next_session_number,
    parse_fields,
)

ROOT = Path(__file__).resolve().parent.parent
NOW = datetime(2026, 11, 26, 8, 5)


def test_a_new_day_gets_its_header_and_month_folder(tmp_path):
    path, n = append_session("Change", [("Files", "a, b"), ("Why", "because")], NOW, tmp_path)
    assert n == 1
    assert path == tmp_path / "logs" / "11" / "2026-11-26.md"
    assert path.read_text() == (
        "# 2026-11-26\n\n## Session 1 — Change (08:05)\n- **Files:** a, b\n- **Why:** because\n"
    )


def test_numbering_counts_every_session_kind_and_entries_are_blank_line_separated(tmp_path):
    append_session("Kickoff", {"Focus": "x"}, NOW, tmp_path)
    append_session("Study", {"Cards reviewed": "3"}, NOW, tmp_path, title_suffix=None)
    _, n = append_session("Kickoff", {"Focus": "y"}, NOW, tmp_path, title_suffix="Refocus")
    text = log_path(tmp_path, NOW).read_text()
    assert n == 3
    assert "\n\n## Session 2 — Study (08:05)\n" in text
    assert "\n\n## Session 3 — Kickoff/Refocus (08:05)\n- **Focus:** y\n" in text
    assert next_session_number(text) == 4


def test_queries_have_their_own_sequence(tmp_path):
    append_session("Study", {"Cards reviewed": "3"}, NOW, tmp_path)
    _, q1 = append_query({"Question": "why?"}, NOW, tmp_path)
    _, s2 = append_session("Change", {"Files": "f"}, NOW, tmp_path)
    _, q2 = append_query({"Question": "how?"}, NOW, tmp_path)
    assert (q1, s2, q2) == (1, 2, 2)
    text = log_path(tmp_path, NOW).read_text()
    assert "\n\n## Query 1 (08:05)\n- **Question:** why?\n" in text
    assert next_query_number(text) == 3


def test_month_boundary_uses_the_date_not_the_previous_file(tmp_path):
    append_session("Change", {"Files": "f"}, datetime(2026, 10, 31, 23, 50), tmp_path)
    path, n = append_session("Change", {"Files": "f"}, datetime(2026, 11, 1, 0, 5), tmp_path)
    assert n == 1
    assert path == tmp_path / "logs" / "11" / "2026-11-01.md"
    assert (tmp_path / "logs" / "10" / "2026-10-31.md").exists()


def test_a_multiline_value_continues_on_indented_lines():
    out = format_fields([("Cards created (2)", "first\n- a\n\n- b"), ("Wiki", "none")])
    assert out == "- **Cards created (2):** first\n  - a\n\n  - b\n- **Wiki:** none\n"


def test_existing_content_is_never_touched(tmp_path):
    path = log_path(tmp_path, NOW)
    path.parent.mkdir(parents=True)
    old = "# 2026-11-26\n\n## Session 4 — Study (07:00)\n**Plain:** old style, no trailing newline"
    path.write_text(old)
    _, n = append_session("Change", {"Files": "f"}, NOW, tmp_path)
    assert n == 5
    text = path.read_text()
    assert text.startswith(old + "\n\n## Session 5")
    assert text.count("\n\n\n") == 0


def test_a_file_already_ending_in_a_blank_line_gets_no_extra_one(tmp_path):
    path = log_path(tmp_path, NOW)
    path.parent.mkdir(parents=True)
    path.write_text("# 2026-11-26\n\n")
    append_session("Change", {"Files": "f"}, NOW, tmp_path)
    assert path.read_text() == "# 2026-11-26\n\n## Session 1 — Change (08:05)\n- **Files:** f\n"


def run_cli(tmp_path, *args, stdin=None, shell=None):
    cmd = [sys.executable, str(ROOT / "scripts" / "log-append"), "--repo-root", str(tmp_path), *args]
    if shell is not None:
        return subprocess.run(shell, shell=True, executable="/bin/bash", capture_output=True,
                              text=True, cwd=ROOT, env=_env(tmp_path))
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT,
                          input=stdin if stdin is not None else "")


def _env(tmp_path):
    import os
    return {**os.environ, "LOGROOT": str(tmp_path), "SCRIPT": str(ROOT / "scripts" / "log-append")}


def only_log(tmp_path):
    return next((tmp_path / "logs").rglob("*.md")).read_text()


# ---- stdin form ----------------------------------------------------------------
def test_parse_fields_continuations_blank_lines_and_colons():
    text = "Files: a, b\n\nChange: first\n  - nested\n    - deeper\n\n  tail\nWhy: a: b\n"
    assert parse_fields(text) == [
        ("Files", "a, b"),
        ("Change", "first\n- nested\n  - deeper\ntail"),
        ("Why", "a: b"),
    ]


def test_parse_fields_rejects_a_stray_line():
    with pytest.raises(ValueError):
        parse_fields("no colon here\n")
    with pytest.raises(ValueError):
        parse_fields("  indented first\n")


def test_a_real_shell_heredoc_round_trips_verbatim(tmp_path):
    # Backticks, $HOME, double quotes and a second line survive because the heredoc is quoted.
    out = run_cli(tmp_path, shell=(
        "\"$SCRIPT\" --repo-root \"$LOGROOT\" Change <<'EOF'\n"
        "Files: `date +%Y`, $HOME, \"q\"\n"
        "Change: line one with $(whoami)\n"
        "  line two \"quoted\" `tick`\n"
        "EOF"
    ))
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip().endswith("#Session 1")
    assert (
        "- **Files:** `date +%Y`, $HOME, \"q\"\n"
        "- **Change:** line one with $(whoami)\n"
        "  line two \"quoted\" `tick`\n"
    ) in only_log(tmp_path)


def test_cli_appends_from_stdin_and_field_still_works(tmp_path):
    out = run_cli(tmp_path, "Kickoff", "--suffix", "Refocus", stdin="Focus: x\nNotes: a\n  b\n")
    assert out.returncode == 0, out.stderr
    assert "## Session 1 — Kickoff/Refocus" in only_log(tmp_path)
    out = run_cli(tmp_path, "Change", "--field", "Files=a, b", "--field", "Why=line1\nline2")
    assert out.stdout.strip().endswith("#Session 2")
    assert "- **Files:** a, b\n- **Why:** line1\n  line2\n" in only_log(tmp_path)
    q = run_cli(tmp_path, "--query", stdin="Question: q\n")
    assert q.stdout.strip().endswith("#Query 1")


def test_cli_rejects_bad_input(tmp_path):
    assert run_cli(tmp_path, stdin="A: b\n").returncode == 2  # no kind, no --query
    assert run_cli(tmp_path, "Change", "--field", "no-equals").returncode == 2
    assert run_cli(tmp_path, "Change", stdin="not a field line\n").returncode == 2
    assert run_cli(tmp_path, "Change", stdin="").returncode == 2
    assert not (tmp_path / "logs").exists()


# ---- main() in process -----------------------------------------------------------
class _Tty(io.StringIO):
    def isatty(self):
        return True


def test_main_in_process_reads_stdin_and_prints_the_anchor(tmp_path, capsys):
    rc = main(["Study", "--repo-root", str(tmp_path)], stdin=io.StringIO("Cards reviewed: 3\n"))
    assert rc == 0
    assert capsys.readouterr().out.strip().endswith("#Session 1")
    assert "- **Cards reviewed:** 3\n" in only_log(tmp_path)


def test_main_in_process_exits_2_without_fields_on_a_terminal(tmp_path):
    with pytest.raises(SystemExit) as e:
        main(["Study", "--repo-root", str(tmp_path)], stdin=_Tty())
    assert e.value.code == 2


# ---- concurrency -----------------------------------------------------------------
def test_parallel_writers_get_unique_numbers_and_one_header(tmp_path):
    procs = [
        subprocess.Popen(
            [sys.executable, str(ROOT / "scripts" / "log-append"), "--repo-root", str(tmp_path),
             "Change"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, cwd=ROOT,
        )
        for _ in range(12)
    ]
    # Each blocks on stdin once started, so releasing them together makes the race real.
    time.sleep(1)
    for i, p in enumerate(procs):
        p.stdin.write(f"Files: f{i}\n")
        p.stdin.close()
    outs = [p.stdout.read() for p in procs]
    for p in procs:
        p.wait()
    assert all(p.returncode == 0 for p in procs)
    text = only_log(tmp_path)
    assert text.count("\n# ") + text.startswith("# ") == 1
    nums = sorted(int(o.strip().rsplit(" ", 1)[1]) for o in outs)
    assert nums == list(range(1, 13))
    assert next_session_number(text) == 13
