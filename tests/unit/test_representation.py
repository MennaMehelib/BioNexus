import json

import numpy as np
import pandas as pd
import pytest

from bionexus.fileio import parse_matrix
from bionexus.records import Outcome
from bionexus.representation import RepresentationEvidence, evidence_record
from bionexus.rules import RuleDisabled, RuleRegistry

BIG = 9007199254740993  # 2**53 + 1, not representable as float64


def obj(data, index=("G1", "G2", "G3")):
    """T1.3-style frame: dtype=object, every cell an exact source string."""
    return pd.DataFrame(data, index=list(index), dtype=object)


def counts():
    return pd.DataFrame({"s1": [10, 0, 5], "s2": [3, 100, 0]}, index=["G1", "G2", "G3"])


def outcomes(res):
    return [r.outcome for r in res.records]


def rec(res, rule_id=None, outcome=None):
    return [
        r for r in res.records
        if (rule_id is None or r.rule_id == rule_id)
        and (outcome is None or r.outcome is outcome)
    ]


def strict_json(res):
    return json.loads(json.dumps(res.to_dict(), allow_nan=False))


def unchanged(df):
    snap = df.copy(deep=True)
    res = evidence_record(df)
    pd.testing.assert_frame_equal(df, snap)
    return res


# ---------------------------------------------------------------- facts / R-01
def test_integer_counts_are_r1_candidate():
    res = unchanged(counts())
    assert isinstance(res, RepresentationEvidence)
    assert res.all_integer_valued is True
    assert res.any_negative is False
    assert res.r1_candidate is True
    assert outcomes(res) == [Outcome.PASS]
    assert res.records[0].rule_id == "R-01"


def test_facts_values():
    res = evidence_record(counts())
    assert res.any_na is False
    assert res.n_na_genes == 0 and res.na_genes == []
    assert res.minimum == 0
    assert res.zero_fraction == pytest.approx(2 / 6)
    assert res.col_sums == [15, 103]
    assert res.col_sum_min == 15 and res.col_sum_max == 103


def test_one_negative_not_r1():
    df = pd.DataFrame({"s1": [10, -1, 5], "s2": [3, 100, 0]}, index=["G1", "G2", "G3"])
    res = unchanged(df)
    assert res.any_negative is True
    assert res.r1_candidate is False
    assert res.minimum == -1
    assert Outcome.PASS not in outcomes(res)


def test_non_integer_undeclared_need_fact():
    df = pd.DataFrame({"s1": [1.5, 2.0], "s2": [0.0, 7.25]}, index=["G1", "G2"])
    res = unchanged(df)
    assert res.all_integer_valued is False
    assert res.r1_candidate is False
    r = rec(res, outcome=Outcome.NEED_FACT)
    assert len(r) == 1 and r[0].rule_id == "R-02"


def test_whole_number_floats_are_integer_valued():
    df = pd.DataFrame({"s1": [1.0, 2.0], "s2": [0.0, 7.0]}, index=["G1", "G2"])
    assert evidence_record(df).r1_candidate is True


def test_column_sums_non_integer():
    df = pd.DataFrame({"s1": [1.5, 2.25], "s2": [0.5, 0.5]}, index=["G1", "G2"])
    res = evidence_record(df)
    assert res.col_sums == pytest.approx([3.75, 1.0])
    assert res.col_sum_min == pytest.approx(1.0)
    assert res.col_sum_max == pytest.approx(3.75)


# ------------------------------------------------------------ declared / R-02
def test_declared_r1_with_non_integers_blocked():
    df = pd.DataFrame({"s1": [1.5, 2.0]}, index=["G1", "G2"])
    snap = df.copy(deep=True)
    res = evidence_record(df, declared="R1")
    pd.testing.assert_frame_equal(df, snap)
    assert res.declared == "R1"
    b = rec(res, outcome=Outcome.BLOCKED)
    assert len(b) == 1 and b[0].decision_basis


def test_declared_r1_consistent_passes():
    res = evidence_record(counts(), declared="R1")
    assert res.declared == "R1"
    assert Outcome.BLOCKED not in outcomes(res)
    assert Outcome.PASS in outcomes(res)


def test_declared_r1_with_negatives_blocked():
    df = pd.DataFrame({"s1": [10, -1]}, index=["G1", "G2"])
    assert Outcome.BLOCKED in outcomes(evidence_record(df, declared="R1"))


def test_declared_linear_with_negatives_need_fact():
    df = pd.DataFrame({"s1": [10, -1]}, index=["G1", "G2"])
    res = evidence_record(df, declared="linear")
    assert res.declared == "linear"
    assert Outcome.NEED_FACT in outcomes(res)
    assert Outcome.BLOCKED not in outcomes(res)


def test_declared_linear_without_negatives_passes():
    res = evidence_record(counts(), declared="linear")
    assert res.declared == "linear"
    assert outcomes(res) == [Outcome.PASS]


def test_other_declared_label_only_recorded():
    res = evidence_record(counts(), declared="something-else")
    assert res.declared == "something-else"
    assert outcomes(res) == [Outcome.NOTE]


def test_undeclared_is_none():
    assert evidence_record(counts()).declared is None


# --------------------------------------------------------------------- R-06
def test_na_genes_listed_matrix_unchanged():
    df = pd.DataFrame({"s1": [10, np.nan, 5], "s2": [3, 100, np.nan]},
                      index=["G1", "G2", "G3"])
    res = unchanged(df)
    assert res.any_na is True
    assert res.na_genes == ["G2", "G3"] and res.n_na_genes == 2
    assert res.col_sums == [15, 103]
    assert df.isna().sum().sum() == 2  # nothing imputed
    assert rec(res, "R-06")


def test_string_empty_cell_is_missing():
    df = obj({"s1": ["10", "", "5"], "s2": ["3", "100", "0"]})
    res = unchanged(df)
    assert res.na_genes == ["G2"]
    assert res.col_sums == [15, 103]
    assert res.minimum == 0


def test_parser_output_end_to_end(tmp_path):
    p = tmp_path / "m.tsv"
    p.write_text("gene\ts1\ts2\nG1\t10\t3\nG2\t\t100\nG3\t5\t0\n", encoding="utf-8")
    parsed = parse_matrix(p)
    df = parsed.df.set_index("gene")
    res = unchanged(df)
    assert res.na_genes == ["G2"]
    assert res.r1_candidate is True
    assert res.col_sums == [15, 103]


def test_string_values_not_converted_in_input():
    df = obj({"s1": ["1.50", "007", "1e3"]})
    unchanged(df)
    assert df["s1"].tolist() == ["1.50", "007", "1e3"]


# ----------------------------------------------- exact numbers / non-numeric
def test_large_integer_string_exact():
    df = obj({"s1": [str(BIG), "2", "3"], "s2": ["4", "5", "6"]})
    res = unchanged(df)
    assert res.r1_candidate is True
    assert res.col_sums[0] == BIG + 5
    assert isinstance(res.col_sums[0], int)
    assert res.minimum == 2


def test_large_integer_is_minimum_exactly():
    df = obj({"s1": [str(BIG), str(BIG + 2)]}, index=("G1", "G2"))
    res = unchanged(df)
    assert res.minimum == BIG and isinstance(res.minimum, int)


def test_large_integer_native_int64():
    df = pd.DataFrame({"s1": np.array([BIG, 2], dtype="int64")}, index=["G1", "G2"])
    res = unchanged(df)
    assert res.col_sums == [BIG + 2]
    assert res.minimum == 2


def test_integer_valued_decimal_strings():
    df = obj({"s1": ["1e3", "2.0", "0"]})
    res = unchanged(df)
    assert res.all_integer_valued is True
    assert res.col_sums == [1002]


@pytest.mark.parametrize(
    "bad", ["SYMBOL", "NA", "nan", "inf", "-Infinity", "1/2", "1_0", "  ", "0x10", "True"]
)
def test_non_numeric_content_not_assessable(bad):
    df = obj({"s1": ["10", bad, "5"]})
    res = unchanged(df)
    assert outcomes(res) == [Outcome.NOT_ASSESSABLE]
    assert res.r1_candidate is False
    assert res.minimum is None and res.col_sums == [None]
    assert bad in json.dumps(res.records[0].to_dict()["evidence"])
    strict_json(res)


def test_native_bool_and_inf_not_assessable():
    df = pd.DataFrame({"s1": [True, False]}, index=["G1", "G2"], dtype=object)
    assert outcomes(evidence_record(df)) == [Outcome.NOT_ASSESSABLE]
    df2 = pd.DataFrame({"s1": [1.0, float("inf")]}, index=["G1", "G2"])
    assert outcomes(evidence_record(df2)) == [Outcome.NOT_ASSESSABLE]


# ------------------------------------------------------- all-NA / empty / JSON
def test_all_na_matrix_strict_json():
    df = pd.DataFrame({"s1": [np.nan, np.nan], "s2": [np.nan, np.nan]}, index=["G1", "G2"])
    res = unchanged(df)
    assert res.any_na is True and res.n_na_genes == 2
    assert res.minimum is None and res.zero_fraction is None
    assert res.col_sums == [None, None]
    assert res.col_sum_min is None and res.col_sum_max is None
    assert res.r1_candidate is False and res.all_integer_valued is False
    assert Outcome.NOT_ASSESSABLE in outcomes(res)
    d = strict_json(res)
    assert d["col_sums"] == [None, None]


def test_all_empty_string_matrix():
    res = unchanged(obj({"s1": ["", ""]}, index=("G1", "G2")))
    assert res.col_sums == [None] and Outcome.NOT_ASSESSABLE in outcomes(res)
    strict_json(res)


def test_column_all_missing_sum_none():
    df = pd.DataFrame({"s1": [1, 2], "s2": [np.nan, np.nan]}, index=["G1", "G2"])
    res = evidence_record(df)
    assert res.col_sums == [3, None]
    assert res.col_sum_min == 3 and res.col_sum_max == 3
    strict_json(res)


def test_empty_frame_not_assessable():
    res = evidence_record(pd.DataFrame())
    assert Outcome.NOT_ASSESSABLE in outcomes(res)
    strict_json(res)


@pytest.mark.parametrize("declared", [None, "R1", "linear"])
def test_to_dict_strict_json_all_paths(declared):
    df = pd.DataFrame({"s1": [1.5, np.nan], "s2": [2, -3]}, index=["G1", "G2"])
    strict_json(evidence_record(df, declared=declared, annotation_genes=["G1", "X"]))


# ----------------------------------------------------------------------- R-05
def test_universe_all_present_no_limitation():
    res = evidence_record(counts(), annotation_genes=["G1", "G2", "G3"])
    assert res.annotation_fraction == 1.0
    assert Outcome.LIMITATION not in outcomes(res)


def test_universe_subset_limitation():
    res = unchanged_with(annotation_genes=["G1", "G2", "G3", "G4", "G5"])
    assert res.annotation_fraction == pytest.approx(3 / 5)
    lim = rec(res, "R-05", Outcome.LIMITATION)
    assert len(lim) == 1
    ev = lim[0].evidence
    assert ev["annotation_genes"] == 5 and ev["present"] == 3 and ev["absent"] == 2


def unchanged_with(**kw):
    df = counts()
    snap = df.copy(deep=True)
    res = evidence_record(df, **kw)
    pd.testing.assert_frame_equal(df, snap)
    return res


def test_universe_basis_only_states_calculated_facts():
    res = evidence_record(counts(), annotation_genes=["G1", "X"])
    basis = rec(res, "R-05", Outcome.LIMITATION)[0].decision_basis.lower()
    assert "threshold" not in basis
    assert "computed" not in basis and "normalis" not in basis
    assert "1 of 2" in basis


def test_universe_duplicates_in_list_counted_once():
    res = evidence_record(counts(), annotation_genes=["G1", "G1", "X"])
    assert res.annotation_fraction == pytest.approx(1 / 2)


def test_universe_none_has_no_fraction():
    res = evidence_record(counts())
    assert res.annotation_fraction is None
    assert not rec(res, "R-05")


def test_universe_empty_list():
    res = unchanged_with(annotation_genes=[])
    assert res.annotation_fraction is None
    assert Outcome.LIMITATION not in outcomes(res)
    assert rec(res, "R-05", Outcome.NOTE)
    strict_json(res)


# ----------------------------------------------------------------------- R-03
def test_r03_registry_disabled_and_not_inferred():
    reg = RuleRegistry()
    assert reg.is_enabled("R-03") is False
    with pytest.raises(RuleDisabled):
        reg.require_enabled("R-03")
    # constant column sums: nothing may be inferred about CPM/TPM/RPKM
    df = pd.DataFrame({"s1": [250000.0, 750000.0], "s2": [500000.0, 500000.0]},
                      index=["G1", "G2"])
    res = evidence_record(df)
    text = json.dumps(res.to_dict()).lower()
    assert "cpm" not in text and "tpm" not in text and "rpkm" not in text
    assert [f for f in vars(res) if any(k in f for k in ("cpm", "tpm", "rpkm", "constant"))] == []


# ---------------------------------------------------------------------- misc
def test_records_valid_and_scope():
    res = evidence_record(counts(), declared="R1", scope="studyA")
    assert all(r.scope == "studyA" for r in res.records)
    assert all(r.rule_id in {"R-01", "R-02", "R-05", "R-06"} for r in res.records)


# ------------------------------------------- exact min/max (before conversion)
def test_col_sum_min_max_compared_exactly():
    # exact column sums: s1 = 9007199254740993.5, s2 = 9007199254740994.
    # Both round to the same float64, so comparing converted values cannot tell
    # which is smaller; comparing exact values can.
    df = obj({"s1": ["9007199254740993.5"], "s2": ["9007199254740994"]}, index=("G1",))
    res = unchanged(df)
    assert res.col_sum_max == 9007199254740994
    assert isinstance(res.col_sum_max, int)  # the exact maximum is the integer column
    assert res.col_sum_min == "9007199254740993.5"  # exact minimum, not rounded
    assert strict_json(res)["col_sum_min"] == "9007199254740993.5"


def test_exact_decimal_string_when_float_would_lose_precision():
    df = obj({"s1": ["9007199254740993.5"]}, index=("G1",))
    res = unchanged(df)
    for v in (res.minimum, res.col_sums[0], res.col_sum_min, res.col_sum_max):
        assert v == "9007199254740993.5" and isinstance(v, str)
    d = strict_json(res)
    assert d["minimum"] == "9007199254740993.5"
    assert d["col_sums"] == ["9007199254740993.5"]
    assert d["col_sum_min"] == d["col_sum_max"] == "9007199254740993.5"


def test_negative_lossy_value_exact_string():
    df = obj({"s1": ["-9007199254740993.5"]}, index=("G1",))
    res = unchanged(df)
    assert res.minimum == "-9007199254740993.5"


def test_mixed_large_integer_and_fraction_sum_exact():
    df = obj({"s1": [str(BIG), "0.5"], "s2": ["1", "2"]}, index=("G1", "G2"))
    res = unchanged(df)
    assert res.minimum == 0.5 and isinstance(res.minimum, float)
    assert res.col_sums == ["9007199254740993.5", 3]
    assert res.all_integer_valued is False
    assert strict_json(res)["col_sums"] == ["9007199254740993.5", 3]


def test_ordinary_fractions_stay_float():
    df = obj({"s1": ["1.5", "2.25"], "s2": ["0.1", "2.3"]}, index=("G1", "G2"))
    res = unchanged(df)
    assert isinstance(res.col_sums[0], float) and res.col_sums[0] == 3.75
    assert isinstance(res.minimum, float) and res.minimum == 0.1
    assert isinstance(res.col_sums[1], float)
    d = strict_json(res)
    assert d["col_sums"][0] == 3.75 and isinstance(d["col_sums"][0], float)


def test_native_float_values_stay_float_when_lossless():
    df = pd.DataFrame({"s1": [0.5, 0.25], "s2": [0.1, 0.0]}, index=["G1", "G2"])
    res = unchanged(df)
    assert isinstance(res.col_sums[0], float) and res.col_sums[0] == 0.75
    assert isinstance(res.col_sums[1], float) and res.col_sums[1] == 0.1


def test_native_float_sum_not_exactly_a_float_is_exact_string():
    # 0.1 and 0.25 are doubles whose exact sum is not itself a double: the exact
    # decimal digits are reported rather than a rounded float.
    from fractions import Fraction

    df = pd.DataFrame({"s1": [0.1, 0.25]}, index=["G1", "G2"])
    res = unchanged(df)
    s = res.col_sums[0]
    assert isinstance(s, str)
    assert Fraction(s) == Fraction(0.1) + Fraction(0.25)


def test_integral_values_stay_int():
    res = evidence_record(obj({"s1": ["1e3", "2.0"]}, index=("G1", "G2")))
    assert res.col_sums == [1002] and isinstance(res.col_sums[0], int)
    assert isinstance(res.minimum, int)


def test_whole_sample_na_alongside_non_numeric_cell():
    df = obj({"s1": ["10", "SYMBOL"], "s2": ["", ""], "s3": ["1", "2"]}, index=("G1", "G2"))
    res = unchanged(df)
    assert rec(res, "R-01", Outcome.NOT_ASSESSABLE)
    ws = rec(res, "R-06", Outcome.NEED_FACT)
    assert len(ws) == 1 and ws[0].evidence["whole_sample_na"] == ["s2"]
    # genes with missing values are still listed (s2 is missing for both genes)
    assert res.any_na is True
    assert res.n_na_genes == 2 and res.na_genes == ["G1", "G2"]
    note = rec(res, "R-06", Outcome.NOTE)
    assert len(note) == 1 and note[0].evidence["na_genes"] == ["G1", "G2"]
    # no numeric facts are reported
    assert res.minimum is None and res.zero_fraction is None
    assert res.col_sums == [None, None, None]
    assert res.col_sum_min is None and res.col_sum_max is None
    assert res.r1_candidate is False and res.all_integer_valued is False
    assert res.any_negative is False
    strict_json(res)


def test_non_numeric_cell_with_partial_missingness_elsewhere():
    df = obj({"s1": ["SYMBOL", "2", "3"], "s2": ["1", "", "3"]}, index=("G1", "G2", "G3"))
    res = unchanged(df)
    assert rec(res, "R-01", Outcome.NOT_ASSESSABLE)
    assert not rec(res, "R-06", Outcome.NEED_FACT)  # no whole-sample NA
    note = rec(res, "R-06", Outcome.NOTE)
    assert len(note) == 1 and note[0].evidence["na_genes"] == ["G2"]
    assert res.any_na is True and res.n_na_genes == 1 and res.na_genes == ["G2"]
    assert res.minimum is None and res.col_sums == [None, None]
    assert res.r1_candidate is False
    strict_json(res)


def test_column_with_non_numeric_and_missing_is_not_whole_sample_na():
    df = obj({"s1": ["SYMBOL", ""], "s2": ["1", "2"]}, index=("G1", "G2"))
    res = unchanged(df)
    # s1 is not whole-sample missing (it has "SYMBOL" and ""), so no NEED_FACT.
    assert not rec(res, "R-06", Outcome.NEED_FACT)
    # But G2 has a missing cell (s1=""), so the R-06 NOTE is still emitted.
    note = rec(res, "R-06", Outcome.NOTE)
    assert len(note) == 1 and note[0].evidence["na_genes"] == ["G2"]
    assert res.any_na is True and res.n_na_genes == 1 and res.na_genes == ["G2"]
    assert set(outcomes(res)) == {Outcome.NOT_ASSESSABLE, Outcome.NOTE}


# ---------------------------------------------------------------- whole-sample NA
def test_whole_sample_na_need_fact():
    df = pd.DataFrame({"s1": [1, 2, 3], "s2": [np.nan] * 3, "s3": [4, 5, 6]},
                      index=["G1", "G2", "G3"])
    res = unchanged(df)
    r = rec(res, "R-06", Outcome.NEED_FACT)
    assert len(r) == 1
    assert r[0].evidence["whole_sample_na"] == ["s2"]
    assert res.na_genes == ["G1", "G2", "G3"]  # gene-level list preserved
    assert Outcome.NOTE in outcomes(res)       # gene-level NOTE preserved
    assert res.col_sums == [6, None, 15]
    strict_json(res)


def test_partial_missing_column_is_not_whole_sample_na():
    df = pd.DataFrame({"s1": [1, np.nan, 3], "s2": [4, 5, 6]}, index=["G1", "G2", "G3"])
    res = unchanged(df)
    assert not rec(res, "R-06", Outcome.NEED_FACT)
    assert res.na_genes == ["G2"]


def test_multiple_whole_sample_na_columns_string_empty_cells():
    df = obj({"s1": ["1", "2"], "s2": ["", ""], "s3": ["", ""], "s4": ["", "7"]},
             index=("G1", "G2"))
    res = unchanged(df)
    r = rec(res, "R-06", Outcome.NEED_FACT)
    assert len(r) == 1
    assert r[0].evidence["whole_sample_na"] == ["s2", "s3"]
    assert r[0].evidence["n_whole_sample_na"] == 2


def test_whole_sample_na_when_entire_matrix_missing():
    df = pd.DataFrame({"s1": [np.nan, np.nan], "s2": [np.nan, np.nan]}, index=["G1", "G2"])
    res = evidence_record(df)
    assert rec(res, "R-06", Outcome.NEED_FACT)[0].evidence["whole_sample_na"] == ["s1", "s2"]
    assert Outcome.NOT_ASSESSABLE in outcomes(res)  # existing behaviour kept


def test_no_whole_sample_na_record_without_missing_and_for_zero_rows():
    assert not rec(evidence_record(counts()), "R-06")
    res = evidence_record(pd.DataFrame({"s1": [], "s2": []}))
    assert not rec(res, "R-06", Outcome.NEED_FACT)
