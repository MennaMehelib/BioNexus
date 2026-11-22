import json

import pytest

from bionexus.provenance import sha256_file
from bionexus.records import Outcome
from bionexus.fileio import ParseResult, parse_matrix


def put(tmp_path, name, data):
    p = tmp_path / name
    p.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
    return p


def outcomes(res):
    return [r.outcome for r in res.records]


def assert_ok(res):
    assert isinstance(res, ParseResult)
    assert res.df is not None
    assert Outcome.PASS in outcomes(res)
    assert not {Outcome.BLOCKED, Outcome.NOT_ASSESSABLE} & set(outcomes(res))
    assert all(r.rule_id == "G-02" for r in res.records)
    for r in res.records:
        json.dumps(r.to_dict())


@pytest.mark.parametrize(
    "name,sep",
    [("m.tsv", "\t"), ("m.csv", ","), ("m.txt", ";")],
)
def test_delimiters(tmp_path, name, sep):
    text = sep.join(["gene", "s1", "s2"]) + "\n" + sep.join(["A", "1", "2"]) + "\n" + sep.join(["B", "3", "4"]) + "\n"
    res = parse_matrix(put(tmp_path, name, text))
    assert_ok(res)
    assert list(res.df.columns) == ["gene", "s1", "s2"]
    assert res.df.shape == (2, 3)
    assert res.df.iloc[1].tolist() == ["B", "3", "4"]


def test_bom(tmp_path):
    p = put(tmp_path, "b.tsv", b"\xef\xbb\xbfgene\ts1\nA\t1\n")
    res = parse_matrix(p)
    assert_ok(res)
    assert list(res.df.columns) == ["gene", "s1"]
    assert any("BOM" in c for c in res.change_log)


def test_quoted_fields(tmp_path):
    p = put(tmp_path, "q.csv", '"gene","s1","s2"\n"A","1","2"\n')
    res = parse_matrix(p)
    assert_ok(res)
    assert list(res.df.columns) == ["gene", "s1", "s2"]
    assert res.df.iloc[0].tolist() == ["A", "1", "2"]
    assert any("quot" in c for c in res.change_log)


def test_quoted_field_containing_delimiter(tmp_path):
    p = put(tmp_path, "q.tsv", 'gene\ts1\n"A,1"\t5\n')
    res = parse_matrix(p)
    assert_ok(res)
    assert res.df.iloc[0].tolist() == ["A,1", "5"]


def test_ragged_header(tmp_path):
    p = put(tmp_path, "r.tsv", "s1\ts2\ts3\nA\t1\t2\t3\nB\t4\t5\t6\n")
    res = parse_matrix(p)
    assert_ok(res)
    assert res.df.shape == (2, 4)
    assert list(res.df.columns) == ["", "s1", "s2", "s3"]
    assert any("ragged" in c.lower() for c in res.change_log)
    assert Outcome.RESOLVED in outcomes(res)
    assert res.df.iloc[1].tolist() == ["B", "4", "5", "6"]


def test_empty_file_blocked(tmp_path):
    res = parse_matrix(put(tmp_path, "e.tsv", b""))
    assert res.df is None
    assert outcomes(res) == [Outcome.BLOCKED]


def test_whitespace_only_blocked(tmp_path):
    res = parse_matrix(put(tmp_path, "w.tsv", b"\n \n\n"))
    assert outcomes(res) == [Outcome.BLOCKED]


def test_binary_junk_blocked(tmp_path):
    res = parse_matrix(put(tmp_path, "j.bin", bytes([0, 159, 146, 150, 255, 0, 1, 2, 254]) * 20))
    assert res.df is None
    assert outcomes(res) == [Outcome.BLOCKED]


@pytest.mark.parametrize(
    "data",
    [
        b"\x01\tA\n\x02\t1\n",  # valid UTF-8 control chars, no NUL
        b"g\ts1\nA\t1\x1b\n",  # ESC inside a cell
        b"g\ts1\nA\t1\x7f\n",  # DEL
        "g\ts1\nA\t1\u0085\n".encode("utf-8"),  # C1 control (NEL)
    ],
)
def test_control_characters_blocked(tmp_path, data):
    res = parse_matrix(put(tmp_path, "c.tsv", data))
    assert res.df is None
    assert outcomes(res) == [Outcome.BLOCKED]


def test_legitimate_whitespace_and_text_preserved(tmp_path):
    p = put(tmp_path, "t.tsv", "gene\ts1\r\nA \u00e9\t1\r\n\r\nB\t2\n")
    res = parse_matrix(p)
    assert_ok(res)
    assert res.df.values.tolist() == [["A \u00e9", "1"], ["B", "2"]]


def test_unclosed_quote_tab_not_assessable(tmp_path):
    res = parse_matrix(put(tmp_path, "q.tsv", 'gene\ts1\n"A\t1\nB\t2\n'))
    assert res.df is None
    assert outcomes(res) == [Outcome.NOT_ASSESSABLE]
    assert "quot" in res.records[0].decision_basis
    assert "tab" in res.records[0].evidence["delimiters_with_quote_errors"]


def test_unclosed_quote_comma_not_assessable(tmp_path):
    res = parse_matrix(put(tmp_path, "q.csv", 'gene,s1\n"A,1\nB,2\n'))
    assert res.df is None
    assert outcomes(res) == [Outcome.NOT_ASSESSABLE]
    assert "quot" in res.records[0].decision_basis
    assert "comma" in res.records[0].evidence["delimiters_with_quote_errors"]


@pytest.mark.parametrize("sep", ["\t", ",", ";"])
def test_header_only_blocked(tmp_path, sep):
    res = parse_matrix(put(tmp_path, "h.txt", sep.join(["gene", "s1", "s2"]) + "\n"))
    assert res.df is None
    assert outcomes(res) == [Outcome.BLOCKED]
    assert res.records[0].decision_basis == "file has a header but no data rows"


def test_missing_file_blocked(tmp_path):
    res = parse_matrix(tmp_path / "nope.tsv")
    assert res.df is None
    assert outcomes(res) == [Outcome.BLOCKED]


def test_ambiguous_delimiter_not_assessable(tmp_path):
    res = parse_matrix(put(tmp_path, "a.txt", "a,b\tc\n1,2\t3\n"))
    assert res.df is None
    assert outcomes(res) == [Outcome.NOT_ASSESSABLE]


def test_unequal_rows_not_assessable(tmp_path):
    res = parse_matrix(put(tmp_path, "u.tsv", "g\ts1\ts2\nA\t1\t2\nB\t3\nC\t4\t5\t6\n"))
    assert res.df is None
    assert outcomes(res) == [Outcome.NOT_ASSESSABLE]


def test_no_delimiter_not_assessable(tmp_path):
    res = parse_matrix(put(tmp_path, "n.txt", "abc\ndef\n"))
    assert res.df is None
    assert outcomes(res) == [Outcome.NOT_ASSESSABLE]


def test_values_identical_as_strings(tmp_path):
    cells = [["A", "1.50", "007", "1e3"], ["B", "-0.0", "NA", ""], ["C", "0.10", "  5", "12345678901234567890"]]
    text = "gene\ts1\ts2\ts3\n" + "\n".join("\t".join(r) for r in cells) + "\n"
    p = put(tmp_path, "v.tsv", text)
    res = parse_matrix(p)
    assert_ok(res)
    assert res.df.values.tolist() == cells


def test_input_untouched_and_out_path(tmp_path):
    p = put(tmp_path, "i.csv", b"\xef\xbb\xbf\"gene\",\"s1\"\r\n\"A\",\"1.50\"\r\n")
    before = sha256_file(p)
    out = tmp_path / "derived" / "i.norm.tsv"
    res = parse_matrix(p, out_path=out)
    assert_ok(res)
    assert sha256_file(p) == before
    assert out.exists()
    again = parse_matrix(out)
    assert_ok(again)
    assert again.df.values.tolist() == res.df.values.tolist() == [["A", "1.50"]]
    assert list(again.df.columns) == list(res.df.columns)


def test_no_derived_file_without_out_path(tmp_path):
    p = put(tmp_path, "i.tsv", "g\ts1\nA\t1\n")
    parse_matrix(p)
    assert sorted(x.name for x in tmp_path.iterdir()) == ["i.tsv"]


def test_out_path_not_written_on_failure(tmp_path):
    p = put(tmp_path, "e.tsv", b"")
    out = tmp_path / "o.tsv"
    parse_matrix(p, out_path=out)
    assert not out.exists()


def test_out_path_equal_to_input_rejected(tmp_path):
    p = put(tmp_path, "i.tsv", "g\ts1\nA\t1\n")
    before = sha256_file(p)
    with pytest.raises(ValueError):
        parse_matrix(p, out_path=p)
    assert sha256_file(p) == before


# ----------------------------------------------------------------- T1.3b
# D-T1.3-1: when one delimiter candidate fails on quoting and another candidate
# is only "plausible" because it reads a quote character as literal text, the
# plausible one must not be chosen silently.
def test_quote_error_with_plausible_other_delimiter_not_assessable(tmp_path):
    p = put(tmp_path, "d.txt", 'g\th,i\nx\t"A,1\ny\t3,4\n')
    res = parse_matrix(p)
    assert res.df is None
    assert outcomes(res) == [Outcome.NOT_ASSESSABLE]
    ev = res.records[0].evidence
    assert "tab" in ev["delimiters_with_quote_errors"]
    assert ev["plausible_delimiters"] == ["comma"]
    for r in res.records:
        json.dumps(r.to_dict())


def test_quote_error_mirror_case_comma_error_tab_plausible(tmp_path):
    p = put(tmp_path, "d.txt", 'g,h\ti\nx,"A\t1\ny,3\t4\n')
    res = parse_matrix(p)
    assert res.df is None
    assert outcomes(res) == [Outcome.NOT_ASSESSABLE]
    assert "comma" in res.records[0].evidence["delimiters_with_quote_errors"]
    assert res.records[0].evidence["plausible_delimiters"] == ["tab"]


def test_not_assessable_quote_case_writes_no_derived_file(tmp_path):
    p = put(tmp_path, "d.txt", 'g\th,i\nx\t"A,1\ny\t3,4\n')
    out = tmp_path / "o.tsv"
    parse_matrix(p, out_path=out)
    assert not out.exists()


def test_legitimate_quoted_comma_file_still_passes_despite_tab_quote_error(tmp_path):
    # Under the tab candidate the quoted first column raises a quote error, but
    # every quote is explained by the comma reading: this must still parse.
    p = put(tmp_path, "q.csv", '"gene,x",s1,s2\n"A,1",1,2\n"B,2",3,4\n')
    res = parse_matrix(p)
    assert_ok(res)
    assert list(res.df.columns) == ["gene,x", "s1", "s2"]
    assert res.df.iloc[0].tolist() == ["A,1", "1", "2"]


def test_escaped_quotes_inside_quoted_field_still_pass(tmp_path):
    p = put(tmp_path, "e.csv", '"g","s1"\n"a ""b""",1\n')
    res = parse_matrix(p)
    assert_ok(res)
    assert res.df.iloc[0].tolist() == ['a "b"', "1"]


def test_literal_quote_without_any_candidate_error_unchanged(tmp_path):
    # No candidate fails on quoting, so there is no disagreement to report.
    p = put(tmp_path, "l.csv", 'g,h\n5" pipe,1\n')
    res = parse_matrix(p)
    assert_ok(res)
    assert res.df.iloc[0].tolist() == ['5" pipe', "1"]


# first-column-as-index helper (data-flow gap between parse_matrix and G-03/R-01)
def test_first_column_as_index_basic(tmp_path):
    from bionexus.fileio import first_column_as_index

    res = parse_matrix(put(tmp_path, "m.tsv", "gene\ts1\ts2\nA\t1\t2\nB\t3\t4\n"))
    out = first_column_as_index(res.df)
    assert list(out.index) == ["A", "B"]
    assert out.index.name == "gene"
    assert list(out.columns) == ["s1", "s2"]
    assert out.values.tolist() == [["1", "2"], ["3", "4"]]
    assert all(dt == object for dt in out.dtypes)


def test_first_column_as_index_does_not_mutate_input_or_alias(tmp_path):
    from bionexus.fileio import first_column_as_index

    res = parse_matrix(put(tmp_path, "m.tsv", "gene\ts1\nA\t1\nB\t2\n"))
    before = res.df.copy(deep=True)
    out = first_column_as_index(res.df)
    assert res.df.equals(before) and list(res.df.columns) == ["gene", "s1"]
    out.iloc[0, 0] = "changed"
    assert res.df.iloc[0, 1] == "1"


def test_first_column_as_index_keeps_exact_strings_and_duplicates(tmp_path):
    from bionexus.fileio import first_column_as_index

    text = "gene\ts1\ts1\nA\t9007199254740993\t1.50\nA\t0010\t-0\n"
    res = parse_matrix(put(tmp_path, "m.tsv", text))
    out = first_column_as_index(res.df)
    assert list(out.index) == ["A", "A"]  # duplicates preserved, not resolved
    assert out.values.tolist() == [["9007199254740993", "1.50"], ["0010", "-0"]]
    assert list(out.columns) == ["s1", "s1"]


def test_first_column_as_index_ragged_header_empty_label(tmp_path):
    from bionexus.fileio import first_column_as_index

    res = parse_matrix(put(tmp_path, "r.tsv", "s1\ts2\nA\t1\t2\n"))
    out = first_column_as_index(res.df)
    assert list(out.index) == ["A"]
    assert list(out.columns) == ["s1", "s2"]


def test_first_column_as_index_needs_two_columns():
    import pandas as pd
    from bionexus.fileio import first_column_as_index

    with pytest.raises(ValueError):
        first_column_as_index(pd.DataFrame({"only": ["a"]}, dtype=object))
