"""Orientation (G-03): output convention is rows = genes, columns = samples.

The matrix is transposed only when every available, independent structural
signal agrees. All signals are boolean comparisons; there are no numeric
thresholds and no built-in identifier patterns (patterns are supplied by the
caller as data). Values are never changed: a transpose only swaps the axes.

Signals (each votes "as_is", "transpose", or is "ambiguous"/unavailable):
  labels   - caller-supplied regex patterns (full match) for gene-like and/or
             sample-like identifiers. An axis is gene-like (sample-like) if
             EVERY label matches a gene (sample) pattern.
  metadata - exact membership of axis labels in the metadata sample IDs. An
             axis "matches" if ANY of its labels is a metadata ID.
  length   - rows longer than columns votes as_is; shorter votes transpose;
             equal (square) is never resolved.

Conservative addition (documented assumption, not a scientific cut-off):
  * a signal that is available but ambiguous blocks any decision (need_fact).
A single available, unambiguous signal is sufficient to decide.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from .records import AssessmentRecord, Outcome

RULE_ID = "G-03"
RULE_VERSION = "0.1"


@dataclass
class OrientationResult:
    df_oriented: pd.DataFrame
    records: list


def _compile(patterns):
    return [re.compile(p) for p in (patterns or [])]


def _all_match(labels, compiled):
    return bool(compiled) and all(any(c.fullmatch(str(x)) for c in compiled) for x in labels)


def _labels_vote(df, gene_patterns, sample_patterns):
    g, s = _compile(gene_patterns), _compile(sample_patterns)
    if not g and not s:
        return {"available": False, "vote": None}
    rows, cols = list(df.index), list(df.columns)
    rows_gene, cols_gene = _all_match(rows, g), _all_match(cols, g)
    rows_sample, cols_sample = _all_match(rows, s), _all_match(cols, s)
    as_is = rows_gene or cols_sample
    flipped = rows_sample or cols_gene
    if as_is and not flipped:
        vote = "as_is"
    elif flipped and not as_is:
        vote = "transpose"
    else:
        vote = "ambiguous"
    return {"available": True, "vote": vote, "rows_gene_like": rows_gene,
            "cols_gene_like": cols_gene, "rows_sample_like": rows_sample,
            "cols_sample_like": cols_sample}


def _metadata_vote(df, metadata_sample_ids):
    if metadata_sample_ids is None:
        return {"available": False, "vote": None}
    ids = {str(x) for x in metadata_sample_ids}
    rows_match = any(str(x) in ids for x in df.index)
    cols_match = any(str(x) in ids for x in df.columns)
    if cols_match and not rows_match:
        vote = "as_is"
    elif rows_match and not cols_match:
        vote = "transpose"
    else:
        vote = "ambiguous"
    return {"available": True, "vote": vote, "rows_match": rows_match,
            "cols_match": cols_match}


def _length_vote(df):
    n_rows, n_cols = df.shape
    if n_rows > n_cols:
        vote = "as_is"
    elif n_rows < n_cols:
        vote = "transpose"
    else:
        vote = "ambiguous"
    return {"available": True, "vote": vote, "n_rows": n_rows, "n_columns": n_cols}


def _record(scope, outcome, basis, signals, extra=None):
    evidence = {"signals": signals}
    evidence.update(extra or {})
    return AssessmentRecord(
        check_id="G-03.orientation",
        rule_id=RULE_ID,
        rule_version=RULE_VERSION,
        scope=scope,
        outcome=outcome,
        evidence=evidence,
        confidence=None,
        limitations=(),
        decision_basis=basis,
    )


def detect_orientation(
    df,
    metadata_sample_ids=None,
    gene_patterns=None,
    sample_patterns=None,
    scope="matrix",
) -> OrientationResult:
    signals = {
        "labels": _labels_vote(df, gene_patterns, sample_patterns),
        "metadata": _metadata_vote(df, metadata_sample_ids),
        "length": _length_vote(df),
    }

    def need_fact(basis):
        return OrientationResult(
            df, [_record(scope, Outcome.NEED_FACT, basis, signals,
                         {"transposed": False})]
        )

    if 0 in df.shape:
        return need_fact("matrix has an empty axis: orientation cannot be assessed")
    if df.shape[0] == df.shape[1]:
        return need_fact("square matrix: orientation cannot be decided from structure; "
                         "no transpose made")

    available = {k: v["vote"] for k, v in signals.items() if v["available"]}
    if any(v == "ambiguous" for v in available.values()):
        return need_fact("an available structural signal is ambiguous: "
                         + ", ".join(k for k, v in available.items() if v == "ambiguous")
                         + "; no transpose made")
    votes = set(available.values())
    if len(votes) > 1:
        return need_fact("structural signals disagree: "
                         + ", ".join(f"{k}={v}" for k, v in available.items())
                         + "; no transpose made")

    vote = votes.pop()
    if vote == "as_is":
        return OrientationResult(df, [_record(
            scope, Outcome.PASS,
            "available structural signals agree the matrix is genes x samples",
            signals, {"transposed": False})])

    # astype(object) first: a plain transpose of mixed int/float columns upcasts
    # everything to float64 and would silently round large integers.
    return OrientationResult(df.astype(object).T, [_record(
        scope, Outcome.RESOLVED,
        "all available structural signals agree the matrix was samples x genes; "
        "transposed (axes swapped, no value changed)",
        signals, {"transposed": True})])
