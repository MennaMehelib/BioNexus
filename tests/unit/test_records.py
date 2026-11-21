import json

import pytest

from bionexus.records import (
    AssessmentRecord,
    Outcome,
    RuleGap,
    State,
    combine_outcomes,
    rule_gap_record,
)


def rec(outcome, check_id="c1", rule_id="G-01", scope="study1"):
    return AssessmentRecord(
        check_id=check_id,
        rule_id=rule_id,
        rule_version="0.1",
        scope=scope,
        outcome=outcome,
        evidence={"k": "v"},
        confidence=None,
        limitations=("l1",),
        decision_basis="test",
    )


def test_outcome_members_exact():
    assert {o.name: o.value for o in Outcome} == {
        "PASS": "pass",
        "RESOLVED": "resolved",
        "NOTE": "note",
        "LIMITATION": "limitation",
        "NEED_FACT": "need_fact",
        "NEED_DECISION": "need_decision",
        "NOT_ASSESSABLE": "not_assessable",
        "BLOCKED": "blocked",
    }


def test_state_members_exact():
    assert {s.value for s in State} == {
        "compatible",
        "compatible_with_warnings",
        "requires_manual_review",
        "incompatible",
    }
    assert len(State) == 4


def test_combine_empty():
    assert combine_outcomes([]) is State.COMPATIBLE


def test_combine_neutral_only():
    records = [rec(Outcome.PASS), rec(Outcome.RESOLVED), rec(Outcome.NOTE)]
    assert combine_outcomes(records) is State.COMPATIBLE


def test_combine_blocked():
    assert combine_outcomes([rec(Outcome.PASS), rec(Outcome.BLOCKED)]) is State.INCOMPATIBLE


@pytest.mark.parametrize(
    "o", [Outcome.NEED_FACT, Outcome.NEED_DECISION, Outcome.NOT_ASSESSABLE]
)
def test_combine_manual_review(o):
    assert combine_outcomes([rec(Outcome.NOTE), rec(o)]) is State.REQUIRES_MANUAL_REVIEW


def test_combine_limitation():
    assert (
        combine_outcomes([rec(Outcome.PASS), rec(Outcome.LIMITATION)])
        is State.COMPATIBLE_WITH_WARNINGS
    )


def test_blocked_beats_need_fact():
    assert (
        combine_outcomes([rec(Outcome.NEED_FACT), rec(Outcome.BLOCKED)])
        is State.INCOMPATIBLE
    )


def test_need_fact_beats_limitation():
    assert (
        combine_outcomes([rec(Outcome.LIMITATION), rec(Outcome.NEED_FACT)])
        is State.REQUIRES_MANUAL_REVIEW
    )


def test_empty_check_id():
    with pytest.raises(ValueError):
        rec(Outcome.PASS, check_id="")


def test_empty_rule_id():
    with pytest.raises(ValueError):
        rec(Outcome.PASS, rule_id="")


def test_empty_scope():
    with pytest.raises(ValueError):
        rec(Outcome.PASS, scope="")


def test_wrong_outcome_type():
    with pytest.raises(ValueError):
        rec("pass")


def test_to_dict_json_serializable():
    d = rec(Outcome.LIMITATION).to_dict()
    s = json.dumps(d)
    assert json.loads(s)["outcome"] == "limitation"
    assert d["limitations"] == ["l1"] or d["limitations"] == ("l1",)


def test_rule_gap_record():
    gap = RuleGap(scope="pair1", description="undefined case", missing="a rule")
    r = rule_gap_record(gap)
    assert r.outcome is Outcome.NOT_ASSESSABLE
    assert r.rule_id == "J-05"
    assert r.scope == "pair1"
    assert r.decision_basis == "rule gap: BioNexus cannot assess this case yet"
    assert r.evidence["missing"] == "a rule"
    json.dumps(r.to_dict())
