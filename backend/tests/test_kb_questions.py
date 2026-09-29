"""The 30-question knowledge-base test (run after every data change)."""
import json
from pathlib import Path

import pytest

from app.services import catalogue

QUESTIONS = json.loads((Path(__file__).resolve().parents[1] / "data" / "kb_questions.json").read_text())["questions"]


def test_there_are_thirty_questions():
    assert len(QUESTIONS) == 30


@pytest.mark.parametrize("q", QUESTIONS, ids=[q["q"] for q in QUESTIONS])
def test_kb_question(db, q):
    ai = catalogue.find_ai(db, q["ai"])
    assert ai is not None, f"ingredient {q['ai']} missing"
    f = catalogue.find_formulation(db, ai, q["pct"], q["type"])
    assert f is not None, f"formulation {q['ai']} {q['pct']} {q['type']} missing"
    claim = catalogue.find_claim(db, f, q["crop"], q["pest"])
    assert (claim is not None) == q["approved"]
    if q["approved"]:
        assert claim["dose_form_ha"] == q["form_ha"]
        assert claim["phi_days"] == q["phi"]
