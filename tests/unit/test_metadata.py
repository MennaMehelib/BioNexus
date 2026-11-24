"""Tests for T1.7 sample matching (M-01, M-02) and Tier A completeness (M-03).

Test names follow test_<RULE>_<P|N|E>_..., with the rule ID written without its
hyphen (M-01 -> M01) because a Python identifier cannot contain "-"."""

import copy
import json

import numpy as np
import pandas as pd
import pytest

from bionexus.metadata import (
    find_metadata_duplicates,
    match_samples,
    normalize_id,
    tier_a_check,
)
from bionexus.records import Outcome, State, combine_outcomes


def by(records, check_id):
    return [r for r in records if r.check_id == check_id]


def strict(records):
    for r in records:
        json.dumps(r.to_dict(), allow_nan=False)


def triples(res):
    return [(m["matrix_id"], m["sample_id"], m["tier"]) for m in res.matches]


# ------------------------------------------------------------ normalization
@pytest.mark.parametrize("raw,expected", [
    ("Sample_1", "sample-1"),
    ("  SAMPLE.2 ", "sample-2"),
    ("s 3", "s-3"),
    ("S__1", "s-1"),
    ("S - 1", "s-1"),
    ("S1", "s1"),
    ("a.b_c d", "a-b-c-d"),
])
def test_M01_P_normalize_id(raw, expected):
    assert normalize_id(raw) == expected


def test_M01_P_exact_match_tier1():
    res = match_samples(["S1", "S2"], ["S2", "S1"], "A")
    assert triples(res) == [("S1", "S1", "exact"), ("S2", "S2", "exact")]
    assert all(m["study"] == "A" for m in res.matches)
    assert res.unmatched_matrix == [] and res.unmatched_metadata == []
    rec = by(res.records, "M-01.match")
    assert len(rec) == 1 and rec[0].outcome == Outcome.PASS
    assert rec[0].evidence["by_tier"] == {"exact": 2}
    assert combine_outcomes(res.records) == State.COMPATIBLE
    strict(res.records)


def test_M01_P_normalized_match_tier2():
    res = match_samples(["Sample_1", "  SAMPLE.2", "s 3"],
                        ["sample-1", "sample-2", "S-3"], "A")
    assert triples(res) == [("Sample_1", "sample-1", "normalized"),
                            ("  SAMPLE.2", "sample-2", "normalized"),
                            ("s 3", "S-3", "normalized")]
    assert combine_outcomes(res.records) == State.COMPATIBLE


def test_M01_P_exact_has_priority_over_normalized():
    res = match_samples(["S-1", "s_1"], ["S-1", "x"], "A")
    assert ("S-1", "S-1", "exact") in triples(res)
    assert res.unmatched_matrix == ["s_1"]


def test_M01_P_documented_mapping_tier2():
    res = match_samples(["GSM1", "GSM2"], ["Patient_A", "Patient_B"], "A",
                        mapping={"GSM1": "Patient_A", "GSM2": "Patient_B"})
    assert triples(res) == [("GSM1", "Patient_A", "mapping"),
                            ("GSM2", "Patient_B", "mapping")]
    assert combine_outcomes(res.records) == State.COMPATIBLE


def test_M01_N_mapping_to_absent_target_is_need_fact_and_not_matched():
    res = match_samples(["GSM1"], ["Patient_A"], "A", mapping={"GSM1": "Nobody"})
    assert res.matches == []
    rec = by(res.records, "M-01.mapping")
    assert len(rec) == 1 and rec[0].outcome == Outcome.NEED_FACT
    assert rec[0].evidence["problems"][0]["matrix_ids"] == ["GSM1"]


def test_M01_N_two_matrix_ids_mapped_to_same_target_need_fact():
    res = match_samples(["GSM1", "GSM2"], ["Patient_A"], "A",
                        mapping={"GSM1": "Patient_A", "GSM2": "Patient_A"})
    assert res.matches == []
    assert by(res.records, "M-01.mapping")[0].outcome == Outcome.NEED_FACT


def test_M01_N_same_stem_different_studies_not_merged():
    a = match_samples(["S1", "S2"], ["S1", "S2"], "StudyA")
    b = match_samples(["S1", "S2"], ["S1", "S2"], "StudyB")
    keys = {(m["study"], m["sample_id"]) for m in a.matches + b.matches}
    assert keys == {("StudyA", "S1"), ("StudyA", "S2"), ("StudyB", "S1"), ("StudyB", "S2")}
    # a study-A call never sees study-B metadata: a stem missing from A stays unmatched
    c = match_samples(["S1"], ["S2"], "StudyA")
    assert c.matches == [] and c.unmatched_matrix == ["S1"]


@pytest.mark.parametrize("study", [None, "", "   "])
def test_M01_N_missing_study_is_need_fact_and_nothing_matched(study):
    res = match_samples(["S1"], ["S1"], study)
    assert res.matches == []
    rec = by(res.records, "M-01.study")
    assert len(rec) == 1 and rec[0].outcome == Outcome.NEED_FACT
    assert combine_outcomes(res.records) == State.REQUIRES_MANUAL_REVIEW


def test_M01_N_no_match_for_unrelated_ids_is_need_fact():
    res = match_samples(["S1"], ["Z9"], "A")
    assert res.matches == []
    rec = by(res.records, "M-01.unmatched")
    assert len(rec) == 1 and rec[0].outcome == Outcome.NEED_FACT
    assert rec[0].evidence["matrix_ids"] == ["S1"]
    assert combine_outcomes(res.records) == State.REQUIRES_MANUAL_REVIEW


def test_M01_N_empty_matrix_ids_not_assessable():
    res = match_samples([], ["S1"], "A")
    assert [r.outcome for r in res.records] == [Outcome.NOT_ASSESSABLE]


def test_M01_E_metadata_without_matrix_sample_is_only_a_note():
    res = match_samples(["S1"], ["S1", "S2"], "A")
    assert res.unmatched_metadata == ["S2"]
    note = by(res.records, "M-01.unmatched_metadata")
    assert len(note) == 1 and note[0].outcome == Outcome.NOTE
    assert combine_outcomes(res.records) == State.COMPATIBLE


def test_M01_E_duplicate_metadata_ids_need_fact_and_unresolved():
    res = match_samples(["S1", "S2"], ["S1", "S1", "S2"], "A")
    rec = by(res.records, "M-01.duplicate_metadata_ids")
    assert len(rec) == 1 and rec[0].outcome == Outcome.NEED_FACT
    assert rec[0].evidence["ids"] == ["S1"]
    assert triples(res) == [("S2", "S2", "exact")]
    assert res.unmatched_matrix == ["S1"]
    assert combine_outcomes(res.records) == State.REQUIRES_MANUAL_REVIEW


def test_M01_E_duplicate_matrix_ids_need_fact_and_unresolved():
    res = match_samples(["S1", "S1", "S2"], ["S1", "S2"], "A")
    rec = by(res.records, "M-01.duplicate_matrix_ids")
    assert len(rec) == 1 and rec[0].outcome == Outcome.NEED_FACT
    assert triples(res) == [("S2", "S2", "exact")]
    assert res.unmatched_matrix == ["S1", "S1"]


def test_M01_E_normalization_collision_matrix_side_never_picks_one():
    res = match_samples(["A_1", "a-1"], ["A-1"], "A")
    assert res.matches == []
    rec = by(res.records, "M-01.normalization_collision")
    assert len(rec) == 1 and rec[0].outcome == Outcome.NEED_FACT
    g = rec[0].evidence["collisions"][0]
    assert g["normalized"] == "a-1"
    assert g["matrix_ids"] == ["A_1", "a-1"] and g["metadata_ids"] == ["A-1"]


def test_M01_E_normalization_collision_metadata_side_never_picks_one():
    res = match_samples(["a 1"], ["a_1", "A-1"], "A")
    assert res.matches == []
    rec = by(res.records, "M-01.normalization_collision")
    assert len(rec) == 1 and rec[0].outcome == Outcome.NEED_FACT
    assert rec[0].evidence["collisions"][0]["metadata_ids"] == ["a_1", "A-1"]


# ------------------------------------------------------- tier 3 positional
def test_M01_P_positional_match_with_equal_counts_and_documented_order():
    res = match_samples(["x", "y", "z"], ["a", "b", "c"], "A", documented_order=True)
    assert triples(res) == [("x", "a", "positional"), ("y", "b", "positional"),
                            ("z", "c", "positional")]
    note = by(res.records, "M-01.positional")
    assert len(note) == 1 and note[0].outcome == Outcome.NOTE
    assert not by(res.records, "M-01.unmatched")
    strict(res.records)


@pytest.mark.parametrize("flag", [False, None, "yes", 1])
def test_M01_N_positional_not_applied_without_explicit_true(flag):
    res = match_samples(["x", "y"], ["a", "b"], "A", documented_order=flag)
    assert res.matches == []
    rec = by(res.records, "M-01.unmatched")
    assert rec[0].outcome == Outcome.NEED_FACT
    assert "documented_order" in rec[0].evidence["positional"]


def test_M01_N_positional_not_applied_when_counts_differ():
    res = match_samples(["x", "y", "z"], ["a", "b"], "A", documented_order=True)
    assert res.matches == []
    assert "counts differ" in by(res.records, "M-01.unmatched")[0].evidence["positional"]


def test_M01_N_positional_not_applied_when_tier1_or_tier2_matched_something():
    res = match_samples(["S1", "b", "c"], ["S1", "y", "z"], "A", documented_order=True)
    assert triples(res) == [("S1", "S1", "exact")]
    assert res.unmatched_matrix == ["b", "c"]
    assert not by(res.records, "M-01.positional")
    assert by(res.records, "M-01.unmatched")[0].outcome == Outcome.NEED_FACT


def test_M01_N_positional_not_applied_when_ids_duplicated():
    res = match_samples(["x", "x"], ["a", "b"], "A", documented_order=True)
    assert res.matches == []
    assert by(res.records, "M-01.duplicate_matrix_ids")


# ------------------------------------------------------------------- M-02
def test_M02_P_fuzzy_ambiguous_pair_listed_as_candidates_only():
    res = match_samples(["S1"], ["S-1", "S.1"], "A")
    assert res.matches == []  # never an automatic match
    rec = by(res.records, "M-02.candidates")
    assert len(rec) == 1
    r = rec[0]
    assert r.outcome == Outcome.NEED_FACT and r.rule_id == "M-02"
    assert r.confidence is None
    ev = r.evidence
    assert ev["matrix_id"] == "S1" and ev["candidates"] == ["S-1", "S.1"]
    assert "case-folding" in ev["relation"] and "separators" in ev["relation"]
    assert ev["consequence"] and "no match" in ev["consequence"].lower()
    assert "similarity" not in ev and "score" not in ev
    strict(res.records)


def test_M02_N_fuzzy_single_candidate_is_still_not_a_match():
    res = match_samples(["S1"], ["S-1"], "A")
    assert res.matches == []
    rec = by(res.records, "M-02.candidates")
    assert rec[0].evidence["candidates"] == ["S-1"]
    assert not by(res.records, "M-01.unmatched")
    assert combine_outcomes(res.records) == State.REQUIRES_MANUAL_REVIEW


@pytest.mark.parametrize("matrix_id,metadata_id", [
    ("S11", "S1"),                # not an edit-distance relation
    ("GSM123_rep1", "GSM123"),    # not a substring relation
    ("sampl1", "sample1"),        # typo
    ("S1_rep", "S1"),             # token containment
])
def test_M02_N_no_other_similarity_methods(matrix_id, metadata_id):
    res = match_samples([matrix_id], [metadata_id], "A")
    assert res.matches == []
    assert not by(res.records, "M-02.candidates")
    assert by(res.records, "M-01.unmatched")[0].outcome == Outcome.NEED_FACT


def test_M02_E_candidates_only_from_ids_still_unmatched():
    res = match_samples(["S1", "S-1"], ["S-1"], "A")
    assert triples(res) == [("S-1", "S-1", "exact")]
    assert not by(res.records, "M-02.candidates")
    assert res.unmatched_matrix == ["S1"]


def test_M02_E_candidates_exclude_duplicate_metadata_ids():
    res = match_samples(["S1"], ["S-1", "S-1"], "A")
    assert not by(res.records, "M-02.candidates")


def test_M02_E_one_candidate_record_per_unmatched_matrix_id():
    res = match_samples(["S1", "T1"], ["S-1", "T_1"], "A")
    rec = by(res.records, "M-02.candidates")
    assert [r.evidence["matrix_id"] for r in rec] == ["S1", "T1"]


# ------------------------------------------------- inputs, JSON, no mutation
def test_M01_E_non_string_ids_are_stringified_and_serializable():
    res = match_samples([1, 2], [1, 3], 7)
    assert triples(res) == [("1", "1", "exact")]
    assert res.matches[0]["study"] == "7"
    strict(res.records)


def test_M01_E_inputs_not_mutated():
    m, d, mp = ["Sample_1", "x"], ["sample-1", "y"], {"x": "y"}
    before = copy.deepcopy((m, d, mp))
    match_samples(m, d, "A", mapping=mp, documented_order=True)
    assert (m, d, mp) == before


def test_M01_E_all_records_carry_rule_ids_and_version():
    res = match_samples(["S1", "x"], ["S-1", "S1"], "A")
    for r in res.records:
        assert r.rule_id in {"M-01", "M-02"} and r.rule_version == "0.1"
        assert r.scope == "matrix"
    res2 = match_samples(["S1"], ["S1"], "A", scope="studyA")
    assert {r.scope for r in res2.records} == {"studyA"}


# ------------------------------------------------------------------- M-03
def meta(rows):
    return pd.DataFrame(rows, dtype=object)


def test_M03_P_tier_a_complete_passes():
    df = meta({"condition": ["ctrl", "case"], "tissue": ["skin", "skin"]})
    recs = tier_a_check(df, ["condition", "tissue"])
    assert len(recs) == 1 and recs[0].check_id == "M-03.tier_a"
    assert recs[0].outcome == Outcome.PASS and recs[0].rule_id == "M-03"
    assert combine_outcomes(recs) == State.COMPATIBLE
    strict(recs)


def test_M03_N_tier_a_missing_condition_field_need_fact_naming_the_field():
    df = meta({"tissue": ["skin", "skin"]})
    recs = tier_a_check(df, ["condition", "tissue"])
    assert len(recs) == 1
    r = recs[0]
    assert r.check_id == "M-03.condition" and r.outcome == Outcome.NEED_FACT
    assert r.evidence["field"] == "condition" and r.evidence["reason"] == "absent"
    assert "condition" in r.decision_basis
    assert r.evidence["available_fields"] == ["tissue"]
    assert combine_outcomes(recs) == State.REQUIRES_MANUAL_REVIEW


@pytest.mark.parametrize("missing", [None, "", "   ", float("nan"), pd.NA])
def test_M03_N_tier_a_incomplete_field_need_fact_with_rows(missing):
    df = meta({"condition": ["ctrl", missing, "case"], "tissue": ["s", "s", "s"]})
    recs = tier_a_check(df, ["condition", "tissue"])
    assert [r.check_id for r in recs] == ["M-03.condition"]
    ev = recs[0].evidence
    assert recs[0].outcome == Outcome.NEED_FACT
    assert ev["reason"] == "incomplete" and ev["n_missing"] == 1
    assert ev["n_samples"] == 3 and ev["missing_rows"] == [1]
    strict(recs)


def test_M03_N_tier_a_each_missing_field_gets_its_own_record():
    df = meta({"condition": ["a", "b"]})
    recs = tier_a_check(df, ["condition", "tissue", "organism"])
    assert [r.check_id for r in recs] == ["M-03.tissue", "M-03.organism"]
    assert all(r.outcome == Outcome.NEED_FACT for r in recs)


def test_M03_N_tier_a_accepts_list_of_row_dicts():
    rows = [{"condition": "a", "tissue": "x"}, {"condition": None, "tissue": "x"}]
    recs = tier_a_check(rows, ["condition"])
    assert recs[0].outcome == Outcome.NEED_FACT and recs[0].evidence["missing_rows"] == [1]


def test_M03_P_tier_a_does_not_inspect_label_values():
    # Label mapping belongs to M-06, outside T1.7: any non-missing value is present.
    df = meta({"condition": ["lesional skin", "???"]})
    recs = tier_a_check(df, ["condition"])
    assert [r.outcome for r in recs] == [Outcome.PASS]


def test_M03_N_tier_a_field_names_match_exactly():
    df = meta({"Condition": ["a"]})
    recs = tier_a_check(df, ["condition"])
    assert recs[0].outcome == Outcome.NEED_FACT and recs[0].evidence["reason"] == "absent"


def test_M03_N_tier_a_no_rows_need_fact():
    df = pd.DataFrame({"condition": pd.Series([], dtype=object)})
    recs = tier_a_check(df, ["condition"])
    assert recs[0].outcome == Outcome.NEED_FACT and recs[0].evidence["reason"] == "no_rows"


def test_M03_N_tier_a_duplicate_column_label_need_fact():
    df = pd.DataFrame([["a", "b"]], columns=["condition", "condition"], dtype=object)
    recs = tier_a_check(df, ["condition"])
    assert recs[0].outcome == Outcome.NEED_FACT
    assert recs[0].evidence["reason"] == "duplicated_column"


def test_M03_E_tier_a_not_mutating_and_scope():
    df = meta({"condition": ["a", None]})
    before = df.copy(deep=True)
    recs = tier_a_check(df, ["condition"], scope="studyA")
    assert df.equals(before) and recs[0].scope == "studyA"


@pytest.mark.parametrize("fields", [[], None])
def test_M03_E_tier_a_requires_field_list(fields):
    with pytest.raises(ValueError):
        tier_a_check(meta({"condition": ["a"]}), fields)


def test_M03_E_tier_a_unsupported_metadata_type():
    with pytest.raises(TypeError):
        tier_a_check("not a table", ["condition"])


# ------------------------------------- regression: invalid mapping vs tier 3
def test_M01_N_invalid_mapping_cannot_be_bypassed_by_positional_matching():
    res = match_samples(["GSM1"], ["Patient_A"], "StudyA",
                        mapping={"GSM1": "Nobody"}, documented_order=True)
    assert res.matches == []
    assert res.unmatched_matrix == ["GSM1"]
    assert by(res.records, "M-01.positional") == []
    mapping_recs = by(res.records, "M-01.mapping")
    assert len(mapping_recs) == 1 and mapping_recs[0].outcome == Outcome.NEED_FACT
    assert combine_outcomes(res.records) == State.REQUIRES_MANUAL_REVIEW
    strict(res.records)


def test_M01_N_invalid_mapping_blocks_positional_for_all_samples():
    res = match_samples(["GSM1", "GSM2"], ["P_A", "P_B"], "StudyA",
                        mapping={"GSM1": "Nobody"}, documented_order=True)
    assert res.matches == []
    assert by(res.records, "M-01.positional") == []
    assert by(res.records, "M-01.mapping")


def test_M01_N_many_to_one_mapping_cannot_be_bypassed_by_positional_matching():
    res = match_samples(["GSM1", "GSM2"], ["P_A", "P_B"], "StudyA",
                        mapping={"GSM1": "P_A", "GSM2": "P_A"}, documented_order=True)
    assert res.matches == []
    assert by(res.records, "M-01.positional") == []


# ------------------------- regression: normalization collision vs tier 3
def test_M01_N_matrix_side_collision_cannot_be_bypassed_by_positional_matching():
    res = match_samples(["A_1", "a-1"], ["A-1", "x"], "StudyA", documented_order=True)
    assert res.matches == []
    assert res.unmatched_matrix == ["A_1", "a-1"]
    assert res.unmatched_metadata == ["A-1", "x"]
    assert by(res.records, "M-01.positional") == []
    collision = by(res.records, "M-01.normalization_collision")
    assert len(collision) == 1 and collision[0].outcome == Outcome.NEED_FACT
    group = collision[0].evidence["collisions"][0]
    assert group["matrix_ids"] == ["A_1", "a-1"] and group["metadata_ids"] == ["A-1"]
    assert "matches" not in collision[0].evidence
    assert combine_outcomes(res.records) == State.REQUIRES_MANUAL_REVIEW
    strict(res.records)


def test_M01_N_metadata_side_collision_cannot_be_bypassed_by_positional_matching():
    res = match_samples(["a 1", "y"], ["a_1", "A-1"], "StudyA", documented_order=True)
    assert res.matches == []
    assert res.unmatched_matrix == ["a 1", "y"]
    assert res.unmatched_metadata == ["a_1", "A-1"]
    assert by(res.records, "M-01.positional") == []
    collision = by(res.records, "M-01.normalization_collision")
    assert len(collision) == 1 and collision[0].outcome == Outcome.NEED_FACT
    group = collision[0].evidence["collisions"][0]
    assert group["matrix_ids"] == ["a 1"] and group["metadata_ids"] == ["a_1", "A-1"]
    assert "matches" not in collision[0].evidence
    assert "collide" in by(res.records, "M-01.unmatched")[0].evidence["positional"]
    assert combine_outcomes(res.records) == State.REQUIRES_MANUAL_REVIEW
    strict(res.records)


# ----------------------------------------------------- regression: pandas NaT
@pytest.mark.parametrize("nat", [pd.NaT, np.datetime64("NaT", "ns"), np.timedelta64("NaT", "s")])
def test_M03_E_tier_a_nat_is_missing(nat):
    df = pd.DataFrame({"condition": ["a", nat]}, dtype=object)
    recs = tier_a_check(df, ["condition"])
    assert len(recs) == 1 and recs[0].outcome == Outcome.NEED_FACT
    assert recs[0].evidence["reason"] == "incomplete"
    assert recs[0].evidence["missing_rows"] == [1]
    strict(recs)


def test_M03_E_tier_a_datetime_column_with_nat_is_missing():
    df = pd.DataFrame({"date": pd.to_datetime(["2020-01-01", None])})
    recs = tier_a_check(df, ["date"])
    assert recs[0].outcome == Outcome.NEED_FACT
    assert recs[0].evidence["missing_rows"] == [1]


# ------------------------------------- I-12: duplicate metadata rows (M-01)
def dup_records(recs):
    return [r for r in recs if r.check_id == "M-01.duplicate_metadata_rows"]


def mdf(ids, **cols):
    """Metadata frame with the sample-ID column 'sample'; cells stay as given."""
    return pd.DataFrame({"sample": ids, **cols}, dtype=object)


def test_M01_P_metadata_duplicates_unique_ids_give_empty_list():
    df = mdf(["S1", "S2", "S3"], condition=["a", "b", "c"])
    assert find_metadata_duplicates(df, "sample") == []


def test_M01_P_identical_duplicate_rows_are_need_fact_and_retained():
    df = mdf(["S1", "S1", "S2"], condition=["ctrl", "ctrl", "case"], tissue=["skin"] * 3)
    before = df.copy(deep=True)
    recs = find_metadata_duplicates(df, "sample")
    assert len(recs) == 1
    r = recs[0]
    assert (r.rule_id, r.check_id, r.rule_version, r.scope) == (
        "M-01", "M-01.duplicate_metadata_rows", "0.1", "matrix")
    assert r.outcome == Outcome.NEED_FACT
    assert r.confidence is None and r.limitations == ()
    ev = r.evidence
    assert ev["id"] == "S1" and ev["id_column"] == "sample"
    assert ev["row_positions"] == [0, 1] and ev["n_rows"] == 2
    assert ev["classification"] == "identical" and ev["n_fields_compared"] == 2
    assert ev["differing_fields"] == [] and ev["blank"] is False
    assert ev["all_rows_retained"] is True
    assert "none is removed or selected as the correct row" in ev["consequence"]
    assert "identical" in r.decision_basis
    assert "all 2 rows are retained, none is removed or selected as the correct row" in r.decision_basis
    assert combine_outcomes(recs) == State.REQUIRES_MANUAL_REVIEW
    assert df.equals(before)
    strict(recs)


def test_M01_N_conflicting_duplicate_rows_report_differing_fields_and_values():
    df = mdf(["S1", "S1"], condition=["ctrl", "case"], tissue=["skin", "skin"])
    recs = find_metadata_duplicates(df, "sample")
    assert len(recs) == 1 and recs[0].outcome == Outcome.NEED_FACT
    ev = recs[0].evidence
    assert ev["classification"] == "conflicting" and ev["n_fields_compared"] == 2
    assert ev["differing_fields"] == [
        {"field": "condition", "position": 1, "values": ["ctrl", "case"],
         "types": ["str", "str"]}]
    assert "condition" in recs[0].decision_basis
    assert "none is removed or selected as the correct row" in recs[0].decision_basis
    assert ev["all_rows_retained"] is True
    strict(recs)


def test_M01_N_absent_id_column_gives_one_record_and_no_grouping():
    df = mdf(["S1", "S1"], condition=["a", "b"])
    recs = find_metadata_duplicates(df, "patient")
    assert len(recs) == 1
    r = recs[0]
    assert r.rule_id == "M-01" and r.check_id == "M-01.metadata_id_column"
    assert r.outcome == Outcome.NEED_FACT
    assert r.evidence["reason"] == "absent" and r.evidence["id_column"] == "patient"
    assert r.evidence["available_columns"] == ["sample", "condition"]
    assert dup_records(recs) == []
    strict(recs)


def test_M01_N_duplicated_id_column_label_gives_one_record_and_no_grouping():
    df = pd.DataFrame([["S1", "a", "S1"], ["S1", "b", "S1"]],
                      columns=["sample", "condition", "sample"], dtype=object)
    recs = find_metadata_duplicates(df, "sample")
    assert len(recs) == 1
    r = recs[0]
    assert r.check_id == "M-01.metadata_id_column" and r.outcome == Outcome.NEED_FACT
    assert r.evidence["reason"] == "duplicated_column"
    assert r.evidence["column_positions"] == [0, 2]
    assert dup_records(recs) == []
    strict(recs)


@pytest.mark.parametrize("blank", ["", "   ", None, float("nan"), pd.NA])
def test_M01_N_blank_ids_are_reported_with_positions_and_rows_are_kept(blank):
    df = mdf(["S1", blank, "S2"], condition=["a", "b", "c"])
    recs = find_metadata_duplicates(df, "sample")
    assert [r.check_id for r in recs] == ["M-01.metadata_id_column"]
    r = recs[0]
    assert r.rule_id == "M-01" and r.outcome == Outcome.NEED_FACT
    assert r.evidence["reason"] == "blank_ids" and r.evidence["n_blank"] == 1
    assert r.evidence["row_positions"] == [1] and r.evidence["n_rows"] == 3
    assert df.shape == (3, 2)
    strict(recs)


def test_M01_E_repeated_blank_ids_take_part_in_grouping_and_are_flagged():
    df = mdf(["", "", "S1"], condition=["a", "a", "b"])
    recs = find_metadata_duplicates(df, "sample")
    assert [r.check_id for r in recs] == [
        "M-01.metadata_id_column", "M-01.duplicate_metadata_rows"]
    assert recs[0].evidence["n_blank"] == 2
    assert recs[0].evidence["row_positions"] == [0, 1]
    ev = recs[1].evidence
    assert ev["id"] == "" and ev["blank"] is True
    assert ev["row_positions"] == [0, 1] and ev["classification"] == "identical"
    strict(recs)


def test_M01_E_duplicate_ids_agree_with_match_samples():
    ids = ["S1", "S2", "S1", "", "S3", "", "S2"]
    df = mdf(ids, condition=list("abcdefg"))
    mine = [r.evidence["id"] for r in dup_records(find_metadata_duplicates(df, "sample"))]
    theirs = by(match_samples(["S1"], ids, "A").records,
                "M-01.duplicate_metadata_ids")[0].evidence["ids"]
    assert mine == theirs == ["S1", "", "S2"]


@pytest.mark.parametrize("a,b", [
    ("ctrl", "ctrl "), ("ctrl", "Ctrl"), ("", " "), ("NA", ""), ("NA", "NaN")])
def test_M01_E_text_values_compare_exactly(a, b):
    df = mdf(["S1", "S1"], condition=[a, b])
    ev = find_metadata_duplicates(df, "sample")[0].evidence
    assert ev["classification"] == "conflicting"
    assert ev["differing_fields"][0]["values"] == [a, b]


@pytest.mark.parametrize("value", ["", "NA", "ctrl"])
def test_M01_E_equal_text_values_are_identical(value):
    df = mdf(["S1", "S1"], condition=[value, value])
    assert find_metadata_duplicates(df, "sample")[0].evidence["classification"] == "identical"


@pytest.mark.parametrize("a,b", [
    (None, float("nan")),
    (pd.NA, pd.NaT),
    (np.datetime64("NaT", "ns"), None),
    (pd.NaT, np.timedelta64("NaT", "s")),
])
def test_M01_E_typed_missing_values_form_one_class(a, b):
    df = mdf(["S1", "S1"], condition=[a, b])
    recs = find_metadata_duplicates(df, "sample")
    assert recs[0].evidence["classification"] == "identical"
    strict(recs)


@pytest.mark.parametrize("a,b,values,types", [
    (5, "5", ["5", "5"], ["int", "str"]),
    (1, 1.0, ["1", "1.0"], ["int", "float"]),
    (True, 1, ["True", "1"], ["bool", "int"]),
    (None, "", ["None", ""], ["NoneType", "str"]),
    ("NA", None, ["NA", "None"], ["str", "NoneType"]),
])
def test_M01_N_different_value_kinds_are_conflicting(a, b, values, types):
    df = mdf(["S1", "S1"], condition=[a, b])
    recs = find_metadata_duplicates(df, "sample")
    ev = recs[0].evidence
    assert ev["classification"] == "conflicting"
    field = ev["differing_fields"][0]
    assert field["values"] == values and field["types"] == types
    strict(recs)


def test_M01_E_group_of_three_reports_only_fields_that_differ():
    df = mdf(["S1", "S2", "S1", "S1"], condition=["a", "x", "a", "b"],
             tissue=["t", "t", "t", "t"])
    recs = find_metadata_duplicates(df, "sample")
    assert len(recs) == 1
    ev = recs[0].evidence
    assert ev["row_positions"] == [0, 2, 3] and ev["n_rows"] == 3
    assert ev["classification"] == "conflicting"
    assert ev["differing_fields"] == [
        {"field": "condition", "position": 1, "values": ["a", "a", "b"],
         "types": ["str", "str", "str"]}]


def test_M01_E_id_column_is_not_compared_and_ids_group_by_str():
    df = mdf([5, "5"], condition=["a", "a"])
    recs = find_metadata_duplicates(df, "sample")
    assert len(recs) == 1
    ev = recs[0].evidence
    assert ev["id"] == "5" and ev["classification"] == "identical"
    assert ev["differing_fields"] == [] and ev["n_fields_compared"] == 1


def test_M01_E_ids_are_case_sensitive_in_grouping():
    df = mdf(["S1", "s1"], condition=["a", "a"])
    assert find_metadata_duplicates(df, "sample") == []


def test_M01_E_duplicate_labels_among_other_columns_are_reported_by_position():
    df = pd.DataFrame([["S1", "a", "x"], ["S1", "a", "y"]],
                      columns=["sample", "tag", "tag"], dtype=object)
    ev = find_metadata_duplicates(df, "sample")[0].evidence
    assert ev["n_fields_compared"] == 2
    assert ev["differing_fields"] == [
        {"field": "tag", "position": 2, "values": ["x", "y"], "types": ["str", "str"]}]


def test_M01_E_row_positions_are_parsed_row_positions_not_index_labels():
    df = mdf(["S1", "S1"], condition=["a", "a"])
    df.index = [10, 11]
    assert find_metadata_duplicates(df, "sample")[0].evidence["row_positions"] == [0, 1]


def test_M01_E_metadata_duplicates_accept_list_of_row_dicts_and_scope():
    rows = [{"sample": "S1", "c": "a"}, {"sample": "S1", "c": "b"}]
    recs = find_metadata_duplicates(rows, "sample", scope="studyA")
    assert recs[0].scope == "studyA" and recs[0].evidence["classification"] == "conflicting"
    absent = find_metadata_duplicates(rows, "nope", scope="studyA")
    assert absent[0].scope == "studyA"


def test_M01_E_metadata_duplicates_no_rows_give_empty_list():
    df = pd.DataFrame({"sample": pd.Series([], dtype=object)})
    assert find_metadata_duplicates(df, "sample") == []


def test_M01_E_metadata_duplicates_values_are_strict_json_safe():
    df = mdf(["S1", "S1"], when=[pd.Timestamp("2020-01-01"), float("nan")])
    recs = find_metadata_duplicates(df, "sample")
    field = recs[0].evidence["differing_fields"][0]
    assert field["types"] == ["Timestamp", "float"]
    assert all(isinstance(v, str) for v in field["values"])
    strict(recs)
