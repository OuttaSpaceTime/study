"""Tests for scripts.srs_pressure — verdict, rendering, CLI, thresholds."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import srs_pressure
from scripts.srs_pressure import (
    EXIT_OK,
    EXIT_PAUSE,
    EXIT_WARN,
    PAUSE_FLASHCARDS,
    PAUSE_NEW_TODAY,
    PAUSE_WIKI,
    WARN_FLASHCARDS,
    WARN_NEW_TODAY,
    WARN_WIKI,
    DeckState,
    exit_code,
    main,
    parse_decks_output,
    render_human,
    verdict,
    wiki_due_count,
)


class TestVerdict:
    def test_all_zero_is_ok(self):
        level, reasons = verdict(0, 0, 0)
        assert level == "ok"
        assert reasons == []

    def test_below_warn_is_ok(self):
        level, reasons = verdict(WARN_FLASHCARDS - 1, WARN_WIKI - 1, WARN_NEW_TODAY - 1)
        assert level == "ok"
        assert reasons == []

    def test_flashcards_at_warn_threshold(self):
        level, reasons = verdict(WARN_FLASHCARDS, 0, 0)
        assert level == "warn"
        assert len(reasons) == 1
        assert "flashcards" in reasons[0]

    def test_flashcards_at_pause_threshold(self):
        level, reasons = verdict(PAUSE_FLASHCARDS, 0, 0)
        assert level == "pause"
        assert f">= {PAUSE_FLASHCARDS}" in reasons[0]

    def test_wiki_at_warn_threshold(self):
        level, reasons = verdict(0, WARN_WIKI, 0)
        assert level == "warn"
        assert "wiki" in reasons[0]

    def test_wiki_at_pause_threshold(self):
        level, reasons = verdict(0, PAUSE_WIKI, 0)
        assert level == "pause"

    def test_new_today_at_warn_threshold(self):
        level, reasons = verdict(0, 0, WARN_NEW_TODAY)
        assert level == "warn"
        assert "today" in reasons[0]

    def test_new_today_at_pause_threshold(self):
        level, reasons = verdict(0, 0, PAUSE_NEW_TODAY)
        assert level == "pause"

    def test_any_pause_wins_over_warn(self):
        # flashcards warn, wiki pause -> overall pause
        level, _ = verdict(WARN_FLASHCARDS, PAUSE_WIKI, 0)
        assert level == "pause"

    def test_multiple_reasons_combined(self):
        level, reasons = verdict(PAUSE_FLASHCARDS, PAUSE_WIKI, PAUSE_NEW_TODAY)
        assert level == "pause"
        assert len(reasons) == 3

    def test_warn_level_reason_has_no_threshold_marker(self):
        # Warn reasons are less alarming — no ">= N" marker.
        _, reasons = verdict(WARN_FLASHCARDS, 0, 0)
        assert ">=" not in reasons[0]

    def test_pause_level_reason_has_threshold_marker(self):
        _, reasons = verdict(PAUSE_FLASHCARDS, 0, 0)
        assert ">=" in reasons[0]


class TestExitCode:
    def test_ok(self):
        assert exit_code("ok") == EXIT_OK == 0

    def test_warn(self):
        assert exit_code("warn") == EXIT_WARN == 1

    def test_pause(self):
        assert exit_code("pause") == EXIT_PAUSE == 2


class TestRenderHuman:
    def test_ok_has_no_recommendation(self):
        out = render_human("ok", [], 3, 0, 0)
        assert "OK" in out
        assert "Recommendation" not in out
        assert "3" in out

    def test_warn_includes_reasons_and_recommendation(self):
        out = render_human("warn", ["30 flashcards due"], 30, 0, 0)
        assert "recommend pausing" in out.lower()
        assert "30 flashcards due" in out
        assert "Recommendation" in out

    def test_pause_header_is_severe(self):
        out = render_human("pause", ["60 flashcards due (>= 50)"], 60, 0, 0)
        assert "Danger" in out
        assert "60 flashcards due (>= 50)" in out

    def test_counts_rendered(self):
        out = render_human("warn", ["x"], 22, 9, 6)
        assert "22" in out
        assert "9" in out
        assert "6" in out


class TestWikiDueCount:
    def test_empty_index(self, wiki_dir: Path):
        assert wiki_due_count(wiki_dir) == 0

    def test_counts_due_entries(self, wiki_dir: Path):
        index = {
            "a": {"next_review": "2020-01-01"},  # past — due
            "b": {"next_review": "2099-01-01"},  # future — not due
            "c": {},  # no next_review — not due
        }
        (wiki_dir / ".wiki-index.json").write_text(json.dumps(index))
        assert wiki_due_count(wiki_dir) == 1


class TestMainCLI:
    def test_json_output_ok(self, capsys, wiki_dir: Path):
        rc = main(["--flashcards-due", "3", "--wiki-dir", str(wiki_dir)])
        assert rc == EXIT_OK
        out = capsys.readouterr().out
        payload = json.loads(out)
        assert payload["verdict"] == "ok"
        assert payload["flashcards_due"] == 3
        assert payload["wiki_due"] == 0
        assert payload["new_today"] == 0
        assert payload["reasons"] == []
        assert "thresholds" in payload

    def test_json_output_warn(self, capsys, wiki_dir: Path):
        rc = main(["--flashcards-due", str(WARN_FLASHCARDS), "--wiki-dir", str(wiki_dir)])
        assert rc == EXIT_WARN
        payload = json.loads(capsys.readouterr().out)
        assert payload["verdict"] == "warn"

    def test_json_output_pause(self, capsys, wiki_dir: Path):
        rc = main(["--flashcards-due", str(PAUSE_FLASHCARDS), "--wiki-dir", str(wiki_dir)])
        assert rc == EXIT_PAUSE
        payload = json.loads(capsys.readouterr().out)
        assert payload["verdict"] == "pause"

    def test_human_output(self, capsys, wiki_dir: Path):
        rc = main([
            "--flashcards-due", str(PAUSE_FLASHCARDS),
            "--wiki-dir", str(wiki_dir),
            "--human",
        ])
        assert rc == EXIT_PAUSE
        out = capsys.readouterr().out
        assert "Danger" in out
        # Not JSON
        with pytest.raises(json.JSONDecodeError):
            json.loads(out)

    def test_self_fetches_when_flashcards_due_omitted(self, monkeypatch, capsys, wiki_dir: Path):
        fake_decks = [
            DeckState(name="Software Engineering", total=439, due=221, new=153, learning=5, review=275),
        ]
        monkeypatch.setattr(srs_pressure, "fetch_srs_state", lambda: fake_decks)
        rc = main(["--wiki-dir", str(wiki_dir)])
        assert rc == EXIT_PAUSE
        payload = json.loads(capsys.readouterr().out)
        assert payload["flashcards_due"] == 221
        assert payload["total_due"] == 221
        assert payload["decks"] == [
            {
                "name": "Software Engineering",
                "total": 439,
                "due": 221,
                "new": 153,
                "learning": 5,
                "review": 275,
                "relearning": 0,
                "due_new": 0,
                "due_learning": 0,
                "due_review": 0,
                "due_relearning": 0,
            }
        ]

    def test_wiki_due_contributes_to_verdict(self, capsys, wiki_dir: Path):
        # Build an index with enough due entries to trigger a warn.
        index = {
            f"page-{i}": {"next_review": "2020-01-01"}
            for i in range(WARN_WIKI)
        }
        (wiki_dir / ".wiki-index.json").write_text(json.dumps(index))
        rc = main(["--flashcards-due", "0", "--wiki-dir", str(wiki_dir)])
        assert rc == EXIT_WARN
        payload = json.loads(capsys.readouterr().out)
        assert payload["wiki_due"] == WARN_WIKI
        assert payload["verdict"] == "warn"


class TestParseDecksOutput:
    SAMPLE = """Decks:

  Software Engineering (274 cards)
    Due: 36 | New: 17 | Learning: 0 | Review: 251 | Relearning: 6
    Due breakdown: 17 new | 0 learning | 14 review | 5 relearning
  Personal (10 cards)
    Due: 2 | New: 1 | Learning: 0 | Review: 9 | Relearning: 0
    Due breakdown: 1 new | 0 learning | 1 review | 0 relearning
"""

    def test_parses_multiple_decks(self):
        decks = parse_decks_output(self.SAMPLE)
        assert len(decks) == 2
        assert decks[0] == DeckState(
            "Software Engineering", 274, 36, 17, 0, 251,
            relearning=6, due_new=17, due_learning=0, due_review=14, due_relearning=5,
        )
        assert decks[1] == DeckState(
            "Personal", 10, 2, 1, 0, 9,
            relearning=0, due_new=1, due_learning=0, due_review=1, due_relearning=0,
        )

    def test_empty_output(self):
        assert parse_decks_output("") == []

    def test_parses_legacy_output_without_relearning_or_breakdown(self):
        # Older flashcard-mcp output (pre-2026-05-04) — no Relearning, no Due breakdown line.
        text = (
            "  My Deck Name (7 cards)\n"
            "    Due: 0 | New: 0 | Learning: 0 | Review: 7\n"
        )
        decks = parse_decks_output(text)
        assert decks == [DeckState("My Deck Name", 7, 0, 0, 0, 7)]


class TestHumanOutputDeckBreakdown:
    def test_includes_state_and_due_breakdown_lines(self):
        decks = [
            DeckState(
                "Software Engineering", 274, 36, 17, 0, 251,
                relearning=6, due_new=17, due_learning=0, due_review=14, due_relearning=5,
            )
        ]
        out = render_human("warn", ["36 flashcards due"], 36, 0, 0, decks)
        assert "Decks:" in out
        assert "Software Engineering — 274 cards" in out
        assert "State:   17 new · 0 learning · 251 review · 6 relearning" in out
        assert "Due now: 36 = 17 new + 0 learning + 14 review + 5 relearning" in out

    def test_appends_suspended_when_state_sum_below_total(self):
        decks = [
            DeckState(
                "D", 10, 0, 1, 0, 7,
                relearning=0, due_new=0, due_learning=0, due_review=0, due_relearning=0,
            )
        ]
        out = render_human("warn", ["x"], 0, 0, 0, decks)
        assert "1 new · 0 learning · 7 review · 0 relearning · 2 suspended" in out

    def test_omits_suspended_when_state_sum_equals_total(self):
        decks = [
            DeckState(
                "Personal", 10, 2, 1, 0, 9,
                relearning=0, due_new=1, due_learning=0, due_review=1, due_relearning=0,
            )
        ]
        out = render_human("warn", ["x"], 2, 0, 0, decks)
        assert "Personal — 10 cards" in out
        assert "1 new · 0 learning · 9 review · 0 relearning" in out
        assert "suspended" not in out

    def test_omits_deck_breakdown_when_no_decks(self):
        out = render_human("ok", [], 0, 0, 0, [])
        assert "Decks:" not in out


class TestThresholdInvariants:
    def test_warn_lower_than_pause(self):
        assert WARN_FLASHCARDS < PAUSE_FLASHCARDS
        assert WARN_WIKI < PAUSE_WIKI
        assert WARN_NEW_TODAY < PAUSE_NEW_TODAY
