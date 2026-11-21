import json
from collections import Counter
from importlib import resources

import pytest

from bionexus.rules import RuleDisabled, RuleRegistry, RuleStatus


def test_status_members():
    assert {s.name for s in RuleStatus} == {
        "ACCEPT_M1",
        "ACCEPT_GATED",
        "CONDITIONAL",
        "REJECTED",
        "DEFERRED",
    }


def test_register_counts_and_uniqueness():
    path = resources.files("bionexus").joinpath("rules_register.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    ids = [r["id"] for r in data]
    assert len(ids) == 45 == len(set(ids))
    assert all(r["version"] == "0.1" for r in data)
    assert Counter(r["status"] for r in data) == Counter(
        {
            "ACCEPT_M1": 25,
            "ACCEPT_GATED": 12,
            "CONDITIONAL": 2,
            "REJECTED": 3,
            "DEFERRED": 3,
        }
    )


def test_registry_exact_membership():
    reg = RuleRegistry()
    expected = {
        "ACCEPT_M1": "G-01 G-02 G-03 G-04 M-01 M-02 M-03 M-04 M-05 M-06 M-07 R-01 R-02 R-05 R-06 N-05 T-07 B-05 J-01 J-02 J-03 J-04 J-05 V-01 V-02",
        "ACCEPT_GATED": "R-04 N-01 N-02 N-03 T-01 T-02 T-03 T-04 B-01 B-02 B-03 B-04",
        "CONDITIONAL": "R-03 T-05",
        "REJECTED": "T-06 B-06 X-02",
        "DEFERRED": "N-04 X-01 X-03",
    }
    for status, ids in expected.items():
        for rid in ids.split():
            assert reg.status(rid) is RuleStatus[status], rid
    assert sum(len(v.split()) for v in expected.values()) == 45


def test_m1_enabled():
    assert RuleRegistry().is_enabled("G-01") is True


def test_gated_disabled_by_default_and_enabled_for_test():
    assert RuleRegistry().is_enabled("T-01") is False
    assert RuleRegistry(enabled_for_test={"T-01"}).is_enabled("T-01") is True


def test_conditional_disabled_by_default_and_enabled_for_test():
    assert RuleRegistry().is_enabled("R-03") is False
    assert RuleRegistry(enabled_for_test={"R-03"}).is_enabled("R-03") is True


def test_require_enabled_raises():
    with pytest.raises(RuleDisabled):
        RuleRegistry().require_enabled("T-01")
    RuleRegistry().require_enabled("G-01")


@pytest.mark.parametrize("rid", ["T-06", "N-04"])
def test_rejected_or_deferred_in_enabled_for_test(rid):
    with pytest.raises(ValueError):
        RuleRegistry(enabled_for_test={rid})


def test_rejected_never_enabled():
    reg = RuleRegistry()
    assert not reg.is_enabled("T-06")
    with pytest.raises(RuleDisabled):
        reg.require_enabled("X-01")


def test_unknown_rule_id():
    with pytest.raises(KeyError):
        RuleRegistry().status("ZZ-99")
    with pytest.raises(KeyError):
        RuleRegistry().is_enabled("ZZ-99")
    with pytest.raises(KeyError):
        RuleRegistry(enabled_for_test={"ZZ-99"})
