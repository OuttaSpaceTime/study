"""The benchmark's scoring and its labels. The judge itself runs in scripts/card-quality-eval: it costs real calls."""

import importlib.machinery
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
loader = importlib.machinery.SourceFileLoader("card_quality_eval", str(ROOT / "scripts" / "card-quality-eval"))
spec = importlib.util.spec_from_loader("card_quality_eval", loader)
evaluation = importlib.util.module_from_spec(spec)
loader.exec_module(evaluation)


def test_every_case_is_labelled_and_split():
    cases = json.loads(evaluation.CASES.read_text())
    assert len({c["key"] for c in cases}) == len(cases)
    assert {c["label"] for c in cases} == {"atomic", "extra", "other", "clean"}
    for label in ("atomic", "extra", "clean"):
        splits = {c["split"] for c in cases if c["label"] == label}
        assert splits == {"dev", "test"}, f"{label} needs a held-out half"


def test_missing_a_flawed_card_fails():
    scores = evaluation.score([("atomic", ["not_atomic"])] * 17 + [("atomic", [])] * 3)
    assert evaluation.failures(scores) == ["atomic: caught 17/20"]


def test_refusing_a_sound_card_fails_whatever_the_flaw():
    for flaw in ("extra_info", "too_vague"):
        bad = evaluation.failures(evaluation.score([("clean", [flaw])] * 3 + [("clean", [])] * 17))
        assert bad == ["clean: 3/20 sound cards refused"]


def test_catching_a_flawed_card_for_the_wrong_flaw_is_no_catch():
    assert evaluation.failures(evaluation.score([("atomic", ["too_vague"])] * 20)) == ["atomic: caught 0/20"]


def test_a_steady_judge_passes():
    assert evaluation.failures(evaluation.score([("atomic", ["not_atomic"]), ("extra", ["extra_info"]), ("clean", [])])) == []
