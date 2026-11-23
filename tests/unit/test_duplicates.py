"""Tests for T1.7 find_duplicates (M-04): non-destructive duplicate detection.

Test names follow test_<RULE>_<P|N|E>_..., with the rule ID written without its
hyphen (M-01 -> M01) because a Python identifier cannot contain "-"."""

import json

import numpy as np
import pandas as pd
import pytest

from bionexus.duplicates import find_duplicates
from bionexus.fileio import first_column_as_index, parse_matrix
from bionexus.records import Outcome, State, combine_outcomes


def frame(rows, columns, index):
    return pd.DataFrame(rows, columns=columns, index=index, dtype=object)


def by(records, check_id):
    return [r for r in records if r.check_id == check_id]


def strict(records):
    for r in records:
        json.dumps(r.to_dict(), allow_nan=False)


def snapshot(df):
    return (df.shape, list(df.columns), list(df.index), df.values.tolist())


def test_M04_P_no_duplicates_passes():
    df = frame([["1", "2"], ["3", "4"]], ["s1", "s2"], ["G1", "G2"])
    recs = find_duplicates(df)
    assert len(recs) == 1 and recs[0].check_id == "M-04.none"
    assert recs[0].outcome == Outcome.PASS and recs[0].rule_id == "M-04"
    assert recs[0].evidence == {"n_columns": 2, "n_rows": 2}
    assert combine_outcomes(recs) == State.COMPATIBLE
    strict(recs)


def test_M04_P_identical_duplicate_sample_columns_recorded_with_note():
    df = frame([["1", "1", "9"], ["2", "2", "8"]], ["s1", "s1", "s2"], ["G1", "G2"])
    recs = find_duplicates(df)
    rec = by(recs, "M-04.duplicate_samples")
    assert len(recs) == 1 and len(rec) == 1
    r = rec[0]
    assert r.outcome == Outcome.NOTE
    assert r.evidence["label"] == "s1" and r.evidence["positions"] == [0, 1]
    assert r.evidence["identical"] is True
    assert "all 2 columns are retained pending an explicit decision" in r.decision_basis
    assert "kept" not in r.decision_basis.lower()
    assert combine_outcomes(recs) == State.COMPATIBLE
    strict(recs)


def test_M04_P_identical_duplicate_gene_rows_recorded_with_note():
    df = frame([["1", "2"], ["1", "2"], ["3", "4"]], ["s1", "s2"], ["G1", "G1", "G2"])
    recs = find_duplicates(df)
    rec = by(recs, "M-04.duplicate_genes")
    assert len(rec) == 1 and rec[0].outcome == Outcome.NOTE
    assert rec[0].evidence["label"] == "G1" and rec[0].evidence["positions"] == [0, 1]
    assert rec[0].evidence["identical"] is True
    assert "all 2 rows are retained pending an explicit decision" in rec[0].decision_basis
    assert "kept" not in rec[0].decision_basis.lower()


def test_M04_N_conflicting_duplicate_sample_columns_need_fact():
    df = frame([["1", "5"], ["2", "2"]], ["s1", "s1"], ["G1", "G2"])
    recs = find_duplicates(df)
    r = by(recs, "M-04.duplicate_samples")[0]
    assert r.outcome == Outcome.NEED_FACT
    assert r.evidence["identical"] is False and r.evidence["n_differing_cells"] == 1
    assert combine_outcomes(recs) == State.REQUIRES_MANUAL_REVIEW
    strict(recs)


def test_M04_N_conflicting_duplicate_gene_rows_need_fact():
    df = frame([["1", "2"], ["1", "3"]], ["s1", "s2"], ["G1", "G1"])
    recs = find_duplicates(df)
    r = by(recs, "M-04.duplicate_genes")[0]
    assert r.outcome == Outcome.NEED_FACT and r.evidence["identical"] is False
    assert combine_outcomes(recs) == State.REQUIRES_MANUAL_REVIEW


def test_M04_N_three_way_group_with_one_different_is_conflicting():
    df = frame([["1", "1", "7"], ["2", "2", "2"]], ["s1", "s1", "s1"], ["G1", "G2"])
    r = by(find_duplicates(df), "M-04.duplicate_samples")[0]
    assert r.outcome == Outcome.NEED_FACT
    assert r.evidence["positions"] == [0, 1, 2]


def test_M04_E_non_destructive_nothing_dropped_or_changed():
    df = frame([["1", "1", "x"], ["1", "1", "y"], ["3", "3", "z"]],
               ["s1", "s1", "s2"], ["G1", "G1", "G2"])
    before = snapshot(df)
    recs = find_duplicates(df)
    assert snapshot(df) == before
    assert df.shape == (3, 3)
    assert by(recs, "M-04.duplicate_samples") and by(recs, "M-04.duplicate_genes")


def test_M04_E_missing_cells_equal_only_to_missing_cells():
    same = frame([[None, None], ["2", "2"]], ["s1", "s1"], ["G1", "G2"])
    assert by(find_duplicates(same), "M-04.duplicate_samples")[0].outcome == Outcome.NOTE
    nan_vs_none = frame([[np.nan, None], ["2", "2"]], ["s1", "s1"], ["G1", "G2"])
    assert by(find_duplicates(nan_vs_none), "M-04.duplicate_samples")[0].outcome == Outcome.NOTE
    empty_vs_none = frame([["", None], ["2", "2"]], ["s1", "s1"], ["G1", "G2"])
    assert by(find_duplicates(empty_vs_none), "M-04.duplicate_samples")[0].outcome == Outcome.NEED_FACT


def test_M04_E_text_and_number_with_same_digits_are_not_identical():
    df = frame([["1", 1], ["2", 2]], ["s1", "s1"], ["G1", "G2"])
    assert by(find_duplicates(df), "M-04.duplicate_samples")[0].outcome == Outcome.NEED_FACT


def test_M04_E_values_are_compared_exactly_not_numerically():
    df = frame([["1.0", "1"], ["2", "2"]], ["s1", "s1"], ["G1", "G2"])
    assert by(find_duplicates(df), "M-04.duplicate_samples")[0].outcome == Outcome.NEED_FACT


def test_M04_N_identical_values_under_different_ids_are_not_duplicates():
    # Duplicates are defined by identifier (AGENT_INSTRUCTIONS section 20), not by value.
    df = frame([["0", "0"], ["0", "0"]], ["s1", "s2"], ["G1", "G2"])
    recs = find_duplicates(df)
    assert [r.check_id for r in recs] == ["M-04.none"]


def test_M04_E_columns_and_rows_both_reported():
    df = frame([["1", "1"], ["1", "1"]], ["s1", "s1"], ["G1", "G1"])
    ids = sorted(r.check_id for r in find_duplicates(df))
    assert ids == ["M-04.duplicate_genes", "M-04.duplicate_samples"]


def test_M04_E_numeric_frame_with_nan_serializes_strictly():
    df = pd.DataFrame([[1.0, 1.0], [np.nan, np.nan]], columns=["s1", "s1"], index=["G1", "G2"])
    recs = find_duplicates(df)
    assert by(recs, "M-04.duplicate_samples")[0].outcome == Outcome.NOTE
    strict(recs)


def test_M04_E_non_string_column_labels_are_not_assessable_never_stringified():
    df = pd.DataFrame([[1, 1], [2, 2]], columns=[5, 5], index=["G1", "G2"], dtype=object)
    recs = find_duplicates(df)
    assert [r.check_id for r in recs] == ["M-04.invalid_sample_labels"]
    r = recs[0]
    assert r.outcome == Outcome.NOT_ASSESSABLE and r.rule_id == "M-04"
    assert r.evidence["axis"] == "columns" and r.evidence["positions"] == [0, 1]
    assert r.evidence["types"] == ["int"]
    assert combine_outcomes(recs) == State.REQUIRES_MANUAL_REVIEW
    strict(recs)


def test_M04_E_non_string_row_labels_are_not_assessable_never_stringified():
    df = pd.DataFrame([[1, 2], [1, 2]], columns=["s1", "s2"], index=[7, 7], dtype=object)
    recs = find_duplicates(df)
    assert [r.check_id for r in recs] == ["M-04.invalid_gene_labels"]
    assert recs[0].outcome == Outcome.NOT_ASSESSABLE
    assert recs[0].evidence["axis"] == "index" and recs[0].evidence["types"] == ["int"]
    strict(recs)


def test_M04_N_int_label_and_text_label_are_never_the_same_identifier():
    # 5 and "5" must not become equivalent through stringification.
    df = pd.DataFrame([[1, 1], [2, 2]], columns=[5, "5"], index=["G1", "G2"], dtype=object)
    recs = find_duplicates(df)
    assert by(recs, "M-04.duplicate_samples") == []
    assert [r.check_id for r in recs] == ["M-04.invalid_sample_labels"]
    assert recs[0].evidence["positions"] == [0]


def test_M04_E_valid_axis_is_still_assessed_when_the_other_axis_is_invalid():
    df = pd.DataFrame([[1, 1], [2, 2]], columns=["s1", "s1"], index=[7, 8], dtype=object)
    ids = sorted(r.check_id for r in find_duplicates(df))
    assert ids == ["M-04.duplicate_samples", "M-04.invalid_gene_labels"]


def test_M04_E_numpy_string_labels_are_text_labels():
    cols = pd.Index([np.str_("s1"), np.str_("s1")], dtype=object)
    df = pd.DataFrame([["1", "1"], ["2", "2"]], columns=cols, index=["G1", "G2"], dtype=object)
    recs = find_duplicates(df)
    assert [r.check_id for r in recs] == ["M-04.duplicate_samples"]


def test_M04_N_labels_are_case_sensitive():
    df = frame([["1", "1"], ["2", "2"]], ["S1", "s1"], ["G1", "g1"])
    assert [r.check_id for r in find_duplicates(df)] == ["M-04.none"]


def test_M04_N_labels_are_compared_including_whitespace():
    df = frame([["1", "1"], ["2", "2"]], ["s1 ", "s1"], [" G1", "G1"])
    assert [r.check_id for r in find_duplicates(df)] == ["M-04.none"]


# ---------------------------------------- I-11: no cross-kind value equality
@pytest.mark.parametrize("a,b", [
    (1, 1.0), (1.0, 1), (True, 1), (1, True), (False, 0), (0, 0.0),
    (np.int64(1), 1.0), (np.float64(1.0), 1), (np.bool_(True), np.int64(1)),
])
def test_M04_N_different_value_kinds_are_not_identical(a, b):
    df = frame([[a, b], ["x", "x"]], ["s1", "s1"], ["G1", "G2"])
    r = by(find_duplicates(df), "M-04.duplicate_samples")[0]
    assert r.outcome == Outcome.NEED_FACT and r.evidence["identical"] is False
    assert r.evidence["n_differing_cells"] == 1


@pytest.mark.parametrize("a,b", [
    (1, 1), (np.int64(1), 1), (1, np.int32(1)), (1.5, 1.5), (np.float64(1.5), 1.5),
    (np.float32(0.5), 0.5), (True, True), (np.bool_(True), True),
])
def test_M04_E_same_kind_values_compare_normally(a, b):
    df = frame([[a, b], ["x", "x"]], ["s1", "s1"], ["G1", "G2"])
    r = by(find_duplicates(df), "M-04.duplicate_samples")[0]
    assert r.outcome == Outcome.NOTE and r.evidence["identical"] is True


def test_M04_N_different_float_values_are_not_identical():
    df = frame([[0.1 + 0.2, 0.3], ["x", "x"]], ["s1", "s1"], ["G1", "G2"])
    r = by(find_duplicates(df), "M-04.duplicate_samples")[0]
    assert r.outcome == Outcome.NEED_FACT


def test_M04_E_numpy_and_builtin_text_are_the_same_kind():
    df = frame([[np.str_("a"), "a"], ["x", "x"]], ["s1", "s1"], ["G1", "G2"])
    assert by(find_duplicates(df), "M-04.duplicate_samples")[0].outcome == Outcome.NOTE


# ------------------------- I-11: text tokens stay text, never interpreted as missing
TOKENS = ["NA", "NaN", "null", ".", ""]


@pytest.mark.parametrize("token", TOKENS)
def test_M04_E_text_token_equals_the_same_token(token):
    df = frame([[token, token], ["x", "x"]], ["s1", "s1"], ["G1", "G2"])
    r = by(find_duplicates(df), "M-04.duplicate_samples")[0]
    assert r.outcome == Outcome.NOTE and r.evidence["identical"] is True


@pytest.mark.parametrize("token", TOKENS)
@pytest.mark.parametrize("sentinel", [None, np.nan, pd.NA, pd.NaT])
def test_M04_N_text_token_is_not_a_missing_sentinel(token, sentinel):
    df = frame([[token, sentinel], ["x", "x"]], ["s1", "s1"], ["G1", "G2"])
    r = by(find_duplicates(df), "M-04.duplicate_samples")[0]
    assert r.outcome == Outcome.NEED_FACT and r.evidence["identical"] is False


@pytest.mark.parametrize("a,b", [(x, y) for x in TOKENS for y in TOKENS if x != y])
def test_M04_N_different_text_tokens_are_not_identical(a, b):
    df = frame([[a, b], ["x", "x"]], ["s1", "s1"], ["G1", "G2"])
    assert by(find_duplicates(df), "M-04.duplicate_samples")[0].outcome == Outcome.NEED_FACT


@pytest.mark.parametrize("a,b", [("a", "A"), ("a", "a "), ("a", " a"), ("1", "01")])
def test_M04_N_text_tokens_are_not_case_folded_or_trimmed(a, b):
    df = frame([[a, b], ["x", "x"]], ["s1", "s1"], ["G1", "G2"])
    assert by(find_duplicates(df), "M-04.duplicate_samples")[0].outcome == Outcome.NEED_FACT


# --------------- I-11: non-string missing sentinels form ONE documented class
SENTINELS = [None, float("nan"), np.float64("nan"), pd.NA, pd.NaT,
             np.datetime64("NaT", "ns"), np.timedelta64("NaT", "s")]


@pytest.mark.parametrize("i", range(len(SENTINELS)))
@pytest.mark.parametrize("j", range(len(SENTINELS)))
def test_M04_E_non_string_missing_sentinels_form_one_class(i, j):
    df = frame([[SENTINELS[i], SENTINELS[j]], ["x", "x"]], ["s1", "s1"], ["G1", "G2"])
    r = by(find_duplicates(df), "M-04.duplicate_samples")[0]
    assert r.outcome == Outcome.NOTE and r.evidence["identical"] is True


def test_M04_N_missing_sentinel_is_not_equal_to_a_number():
    df = frame([[np.nan, 0], ["x", "x"]], ["s1", "s1"], ["G1", "G2"])
    assert by(find_duplicates(df), "M-04.duplicate_samples")[0].outcome == Outcome.NEED_FACT


def test_M04_E_scope_and_versions():
    df = frame([["1", "1"], ["2", "2"]], ["s1", "s1"], ["G1", "G2"])
    for r in find_duplicates(df, scope="studyA"):
        assert r.scope == "studyA" and r.rule_id == "M-04" and r.rule_version == "0.1"


def test_M04_E_works_on_parse_matrix_output_via_first_column_index(tmp_path):
    p = tmp_path / "m.tsv"
    p.write_text("gene\ts1\ts1\nG1\t1\t1\nG1\t1\t2\n", encoding="utf-8")
    res = parse_matrix(p)
    df = first_column_as_index(res.df)
    before = snapshot(df)
    recs = find_duplicates(df)
    assert by(recs, "M-04.duplicate_samples")[0].outcome == Outcome.NEED_FACT
    assert by(recs, "M-04.duplicate_genes")[0].outcome == Outcome.NEED_FACT
    assert snapshot(df) == before


def test_M04_E_empty_frame_passes():
    df = pd.DataFrame(dtype=object)
    recs = find_duplicates(df)
    assert [r.check_id for r in recs] == ["M-04.none"]


# ----------------------------------------------------- regression: pandas NaT
@pytest.mark.parametrize("nat", [pd.NaT, np.datetime64("NaT", "ns"), np.timedelta64("NaT", "s")])
def test_M04_E_nat_cells_equal_missing_cells(nat):
    df = frame([[nat, pd.NaT], ["2", "2"]], ["s1", "s1"], ["G1", "G2"])
    recs = find_duplicates(df)
    r = by(recs, "M-04.duplicate_samples")[0]
    assert r.outcome == Outcome.NOTE and r.evidence["identical"] is True
    strict(recs)


def test_M04_E_nat_equals_none_and_nan_but_not_a_value():
    same = frame([[pd.NaT, None], [np.nan, pd.NaT]], ["s1", "s1"], ["G1", "G2"])
    assert by(find_duplicates(same), "M-04.duplicate_samples")[0].outcome == Outcome.NOTE
    diff = frame([[pd.NaT, "x"], ["2", "2"]], ["s1", "s1"], ["G1", "G2"])
    assert by(find_duplicates(diff), "M-04.duplicate_samples")[0].outcome == Outcome.NEED_FACT


def test_M04_E_duplicate_rows_with_nat_are_identical():
    df = frame([[pd.NaT, "1"], [pd.NaT, "1"]], ["s1", "s2"], ["G1", "G1"])
    r = by(find_duplicates(df), "M-04.duplicate_genes")[0]
    assert r.outcome == Outcome.NOTE and r.evidence["identical"] is True


def test_M04_E_datetime_dtype_columns_with_nat_are_identical():
    col = pd.to_datetime(["2020-01-01", None])
    df = pd.DataFrame({"a": col, "b": col})
    df.columns = ["s1", "s1"]
    r = by(find_duplicates(df), "M-04.duplicate_samples")[0]
    assert r.outcome == Outcome.NOTE
