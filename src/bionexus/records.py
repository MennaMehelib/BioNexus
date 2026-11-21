"""Assessment records, outcomes, states and the fixed outcome-combination order (J-04)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    PASS = "pass"
    RESOLVED = "resolved"
    NOTE = "note"
    LIMITATION = "limitation"
    NEED_FACT = "need_fact"
    NEED_DECISION = "need_decision"
    NOT_ASSESSABLE = "not_assessable"
    BLOCKED = "blocked"


class State(str, Enum):
    COMPATIBLE = "compatible"
    COMPATIBLE_WITH_WARNINGS = "compatible_with_warnings"
    REQUIRES_MANUAL_REVIEW = "requires_manual_review"
    INCOMPATIBLE = "incompatible"


@dataclass(frozen=True)
class AssessmentRecord:
    check_id: str
    rule_id: str
    rule_version: str
    scope: str
    outcome: Outcome
    evidence: dict
    confidence: str | None
    limitations: tuple[str, ...]
    decision_basis: str

    def __post_init__(self):
        for name in ("check_id", "rule_id", "scope"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} must be a non-empty string")
        if not isinstance(self.outcome, Outcome):
            raise ValueError("outcome must be an Outcome member")

    def to_dict(self) -> dict:
        return {
            "check_id": self.check_id,
            "rule_id": self.rule_id,
            "rule_version": self.rule_version,
            "scope": self.scope,
            "outcome": self.outcome.value,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "limitations": list(self.limitations),
            "decision_basis": self.decision_basis,
        }


_MANUAL_REVIEW = {Outcome.NEED_FACT, Outcome.NEED_DECISION, Outcome.NOT_ASSESSABLE}


def combine_outcomes(records) -> State:
    """Fixed precedence: blocked > need_fact/need_decision/not_assessable > limitation > compatible."""
    outcomes = {r.outcome for r in records}
    if Outcome.BLOCKED in outcomes:
        return State.INCOMPATIBLE
    if outcomes & _MANUAL_REVIEW:
        return State.REQUIRES_MANUAL_REVIEW
    if Outcome.LIMITATION in outcomes:
        return State.COMPATIBLE_WITH_WARNINGS
    return State.COMPATIBLE


@dataclass(frozen=True)
class RuleGap:
    scope: str
    description: str
    missing: str


def rule_gap_record(gap: RuleGap) -> AssessmentRecord:
    return AssessmentRecord(
        check_id="rule_gap",
        rule_id="J-05",
        rule_version="0.1",
        scope=gap.scope,
        outcome=Outcome.NOT_ASSESSABLE,
        evidence={"description": gap.description, "missing": gap.missing},
        confidence=None,
        limitations=(),
        decision_basis="rule gap: BioNexus cannot assess this case yet",
    )
