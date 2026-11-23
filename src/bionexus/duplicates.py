"""T1.7 duplicate detection (M-04). Non-destructive: findings only.

A duplicate is a repeated identifier: a sample ID (column label) or a gene ID
(row label) that occurs more than once. Identifiers are text and are compared
exactly: case-sensitive, whitespace included, never normalized. A label that is not
a string is never converted to text (``5`` and ``"5"`` are different things); that
axis is reported as ``not_assessable`` instead.

The cell values decide whether the repeats are identical (recorded with a note) or
conflicting (``need_fact``). Cells are compared as parsed tokens, exactly, in order
and with the same length. This is parsed-token equality, not equality of file
bytes (file integrity is a separate check). Text tokens such as ``"NA"``,
``"NaN"``, ``"null"``, ``"."`` and ``""`` stay text. For typed (non-string) cells,
values of different kinds (bool, integer, floating, other types) are never equal,
even if Python would compare them equal (``1`` and ``1.0``). Non-string missing
sentinels (None, NaN, ``pd.NA``, ``pd.NaT``, NumPy NaT) form ONE missing class that
equals only itself.

No row or column is ever dropped, merged or changed, and identical values under
different identifiers are not duplicates.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .records import AssessmentRecord, Outcome

_VERSION = "0.1"


def _rec(check_id, scope, outcome, basis, evidence):
    return AssessmentRecord(
        check_id=check_id,
        rule_id="M-04",
        rule_version=_VERSION,
        scope=scope,
        outcome=outcome,
        evidence=evidence,
        confidence=None,
        limitations=(),
        decision_basis=basis,
    )


def _missing(value) -> bool:
    """Non-string missing sentinels: None, pd.NA, pd.NaT, NaN, NumPy NaT.

    Strings are never missing here: ``"NA"``, ``"NaN"`` and ``""`` are text.
    """
    if value is None or value is pd.NA or value is pd.NaT:
        return True
    if isinstance(value, (np.datetime64, np.timedelta64)):
        return bool(np.isnat(value))
    return isinstance(value, (float, np.floating)) and value != value


def _kind(value):
    """Value kind used to forbid cross-kind equality (bool is not an integer)."""
    if isinstance(value, str):
        return "text"
    if isinstance(value, (bool, np.bool_)):
        return "bool"
    if isinstance(value, (int, np.integer)):
        return "integer"
    if isinstance(value, (float, np.floating)):
        return "floating"
    return type(value)


def _same(a, b) -> bool:
    """Exact cell equality for parsed tokens and typed cells.

    All non-string missing sentinels are one class that equals only itself. Cells of
    different kinds never compare equal; cells of the same kind compare with ``==``.
    """
    am, bm = _missing(a), _missing(b)
    if am or bm:
        return am and bm
    if _kind(a) != _kind(b):
        return False
    try:
        return bool(a == b)
    except Exception:
        return False


def _groups(labels):
    seen: dict[str, list[int]] = {}
    for i, label in enumerate(labels):
        seen.setdefault(label, []).append(i)
    return {k: v for k, v in seen.items() if len(v) > 1}


def _scan(df, axis, scope):
    labels = list(df.columns if axis == "columns" else df.index)
    out = []
    noun, unit = (("sample", "column") if axis == "columns" else ("gene", "row"))
    check_id = "M-04.duplicate_samples" if axis == "columns" else "M-04.duplicate_genes"
    bad = [i for i, x in enumerate(labels) if not isinstance(x, str)]
    if bad:
        # A non-string label is never turned into text: 5 and "5" are not the same ID.
        return [_rec(
            f"M-04.invalid_{noun}_labels", scope, Outcome.NOT_ASSESSABLE,
            f"{len(bad)} {noun} label(s) are not text; identifiers are compared "
            "exactly and are never converted to text, so duplicates on this axis "
            "were not assessed",
            {"axis": axis, "positions": bad,
             "types": sorted({type(labels[i]).__name__ for i in bad}),
             "consequence": f"No duplicate check was made on the {noun} labels; they "
                            "must be supplied as text."})]
    for label, positions in _groups(labels).items():
        if axis == "columns":
            vectors = [df.iloc[:, p].tolist() for p in positions]
        else:
            vectors = [df.iloc[p, :].tolist() for p in positions]
        first = vectors[0]
        differing = sum(
            1 for i in range(len(first))
            if not all(_same(first[i], v[i]) for v in vectors[1:])
        )
        identical = differing == 0
        ev = {"label": label, "positions": positions, "identical": identical,
              "n_differing_cells": differing, "kind": unit}
        if identical:
            out.append(_rec(
                check_id, scope, Outcome.NOTE,
                f"duplicate {noun} ID '{label}' in {len(positions)} {unit}s with "
                f"identical values; recorded only, all {len(positions)} {unit}s are "
                "retained pending an explicit decision", ev))
        else:
            out.append(_rec(
                check_id, scope, Outcome.NEED_FACT,
                f"duplicate {noun} ID '{label}' in {len(positions)} {unit}s with "
                f"different values ({differing} differing cell(s)); no {unit} was "
                "removed", dict(ev, consequence=(
                    f"It is not known which {unit} is correct; the {noun} stays "
                    "unresolved until this is answered."))))
    return out


def find_duplicates(df: pd.DataFrame, scope: str = "matrix") -> list[AssessmentRecord]:
    """Report duplicate sample columns and duplicate gene rows (M-04).

    Expects genes as the row index and samples as the columns. ``df`` is never
    modified.
    """
    records = _scan(df, "columns", scope) + _scan(df, "index", scope)
    if not records:
        records.append(_rec(
            "M-04.none", scope, Outcome.PASS,
            "no duplicate sample IDs or gene IDs",
            {"n_columns": int(df.shape[1]), "n_rows": int(df.shape[0])},
        ))
    return records
