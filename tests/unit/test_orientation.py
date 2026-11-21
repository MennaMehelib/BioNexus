import json

import numpy as np
import pandas as pd
import pytest

from bionexus.orientation import OrientationResult, detect_orientation
from bionexus.records import Outcome

GENE_PATTERNS = [r"ENSG\d+"]
SAMPLE_PATTERNS = [r"GSM\d+"]
GENES = ["ENSG1", "ENSG2", "ENSG3", "ENSG4"]
SAMPLES = ["GSM1", "GSM2"]
META = ["GSM1", "GSM2"]


def correct_df():
    return pd.DataFrame(
        [["1.50", "2"], ["0", "007"], ["NA", "4"], ["5", "6"]],
        index=GENES,
        columns=SAMPLES,
        dtype=object,
    )


def kw(**over):
    d = dict(
        metadata_sample_ids=META,
        gene_patterns=GENE_PATTERNS,
        sample_patterns=SAMPLE_PATTERNS,
    )
    d.update(over)
    return d


def outcomes(res):
    return [r.outcome for r in res.records]


def check_records(res):
    assert isinstance(res, OrientationResult)
    assert res.records
    for r in res.records:
        assert r.rule_id == "G-03"
        json.dumps(r.to_dict())


def test_already_correct_all_signals():
    df = correct_df()
    res = detect_orientation(df, **kw())
    check_records(res)
    assert outcomes(res) == [Outcome.PASS]
    pd.testing.assert_frame_equal(res.df_oriented, df)


def test_clearly_transposed_all_signals():
    df = correct_df().T
    res = detect_orientation(df, **kw())
    check_records(res)
    assert outcomes(res) == [Outcome.RESOLVED]
    pd.testing.assert_frame_equal(res.df_oriented, df.T)
    assert list(res.df_oriented.index) == GENES
    assert list(res.df_oriented.columns) == SAMPLES


def test_values_identical_after_transpose():
    df = correct_df().T
    expected = df.values.T.tolist()
    res = detect_orientation(df, **kw())
    assert res.df_oriented.values.tolist() == expected
    assert correct_df().values.tolist() == res.df_oriented.values.tolist()


def test_input_not_mutated():
    df = correct_df().T
    snapshot = df.copy(deep=True)
    detect_orientation(df, **kw())
    pd.testing.assert_frame_equal(df, snapshot)


def test_square_matrix_need_fact():
    df = pd.DataFrame(np.arange(4).reshape(2, 2), index=["ENSG1", "ENSG2"], columns=SAMPLES)
    res = detect_orientation(df, **kw())
    check_records(res)
    assert outcomes(res) == [Outcome.NEED_FACT]
    pd.testing.assert_frame_equal(res.df_oriented, df)


def test_signals_disagree_length_vs_patterns():
    # labels say genes are rows, but rows are the shorter axis
    df = pd.DataFrame(np.arange(6).reshape(2, 3), index=["ENSG1", "ENSG2"], columns=["GSM1", "GSM2", "GSM3"]).T
    df = df.T  # 2 rows (genes) x 3 columns (samples): correct labels, rows shorter
    res = detect_orientation(df, **kw(metadata_sample_ids=["GSM1", "GSM2", "GSM3"]))
    check_records(res)
    assert outcomes(res) == [Outcome.NEED_FACT]
    pd.testing.assert_frame_equal(res.df_oriented, df)


def test_signals_disagree_metadata_vs_length():
    df = correct_df()  # length: correct; metadata ids found on the rows instead
    res = detect_orientation(
        df, metadata_sample_ids=GENES, gene_patterns=None, sample_patterns=None
    )
    assert outcomes(res) == [Outcome.NEED_FACT]
    pd.testing.assert_frame_equal(res.df_oriented, df)


def test_metadata_matches_both_axes_is_ambiguous():
    df = correct_df()
    res = detect_orientation(
        df, metadata_sample_ids=GENES + SAMPLES, gene_patterns=None, sample_patterns=None
    )
    assert outcomes(res) == [Outcome.NEED_FACT]


def test_patterns_match_nothing_is_ambiguous():
    df = correct_df().T
    res = detect_orientation(
        df, gene_patterns=[r"NOPE\d+"], sample_patterns=[r"ZZZ\d+"]
    )
    assert outcomes(res) == [Outcome.NEED_FACT]
    pd.testing.assert_frame_equal(res.df_oriented, df)


def test_length_only_transposes_wrong_axis():
    # a single available, unambiguous signal is sufficient to transpose
    df = correct_df().T
    res = detect_orientation(df)
    assert outcomes(res) == [Outcome.RESOLVED]
    pd.testing.assert_frame_equal(res.df_oriented, df.T)


def test_transpose_preserves_exact_values_mixed_dtypes():
    big = 9007199254740993  # 2**53 + 1: not representable as float64
    df = pd.DataFrame(
        {
            "i1": pd.Series([big, 2], dtype="int64"),
            "f1": pd.Series([0.5, 1.25], dtype="float64"),
            "i2": pd.Series([3, 4], dtype="int64"),
        }
    )
    assert df.shape == (2, 3)  # rows shorter than columns: length says transpose
    snapshot = df.copy(deep=True)
    res = detect_orientation(df)
    assert outcomes(res) == [Outcome.RESOLVED]
    out = res.df_oriented
    assert out.shape == (3, 2)
    assert out.loc["i1", 0] == big
    assert isinstance(out.loc["i1", 0], int)
    assert out.loc["f1", 0] == 0.5
    assert not any(dt == "float64" for dt in out.dtypes)
    pd.testing.assert_frame_equal(df, snapshot)
    assert df["i1"].dtype == "int64" and int(df["i1"][0]) == big


def test_length_only_correct_axis_passes():
    df = correct_df()
    res = detect_orientation(df)
    assert outcomes(res) == [Outcome.PASS]
    pd.testing.assert_frame_equal(res.df_oriented, df)


def test_two_agreeing_signals_without_patterns_transpose():
    df = correct_df().T
    res = detect_orientation(df, metadata_sample_ids=META)
    assert outcomes(res) == [Outcome.RESOLVED]
    pd.testing.assert_frame_equal(res.df_oriented, df.T)


def test_no_builtin_patterns():
    # without caller-supplied patterns, ENSG/GSM labels carry no meaning
    df = correct_df().T
    res = detect_orientation(df)
    assert res.records[0].evidence["signals"]["labels"]["available"] is False


def test_empty_axis_need_fact():
    df = pd.DataFrame(index=["ENSG1"], columns=[], dtype=object)
    res = detect_orientation(df, **kw())
    assert outcomes(res) == [Outcome.NEED_FACT]


def test_scope_is_used():
    res = detect_orientation(correct_df(), scope="studyA", **kw())
    assert res.records[0].scope == "studyA"
