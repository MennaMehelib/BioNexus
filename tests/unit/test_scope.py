"""Tests for T1.6 scope_gate (G-01 scope gate).

Covers all 14 test groups from the revised T1.6 contract.
"""

import copy
import inspect
import json

import pytest

from bionexus.records import AssessmentRecord, Outcome, State, combine_outcomes
from bionexus.scope import scope_gate


def _by_check(records, check_id):
    return [r for r in records if r.check_id == check_id]


def _outcomes(records):
    return [r.outcome for r in records]


def _base_declared():
    return {"organism": "human", "technology": "RNA-seq", "level": "gene"}


# ---------------------------------------------------------------- Group 1
def test_human_rna_seq_gene_all_pass():
    declared = _base_declared()
    before = copy.deepcopy(declared)
    records = scope_gate(declared)
    assert declared == before  # not mutated
    assert len(records) == 3
    assert all(r.outcome == Outcome.PASS for r in records)
    assert combine_outcomes(records) == State.COMPATIBLE
    for r in records:
        assert r.rule_id == "G-01"
        assert r.rule_version == "0.1"
        assert r.confidence is None
        assert r.limitations == ()
        assert r.scope == "matrix"


# ---------------------------------------------------------------- Group 2
@pytest.mark.parametrize(
    "value,field",
    [
        (" HUMAN ", "organism"),
        ("Homo sapiens", "organism"),
        ("homo_sapiens", "organism"),
        ("RNA_seq", "technology"),
        ("RNAseq", "technology"),
        ("Gene Level", "level"),
    ],
)
def test_normalized_values_pass(value, field):
    declared = _base_declared()
    declared[field] = value
    records = scope_gate(declared)
    field_record = _by_check(records, f"G-01.{field}")[0]
    assert field_record.outcome == Outcome.PASS


# ---------------------------------------------------------------- Group 3
def test_microarray_blocked():
    declared = _base_declared()
    declared["technology"] = "microarray"
    records = scope_gate(declared)
    tech = _by_check(records, "G-01.technology")[0]
    assert tech.outcome == Outcome.BLOCKED
    assert "out of V1 scope" in tech.decision_basis
    assert combine_outcomes(records) == State.INCOMPATIBLE


# ---------------------------------------------------------------- Group 4
@pytest.mark.parametrize(
    "value,field",
    [
        ("mouse", "organism"),
        ("Mus musculus", "organism"),
        ("transcript", "level"),
    ],
)
def test_known_out_of_scope_blocked(value, field):
    declared = _base_declared()
    declared[field] = value
    records = scope_gate(declared)
    field_record = _by_check(records, f"G-01.{field}")[0]
    assert field_record.outcome == Outcome.BLOCKED


# ---------------------------------------------------------------- Group 5
@pytest.mark.parametrize(
    "value,field",
    [
        (None, "organism"),
        ("", "organism"),
        ("   ", "organism"),
        (None, "technology"),
        ("", "technology"),
        ("   ", "technology"),
        (None, "level"),
        ("", "level"),
        ("   ", "level"),
    ],
)
def test_missing_value_need_fact(value, field):
    declared = _base_declared()
    declared[field] = value
    records = scope_gate(declared)
    field_records = _by_check(records, f"G-01.{field}")
    assert len(field_records) == 1
    assert field_records[0].outcome == Outcome.NEED_FACT
    assert field in field_records[0].decision_basis
    assert "missing" in field_records[0].decision_basis.lower()


def test_absent_key_need_fact():
    declared = {"organism": "human", "technology": "RNA-seq"}  # level absent
    records = scope_gate(declared)
    field_records = _by_check(records, "G-01.level")
    assert len(field_records) == 1
    assert field_records[0].outcome == Outcome.NEED_FACT


# ---------------------------------------------------------------- Group 6
@pytest.mark.parametrize(
    "value,field",
    [
        ("martian", "organism"),
        ("proteomics", "technology"),
        ("exon", "level"),
        (5, "organism"),
    ],
)
def test_unrecognized_value_need_fact(value, field):
    declared = _base_declared()
    declared[field] = value
    records = scope_gate(declared)
    field_record = _by_check(records, f"G-01.{field}")[0]
    assert field_record.outcome == Outcome.NEED_FACT
    accepted = {
        "organism": ["human", "homo-sapiens"],
        "technology": ["rna-seq", "rnaseq"],
        "level": ["gene", "gene-level"],
    }[field]
    for acc in accepted:
        assert acc in field_record.decision_basis


# ---------------------------------------------------------------- Group 7
def test_mouse_microarray_gene_two_blocked_one_pass():
    declared = {"organism": "mouse", "technology": "microarray", "level": "gene"}
    records = scope_gate(declared)
    blocked = [r for r in records if r.outcome == Outcome.BLOCKED]
    passed = [r for r in records if r.outcome == Outcome.PASS]
    assert len(blocked) == 2
    assert len(passed) == 1
    assert len(records) == 3  # all three fields checked


# ---------------------------------------------------------------- Group 8
@pytest.mark.parametrize("id_type", ["probe", "reporter"])
def test_id_type_probe_reporter_consistency_need_fact(id_type):
    declared = _base_declared()
    declared["id_type"] = id_type
    records = scope_gate(declared)
    consistency = _by_check(records, "G-01.consistency")
    assert len(consistency) == 1
    assert consistency[0].outcome == Outcome.NEED_FACT
    assert "confirm the technology and the identifier type" in consistency[0].decision_basis


# ---------------------------------------------------------------- Group 9
@pytest.mark.parametrize("id_type", ["ensembl_gene", "entrez-gene", "symbol"])
def test_id_type_recognized_consistency_pass(id_type):
    declared = _base_declared()
    declared["id_type"] = id_type
    records = scope_gate(declared)
    consistency = _by_check(records, "G-01.consistency")
    assert len(consistency) == 1
    assert consistency[0].outcome == Outcome.PASS


# ---------------------------------------------------------------- Group 10
@pytest.mark.parametrize("id_type", [None, "unknown"])
def test_id_type_missing_or_unknown_no_record(id_type):
    declared = _base_declared()
    if id_type is None:
        declared["id_type"] = None
    else:
        declared["id_type"] = id_type
    records = scope_gate(declared)
    assert not _by_check(records, "G-01.id_type")
    assert not _by_check(records, "G-01.consistency")


def test_id_type_absent_no_record():
    declared = _base_declared()
    records = scope_gate(declared)
    assert not _by_check(records, "G-01.id_type")
    assert not _by_check(records, "G-01.consistency")


# ---------------------------------------------------------------- Group 11
def test_id_type_ensg_unrecognized_need_fact():
    declared = {"id_type": "ENSG"}
    records = scope_gate(declared)
    id_type_records = _by_check(records, "G-01.id_type")
    assert len(id_type_records) == 1
    assert id_type_records[0].outcome == Outcome.NEED_FACT
    accepted = ["ensembl-gene", "entrez-gene", "symbol", "probe", "reporter", "unknown"]
    for acc in accepted:
        assert acc in id_type_records[0].decision_basis


# ---------------------------------------------------------------- Group 12
def test_microarray_with_probe_no_consistency():
    declared = _base_declared()
    declared["technology"] = "microarray"
    declared["id_type"] = "probe"
    records = scope_gate(declared)
    tech = _by_check(records, "G-01.technology")[0]
    assert tech.outcome == Outcome.BLOCKED
    assert not _by_check(records, "G-01.consistency")


# ---------------------------------------------------------------- Group 13
def test_declared_not_mutated_scope_and_json_serializable():
    declared = {"organism": "human", "technology": "RNA-seq", "level": "gene", "extra": "ignored"}
    before = copy.deepcopy(declared)
    records = scope_gate(declared, scope="studyA")
    assert declared == before
    for r in records:
        assert r.scope == "studyA"
        json.dumps(r.to_dict())  # must not raise


# ---------------------------------------------------------------- Group 14
def test_scope_py_no_accessions_regex():
    import bionexus.scope as scope_module

    source = inspect.getsource(scope_module)
    assert "GSE" not in source
    assert "GSM" not in source
    assert "re.compile" not in source
    assert "import re" not in source


# ------------------------------------------------ T1.6 correction tests
class _Str:
    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text


class _Bad:
    def __str__(self):
        raise RuntimeError("no str")

    __repr__ = __str__


_HOSTILE = [
    {"x"}, float("nan"), float("inf"), b"human", ["mouse"], {"a": 1},
    (1, 2), 10**30, object(), _Str("probe"), _Str("rnaseq"), _Bad(),
]


def _hostile_id(h):
    return type(h).__name__


@pytest.mark.parametrize("field", ["organism", "technology", "level", "id_type"])
@pytest.mark.parametrize("hostile", _HOSTILE, ids=_hostile_id)
def test_any_declared_value_yields_strict_json(field, hostile):
    declared = _base_declared()
    declared[field] = hostile
    records = scope_gate(declared)
    for r in records:
        json.dumps(r.to_dict(), allow_nan=False)


@pytest.mark.parametrize("hostile", [_Str("probe"), _Str("reporter")])
def test_consistency_record_strict_json_with_custom_str_id_type(hostile):
    declared = _base_declared()
    declared["id_type"] = hostile
    records = scope_gate(declared)
    # str() says "probe"/"reporter" -> consistency record exists and must serialize
    cons = _by_check(records, "G-01.consistency")
    assert len(cons) == 1
    json.dumps(cons[0].to_dict(), allow_nan=False)


def test_custom_str_technology_serializes_in_both_records():
    declared = _base_declared()
    declared["technology"] = _Str("rnaseq")
    declared["id_type"] = "probe"
    records = scope_gate(declared)
    for check in ("G-01.technology", "G-01.consistency"):
        rec = _by_check(records, check)
        assert len(rec) == 1
        json.dumps(rec[0].to_dict(), allow_nan=False)


def test_evidence_does_not_alias_caller_objects():
    caller_list = ["mouse"]
    declared = _base_declared()
    declared["organism"] = caller_list
    before = copy.deepcopy(declared)
    records = scope_gate(declared)
    snapshot = json.dumps(records[0].to_dict(), allow_nan=False)
    caller_list.append("X")
    assert json.dumps(records[0].to_dict(), allow_nan=False) == snapshot
    assert declared["organism"] == ["mouse", "X"] and before["organism"] == ["mouse"]


def test_string_value_kept_verbatim_in_evidence():
    declared = _base_declared()
    declared["organism"] = " HUMAN "
    rec = _by_check(scope_gate(declared), "G-01.organism")[0]
    assert rec.evidence["declared"] == " HUMAN "
    assert rec.evidence["declared_type"] == "str"
    assert rec.evidence["normalized"] == "human"


@pytest.mark.parametrize("missing", ["organism", "technology"])
def test_absent_key_need_fact_for_organism_and_technology(missing):
    declared = _base_declared()
    del declared[missing]
    records = scope_gate(declared)
    rec = _by_check(records, f"G-01.{missing}")
    assert len(rec) == 1 and rec[0].outcome == Outcome.NEED_FACT


def test_extra_key_produces_no_extra_record():
    declared = _base_declared()
    declared["extra"] = "ignored"
    records = scope_gate(declared)
    assert [r.check_id for r in records] == [
        "G-01.organism", "G-01.technology", "G-01.level"]


def test_exact_signature():
    sig = inspect.signature(scope_gate)
    assert list(sig.parameters) == ["declared", "scope"]
    assert sig.parameters["scope"].default == "matrix"
    assert scope_gate.__annotations__ == {
        "declared": "dict", "scope": "str", "return": "list[AssessmentRecord]"}
