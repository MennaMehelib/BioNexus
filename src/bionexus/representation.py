"""Representation evidence (R-01, R-02, R-05, R-06).

Computes plain structural facts about a genes x samples matrix and emits
assessment records. No value is changed, rounded, imputed or normalized, and
the input DataFrame is only read.

Input contract: the frame may be numeric or the all-string (dtype=object)
frame produced by T1.3 ``parse_matrix``. A cell is *missing* if it is None,
NaN, pandas NA, or the empty string (what T1.3 yields for an empty cell). Any
other cell must be an exact finite number: strings are parsed with ``Decimal``
and held as exact ``Fraction`` values, so large integers (e.g. 2**53 + 1) are
never rounded through float64. A cell that is not a finite number (``"NA"``,
gene symbols, ``"inf"``, booleans, ...) is never reinterpreted: the result is a
``not_assessable`` record and no numeric facts are reported.

Reported numbers (minimum, column sums and their min/max) are compared and summed
exactly; they are int when integral, float when non-integral and the float is
lossless, and otherwise an exact decimal string. Nothing is rounded.

R-03 (constant-sum inference) is CONDITIONAL and disabled; it is deliberately
not implemented here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from fractions import Fraction

import numpy as np
import pandas as pd

from .records import AssessmentRecord, Outcome

_VERSION = "0.1"
_MISSING = object()

# Resource-safety bound, not a biological threshold: a cell is assessed only if
# the exact positional expansion of its value (digits left of the decimal point
# plus digits right of it) is at most this many digits. Real expression values are
# many orders of magnitude inside it (float64 spans about 308 digits). Beyond it,
# exact arithmetic could hang (e.g. 1e100000000) or hit Python's 4300-digit
# int-to-string limit when the value is reported, so the cell is not assessed.
_MAX_POSITIONAL_DIGITS = 4000


# Smallest bit length that certainly exceeds the digit bound: 2**13300 has more
# than 4003 decimal digits. Used so huge ints are rejected without converting them
# to a string (which Python itself refuses beyond 4300 digits).
_INT_BITS_CERTAINLY_OVER = 13300


class _NonNumeric(Exception):
    pass


class _OutOfRange(_NonNumeric):
    """A finite numeric-looking cell whose exact expansion exceeds the bound."""


def _classify(x):
    """Return _MISSING, or an exact Fraction. Raise _NonNumeric otherwise."""
    if x is None or x is pd.NA:
        return _MISSING
    if isinstance(x, (bool, np.bool_)):
        raise _NonNumeric
    if isinstance(x, str):
        if x == "":
            return _MISSING
        if "_" in x:  # Decimal would accept digit-group underscores
            raise _NonNumeric
        try:
            d = Decimal(x.strip())
        except InvalidOperation:
            raise _NonNumeric from None
        if not d.is_finite():
            raise _NonNumeric
        left = max(0, d.adjusted() + 1)
        right = max(0, -d.as_tuple().exponent)
        if left + right > _MAX_POSITIONAL_DIGITS:
            raise _OutOfRange
        return Fraction(d)
    if isinstance(x, (int, np.integer)):
        n = abs(int(x))
        if n.bit_length() > _INT_BITS_CERTAINLY_OVER or len(str(n)) > _MAX_POSITIONAL_DIGITS:
            raise _OutOfRange
        return Fraction(int(x))
    if isinstance(x, (float, np.floating)):
        if math.isnan(x):
            return _MISSING
        if math.isinf(x):
            raise _NonNumeric
        return Fraction(float(x))
    raise _NonNumeric


def _cell_text(x):
    """str(x) for evidence, except that a huge int is described, not converted
    (Python refuses int-to-str beyond 4300 digits)."""
    if isinstance(x, (int, np.integer)) and not isinstance(x, (bool, np.bool_)):
        bits = abs(int(x)).bit_length()
        if bits > _INT_BITS_CERTAINLY_OVER:
            return f"<integer of {bits} bits, not shown>"
    return str(x)


def _exact_decimal_string(fr):
    """Exact decimal expansion of a non-integral Fraction (denominator is 2^a*5^b)."""
    k = 0
    while 10**k % fr.denominator:
        k += 1
        if k > 4096:  # cannot happen for Decimal/float-derived values
            raise ValueError("value has no finite decimal expansion")
    scaled = fr.numerator * (10**k // fr.denominator)
    sign = "-" if scaled < 0 else ""
    whole, frac = divmod(abs(scaled), 10**k)
    return f"{sign}{whole}.{str(frac).zfill(k).rstrip('0')}"


def _plain(fr):
    """Exact Fraction -> reportable value, never rounded.

    Integral -> int. Non-integral -> float when the float is lossless, i.e. it
    equals the exact value or its shortest repr (the JSON text) is exactly the
    decimal value; otherwise the exact decimal string.
    """
    if fr.denominator == 1:
        return int(fr)
    f = float(fr)
    if math.isfinite(f) and (
        Fraction(f) == fr or Fraction(Decimal(repr(f))) == fr
    ):
        return f
    return _exact_decimal_string(fr)


@dataclass(frozen=True)
class RepresentationEvidence:
    # minimum / col_sums / col_sum_min / col_sum_max: int when integral; float when
    # non-integral and lossless; otherwise an exact decimal string (never rounded).
    all_integer_valued: bool
    any_negative: bool
    any_na: bool
    n_na_genes: int
    na_genes: list
    minimum: int | float | str | None
    zero_fraction: float | None
    col_sums: list
    col_sum_min: int | float | str | None
    col_sum_max: int | float | str | None
    r1_candidate: bool
    declared: str | None
    annotation_fraction: float | None
    records: list = field(default_factory=list)

    def to_dict(self) -> dict:
        """Strict-JSON-compatible: unavailable facts are None, never NaN/Inf."""
        return {
            "all_integer_valued": self.all_integer_valued,
            "any_negative": self.any_negative,
            "any_na": self.any_na,
            "n_na_genes": self.n_na_genes,
            "na_genes": list(self.na_genes),
            "minimum": self.minimum,
            "zero_fraction": self.zero_fraction,
            "col_sums": list(self.col_sums),
            "col_sum_min": self.col_sum_min,
            "col_sum_max": self.col_sum_max,
            "r1_candidate": self.r1_candidate,
            "declared": self.declared,
            "annotation_fraction": self.annotation_fraction,
            "records": [r.to_dict() for r in self.records],
        }


def _rec(rule_id, check_id, scope, outcome, basis, evidence):
    return AssessmentRecord(
        check_id=check_id,
        rule_id=rule_id,
        rule_version=_VERSION,
        scope=scope,
        outcome=outcome,
        evidence=evidence,
        confidence=None,
        limitations=(),
        decision_basis=basis,
    )


def evidence_record(
    df: pd.DataFrame,
    declared: str | None = None,
    *,
    annotation_genes=None,
    scope: str = "matrix",
) -> RepresentationEvidence:
    n_rows, n_cols = df.shape
    cells = df.to_numpy(dtype=object)  # read-only use; df is never written

    parsed = [[None] * n_cols for _ in range(n_rows)]
    bad = []
    for r in range(n_rows):
        for c in range(n_cols):
            try:
                parsed[r][c] = _classify(cells[r][c])
            except _NonNumeric as exc:
                item = {"gene": str(df.index[r]), "sample": str(df.columns[c]),
                        "value": _cell_text(cells[r][c])}
                if isinstance(exc, _OutOfRange):
                    item["reason"] = "outside supported exact range"
                bad.append(item)

    records: list[AssessmentRecord] = []
    declared_out = declared

    def result(**facts):
        base = dict(
            all_integer_valued=False, any_negative=False, any_na=False,
            n_na_genes=0, na_genes=[], minimum=None, zero_fraction=None,
            col_sums=[None] * n_cols, col_sum_min=None, col_sum_max=None,
            r1_candidate=False, declared=declared_out, annotation_fraction=None,
        )
        base.update(facts)
        return RepresentationEvidence(records=records, **base)

    def add_annotation():
        """R-05 needs only the gene labels, so it runs on every path."""
        if annotation_genes is None:
            return None
        ann = {str(g) for g in annotation_genes}
        if not ann:
            records.append(_rec("R-05", "R-05.annotation", scope, Outcome.NOTE,
                                "annotation gene list is empty; coverage fraction "
                                "is undefined", {"annotation_genes": 0}))
            return None
        n_present = len(ann & {str(g) for g in df.index})
        absent = len(ann) - n_present
        ann_fraction = n_present / len(ann)
        if absent:
            records.append(_rec(
                "R-05", "R-05.annotation", scope, Outcome.LIMITATION,
                f"{n_present} of {len(ann)} annotation genes are present in the "
                f"matrix; {absent} are absent. Any later per-sample total over "
                "this matrix covers only the genes present",
                {"annotation_genes": len(ann), "present": n_present,
                 "absent": absent, "fraction_present": ann_fraction},
            ))
        return ann_fraction

    # R-06: a sample (column) with no value at all -> fact request. Established
    # from missingness alone, so it holds even when non-numeric cells exist (a
    # column containing a non-numeric cell is never "all missing").
    whole_sample_na = [
        str(df.columns[c]) for c in range(n_cols)
        if n_rows > 0 and all(parsed[r][c] is _MISSING for r in range(n_rows))
    ]

    def add_whole_sample_na():
        if whole_sample_na:
            records.append(_rec(
                "R-06", "R-06.whole_sample_na", scope, Outcome.NEED_FACT,
                f"{len(whole_sample_na)} sample(s) have no value at all (whole-sample "
                "missing); the sample's status must be supplied; nothing imputed",
                {"whole_sample_na": whole_sample_na,
                 "n_whole_sample_na": len(whole_sample_na)},
            ))

    if bad:
        n_out_of_range = sum(1 for b in bad if "reason" in b)
        records.append(_rec(
            "R-01", "R-01.non_numeric", scope, Outcome.NOT_ASSESSABLE,
            f"{len(bad)} cell(s) are not finite numbers within the supported exact "
            f"range ({n_out_of_range} of them numeric-looking but outside it); "
            "representation cannot be assessed and no cell was reinterpreted",
            {"n_non_numeric_cells": len(bad), "examples": bad[:5],
             "n_out_of_supported_range": n_out_of_range},
        ))
        add_whole_sample_na()
        # Gene-level missingness (R-06 NOTE) must still be reported even when
        # non-numeric cells block numeric representation assessment.
        na_genes = [str(df.index[r]) for r in range(n_rows)
                    if any(v is _MISSING for v in parsed[r])]
        any_na = bool(na_genes)
        if any_na:
            records.append(_rec(
                "R-06", "R-06.na_genes", scope, Outcome.NOTE,
                f"{len(na_genes)} gene(s) have at least one missing value; listed as the "
                "genes excluded from the complete-case set; nothing imputed",
                {"na_genes": na_genes, "n_na_genes": len(na_genes)},
            ))
        return result(any_na=any_na, n_na_genes=len(na_genes), na_genes=na_genes,
                      annotation_fraction=add_annotation())

    na_genes = [str(df.index[r]) for r in range(n_rows)
                if any(v is _MISSING for v in parsed[r])]
    any_na = bool(na_genes)
    if any_na:
        records.append(_rec(
            "R-06", "R-06.na_genes", scope, Outcome.NOTE,
            f"{len(na_genes)} gene(s) have at least one missing value; listed as the "
            "genes excluded from the complete-case set; nothing imputed",
            {"na_genes": na_genes, "n_na_genes": len(na_genes)},
        ))

    values = [v for row in parsed for v in row if v is not _MISSING]
    na_facts = dict(any_na=any_na, n_na_genes=len(na_genes), na_genes=na_genes)

    add_whole_sample_na()

    if not values:
        records.append(_rec(
            "R-01", "R-01.no_values", scope, Outcome.NOT_ASSESSABLE,
            "matrix has no non-missing values; representation cannot be assessed",
            {"n_rows": n_rows, "n_columns": n_cols},
        ))
        return result(**na_facts, annotation_fraction=add_annotation())

    all_int = all(v.denominator == 1 for v in values)
    any_neg = any(v < 0 for v in values)
    r1 = all_int and not any_neg
    exact_sums = []
    for c in range(n_cols):
        col = [parsed[r][c] for r in range(n_rows) if parsed[r][c] is not _MISSING]
        exact_sums.append(sum(col, Fraction(0)) if col else None)
    present = [s for s in exact_sums if s is not None]  # compared exactly

    facts = dict(
        na_facts,
        all_integer_valued=all_int,
        any_negative=any_neg,
        minimum=_plain(min(values)),
        zero_fraction=sum(1 for v in values if v == 0) / len(values),
        col_sums=[None if s is None else _plain(s) for s in exact_sums],
        col_sum_min=_plain(min(present)),
        col_sum_max=_plain(max(present)),
        r1_candidate=r1,
    )
    ev = {"all_integer_valued": all_int, "any_negative": any_neg}

    if declared is None:
        if r1:
            records.append(_rec("R-01", "R-01.candidate", scope, Outcome.PASS,
                                "all non-missing values are non-negative integers: "
                                "R1 candidate", ev))
        else:
            why = ("values are not all integer-valued" if not all_int
                   else "negative values are present")
            records.append(_rec("R-02", "R-02.undeclared", scope, Outcome.NEED_FACT,
                                f"{why} and no representation was declared; "
                                "documentation is needed", ev))
    elif declared == "R1":
        if not all_int:
            records.append(_rec("R-01", "R-01.declared_r1", scope, Outcome.BLOCKED,
                                "declared R1 but values are not all integer-valued",
                                dict(ev, declared=declared)))
        elif any_neg:
            records.append(_rec("R-01", "R-01.declared_r1", scope, Outcome.BLOCKED,
                                "declared R1 but negative values are present",
                                dict(ev, declared=declared)))
        else:
            records.append(_rec("R-01", "R-01.declared_r1", scope, Outcome.PASS,
                                "declared R1 is consistent with the structural facts",
                                dict(ev, declared=declared)))
    elif declared == "linear":
        if any_neg:
            records.append(_rec("R-02", "R-02.declared_linear", scope, Outcome.NEED_FACT,
                                "declared linear but negative values are present",
                                dict(ev, declared=declared)))
        else:
            records.append(_rec("R-02", "R-02.declared_linear", scope, Outcome.PASS,
                                "declared linear shows no contradiction in the "
                                "structural facts", dict(ev, declared=declared)))
    else:
        records.append(_rec("R-02", "R-02.declared", scope, Outcome.NOTE,
                            f"declared representation {declared!r} recorded; no "
                            "consistency check is defined for it",
                            dict(ev, declared=declared)))

    ann_fraction = add_annotation()

    return result(**facts, annotation_fraction=ann_fraction)
