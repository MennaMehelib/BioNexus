"""Rule registry: loads rules_register.json and controls rule enablement."""

from __future__ import annotations

import json
from enum import Enum
from importlib import resources


class RuleStatus(str, Enum):
    ACCEPT_M1 = "ACCEPT_M1"
    ACCEPT_GATED = "ACCEPT_GATED"
    CONDITIONAL = "CONDITIONAL"
    REJECTED = "REJECTED"
    DEFERRED = "DEFERRED"


class RuleDisabled(Exception):
    """Raised when a rule that is not enabled is required."""


_OPT_IN = {RuleStatus.ACCEPT_GATED, RuleStatus.CONDITIONAL}
_NEVER = {RuleStatus.REJECTED, RuleStatus.DEFERRED}


class RuleRegistry:
    def __init__(self, enabled_for_test=None):
        text = (
            resources.files("bionexus")
            .joinpath("rules_register.json")
            .read_text(encoding="utf-8")
        )
        self._rules = {
            r["id"]: {"status": RuleStatus(r["status"]), "version": r["version"]}
            for r in json.loads(text)
        }
        self._enabled_for_test = frozenset(enabled_for_test or ())
        for rid in self._enabled_for_test:
            st = self.status(rid)  # KeyError for unknown ids
            if st in _NEVER:
                raise ValueError(f"{rid} has status {st.value} and can never be enabled")

    def status(self, rule_id: str) -> RuleStatus:
        return self._rules[rule_id]["status"]

    def version(self, rule_id: str) -> str:
        return self._rules[rule_id]["version"]

    def is_enabled(self, rule_id: str) -> bool:
        st = self.status(rule_id)
        if st is RuleStatus.ACCEPT_M1:
            return True
        if st in _OPT_IN:
            return rule_id in self._enabled_for_test
        return False

    def require_enabled(self, rule_id: str) -> None:
        if not self.is_enabled(rule_id):
            raise RuleDisabled(f"rule {rule_id} is not enabled")
