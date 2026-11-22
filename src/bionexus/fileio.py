"""Parse and structural validation (G-02).

Every cell is kept as the exact source string; no value is converted, rounded,
imputed or otherwise changed here. Numeric interpretation belongs to later steps.
Only UTF-8 text (with or without BOM) is supported; other encodings are blocked.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .records import AssessmentRecord, Outcome

RULE_ID = "G-02"
RULE_VERSION = "0.1"
_CANDIDATES = (("tab", "\t"), ("comma", ","), ("semicolon", ";"))
_BOM = "\ufeff"
# Unicode category Cc (U+0000-001F, U+007F-009F) except tab, LF, CR. The BOM is
# category Cf, so it is not matched.
_CONTROL_CHARS = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


@dataclass
class ParseResult:
    df: pd.DataFrame | None
    change_log: list = field(default_factory=list)
    records: list = field(default_factory=list)


def _record(path, outcome, basis, evidence=None, check_id="G-02.parse"):
    return AssessmentRecord(
        check_id=check_id,
        rule_id=RULE_ID,
        rule_version=RULE_VERSION,
        scope=str(path),
        outcome=outcome,
        evidence=evidence or {},
        confidence=None,
        limitations=(),
        decision_basis=basis,
    )


def _fail(path, outcome, basis, evidence=None):
    return ParseResult(None, [], [_record(path, outcome, basis, evidence)])


def _split(text, sep):
    rows = list(csv.reader(io.StringIO(text, newline=""), delimiter=sep, quotechar='"', strict=True))
    return [r for r in rows if r]  # blank lines carry no data


def _has_unexplained_quote(text, sep):
    """True if a quote character appears inside an unquoted field under ``sep``.

    A quote is "explained" when it opens a quoted field, closes one, or is an
    escaped pair inside one. A quote in the middle of an unquoted field is read
    as literal text by the csv module, so it never fails; it is only reported
    here, to detect disagreement between delimiter candidates (D-T1.3-1).
    """
    state = "start"
    for ch in text:
        end = ch == sep or ch in "\r\n"
        if state == "start":
            if ch == '"':
                state = "quoted"
            elif not end:
                state = "unquoted"
        elif state == "unquoted":
            if end:
                state = "start"
            elif ch == '"':
                return True
        elif state == "quoted":
            if ch == '"':
                state = "after_quote"
        else:  # after_quote
            if ch == '"':
                state = "quoted"  # escaped quote
            elif end:
                state = "start"
            else:
                return True  # text after a closing quote
    return False


def _structure(rows):
    """Return 'ok' (equal widths), 'ragged' (header one label short) or None."""
    if not rows:
        return None
    header_n = len(rows[0])
    body = {len(r) for r in rows[1:]}
    if not body:
        return "ok" if header_n >= 2 else None
    if len(body) != 1:
        return None
    n = body.pop()
    if n < 2:
        return None
    if header_n == n:
        return "ok"
    if header_n == n - 1:
        return "ragged"
    return None


def parse_matrix(path, out_path=None) -> ParseResult:
    path = Path(path)
    if out_path is not None:
        out_path = Path(out_path)
        if out_path.resolve() == path.resolve():
            raise ValueError("out_path must differ from the input path")

    try:
        data = path.read_bytes()
    except OSError as exc:
        return _fail(path, Outcome.BLOCKED, "input file unreadable",
                     {"error": f"{type(exc).__name__}: {exc}"})
    if not data.strip():
        return _fail(path, Outcome.BLOCKED, "file is empty")
    if b"\x00" in data:
        return _fail(path, Outcome.BLOCKED, "file contains NUL bytes: not a text matrix")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        return _fail(path, Outcome.BLOCKED, "file is not valid UTF-8 text",
                     {"error": str(exc)})

    bad = _CONTROL_CHARS.search(text)
    if bad:
        return _fail(path, Outcome.BLOCKED,
                     "file contains control characters: not a text matrix",
                     {"first_control_character": f"U+{ord(bad.group()):04X}",
                      "offset": bad.start()})

    change_log: list[str] = []
    if text.startswith(_BOM):
        text = text[1:]
        change_log.append("removed UTF-8 BOM")

    parsed = {}
    quote_errors = {}
    for name, sep in _CANDIDATES:
        try:
            rows = _split(text, sep)
        except csv.Error as exc:
            # malformed quoting under this delimiter: candidate is not plausible
            quote_errors[name] = str(exc)
            continue
        parsed[name] = (sep, rows, _structure(rows))
    plausible = [n for n, (_, _, s) in parsed.items() if s is not None]

    if len(plausible) > 1:
        return _fail(path, Outcome.NOT_ASSESSABLE,
                     "ambiguous delimiter: more than one is equally plausible; no guess made",
                     {"plausible_delimiters": plausible})
    if len(plausible) == 1 and quote_errors:
        # Another delimiter failed on quoting. That is harmless when every quote
        # is explained by the plausible reading; otherwise the two readings
        # disagree about what a quote means and no guess is made.
        sep = parsed[plausible[0]][0]
        if _has_unexplained_quote(text, sep):
            return _fail(path, Outcome.NOT_ASSESSABLE,
                         "quote handling disagrees between delimiter candidates: "
                         "one candidate fails on quoting and the other reads a quote "
                         "as literal text; no guess made",
                         {"delimiters_with_quote_errors": quote_errors,
                          "plausible_delimiters": plausible})
    if not plausible:
        splitting = [n for n, (_, rows, _) in parsed.items()
                     if any(len(r) > 1 for r in rows)]
        if quote_errors and not splitting:
            return _fail(path, Outcome.NOT_ASSESSABLE,
                         "malformed or unclosed quoting: no delimiter candidate "
                         "could be parsed; no guess made",
                         {"delimiters_with_quote_errors": quote_errors})
        if splitting:
            return _fail(path, Outcome.NOT_ASSESSABLE,
                         "rows of unequal length not explained by a one-label-short header",
                         {"delimiters_that_split_rows": splitting})
        return _fail(path, Outcome.NOT_ASSESSABLE,
                     "no tab, comma or semicolon delimiter found in the content")

    name = plausible[0]
    sep, rows, structure = parsed[name]
    if len(rows) < 2:
        return _fail(path, Outcome.BLOCKED, "file has a header but no data rows",
                     {"delimiter": name, "header_labels": len(rows[0])})
    change_log.append(f"detected {name} delimiter")
    if '"' in text:
        change_log.append("removed surrounding quotes via quote-aware parsing")

    header, body = rows[0], rows[1:]
    records = []
    if structure == "ragged":
        header = [""] + header
        change_log.append(
            "ragged header: header had one fewer label than data columns; "
            "added an empty label for the first column"
        )
        records.append(_record(
            path, Outcome.RESOLVED,
            "header one label short of data columns; empty first label added",
            {"header_labels": len(header) - 1, "data_columns": len(header)},
            check_id="G-02.ragged_header",
        ))

    df = pd.DataFrame(body, columns=header, dtype=object)
    records.insert(0, _record(
        path, Outcome.PASS, "file parsed structurally",
        {"delimiter": name, "n_rows": len(body), "n_columns": len(header)},
    ))

    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter="\t", lineterminator="\n")
            w.writerow(header)
            w.writerows(body)
        change_log.append(f"wrote normalized tab-delimited copy to {out_path}")

    return ParseResult(df, change_log, records)


def first_column_as_index(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of a parsed matrix with its first column as the row labels.

    ``parse_matrix`` keeps the identifier column as ordinary data. Orientation
    and representation steps need the identifiers as the index, so this helper
    moves the first column into the index without changing any cell: values stay
    exact strings, duplicate labels are preserved (never resolved here), and the
    input frame is not modified.
    """
    if df.shape[1] < 2:
        raise ValueError("matrix needs an identifier column and at least one data column")
    labels = pd.Index(df.iloc[:, 0].tolist(), dtype=object, name=df.columns[0])
    out = df.iloc[:, 1:].copy(deep=True)
    out.index = labels
    return out
