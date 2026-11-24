"""T1.7 sample matching (M-01, M-02) and Tier A metadata completeness (M-03).

Matching never changes a sample identity silently. Tier 1 is exact, tier 2 is a
documented mapping or the approved normalization, tier 3 is positional and only
with an explicit ``documented_order=True``. Near matches are never matches: they
are listed as candidates inside a ``need_fact`` record. The identity key of a
sample is always ``(study, sample_id)``.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Mapping

import numpy as np
import pandas as pd

from .duplicates import _same
from .records import AssessmentRecord, Outcome

_VERSION = "0.1"

_RELATION = ("equal after case-folding and removing all separators "
             "(whitespace, '-', '_' and '.')")


@dataclass(frozen=True)
class MatchResult:
    """Outcome of ``match_samples``.

    ``matches`` holds one dict per matched sample: study, sample_id (the metadata
    ID), matrix_id and tier. Everything is plain strings, so it is JSON-safe.
    """

    matches: list[dict]
    unmatched_matrix: list[str]
    unmatched_metadata: list[str]
    records: list[AssessmentRecord] = field(default_factory=list)


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


def _is_sep(ch):
    return ch.isspace() or ch in "-_."


def normalize_id(value) -> str:
    """Tier 2 form: case-fold, trim, and one ``-`` for each run of whitespace, ``-``, ``_`` or ``.``."""
    out = []
    prev_sep = False
    for ch in str(value).strip().casefold():
        if _is_sep(ch):
            if not prev_sep:
                out.append("-")
            prev_sep = True
        else:
            out.append(ch)
            prev_sep = False
    return "".join(out)


def _squash(value) -> str:
    """Candidate relation key: case-folded with every separator removed."""
    return "".join(ch for ch in str(value).casefold() if not _is_sep(ch))


def _duplicated(ids):
    seen, dup = set(), []
    for x in ids:
        if x in seen and x not in dup:
            dup.append(x)
        seen.add(x)
    return dup


def _match(study, matrix_id, sample_id, tier):
    return {"study": study, "sample_id": sample_id, "matrix_id": matrix_id, "tier": tier}


def match_samples(matrix_ids, metadata_ids, study, mapping=None,
                  documented_order=False, scope="matrix") -> MatchResult:
    """Match matrix sample IDs to metadata sample IDs of one study (M-01, M-02).

    ``mapping`` is an optional documented ``{matrix_id: metadata_id}`` dict. Inputs
    are never mutated; IDs are converted to ``str``.
    """
    m_ids = [str(x) for x in matrix_ids]
    d_ids = [str(x) for x in metadata_ids]
    records: list[AssessmentRecord] = []

    if study is None or str(study).strip() == "":
        records.append(_rec(
            "M-01", "M-01.study", scope, Outcome.NEED_FACT,
            "the study of these samples is missing; the identity key is (study, "
            "sample) so no sample can be matched",
            {"matrix_ids": len(m_ids), "metadata_ids": len(d_ids),
             "consequence": "No sample is matched until the study is supplied."},
        ))
        return MatchResult([], m_ids, d_ids, records)
    study_s = str(study)

    if not m_ids:
        records.append(_rec(
            "M-01", "M-01.no_ids", scope, Outcome.NOT_ASSESSABLE,
            "no matrix sample IDs were given; matching cannot be assessed",
            {"study": study_s, "metadata_ids": len(d_ids)},
        ))
        return MatchResult([], m_ids, d_ids, records)

    dup_m, dup_d = _duplicated(m_ids), _duplicated(d_ids)
    if dup_m:
        records.append(_rec(
            "M-01", "M-01.duplicate_matrix_ids", scope, Outcome.NEED_FACT,
            f"{len(dup_m)} matrix sample ID(s) occur more than once; they are not "
            "matched automatically",
            {"study": study_s, "ids": dup_m,
             "consequence": "These samples stay unresolved until it is known which "
                            "column each ID refers to."},
        ))
    if dup_d:
        records.append(_rec(
            "M-01", "M-01.duplicate_metadata_ids", scope, Outcome.NEED_FACT,
            f"{len(dup_d)} metadata sample ID(s) occur more than once; they are not "
            "matched automatically",
            {"study": study_s, "ids": dup_d,
             "consequence": "These samples stay unresolved until it is known which "
                            "metadata row applies."},
        ))
    dup_m_set, dup_d_set = set(dup_m), set(dup_d)

    matches: list[dict] = []
    matched_m: set[str] = set()
    matched_d: set[str] = set()
    blocked: set[str] = set()  # matrix IDs whose documented mapping is unusable

    def add(x, d, tier):
        matches.append(_match(study_s, x, d, tier))
        matched_m.add(x)
        matched_d.add(d)

    def remaining():
        return ([x for x in m_ids if x not in dup_m_set and x not in matched_m
                 and x not in blocked],
                [x for x in d_ids if x not in dup_d_set and x not in matched_d])

    # tier 1: exact
    d_usable = {x for x in d_ids if x not in dup_d_set}
    for x in m_ids:
        if x not in dup_m_set and x in d_usable and x not in matched_d:
            add(x, x, "exact")

    # tier 2a: documented mapping
    if mapping:
        mp = {str(k): str(v) for k, v in mapping.items()}
        rem_m, rem_d = remaining()
        rem_d_set = set(rem_d)
        targets: dict[str, list[str]] = {}
        for x in rem_m:
            if x in mp:
                targets.setdefault(mp[x], []).append(x)
        problems = []
        for target, xs in targets.items():
            if len(xs) == 1 and target in rem_d_set:
                add(xs[0], target, "mapping")
            else:
                blocked.update(xs)
                problems.append({
                    "target": target, "matrix_ids": xs,
                    "reason": ("several matrix IDs map to the same target"
                               if len(xs) > 1 else
                               "target is not among the unmatched metadata IDs"),
                })
        if problems:
            records.append(_rec(
                "M-01", "M-01.mapping", scope, Outcome.NEED_FACT,
                f"{len(problems)} documented mapping entr(ies) cannot be applied",
                {"study": study_s, "problems": problems,
                 "consequence": "These samples are not matched until the mapping "
                                "is corrected."},
            ))

    # tier 2b: normalization
    rem_m, rem_d = remaining()
    groups_m: dict[str, list[str]] = defaultdict(list)
    groups_d: dict[str, list[str]] = defaultdict(list)
    for x in rem_m:
        groups_m[normalize_id(x)].append(x)
    for x in rem_d:
        groups_d[normalize_id(x)].append(x)
    collisions = []
    for key in list(dict.fromkeys(list(groups_m) + list(groups_d))):
        ms, ds = groups_m.get(key, []), groups_d.get(key, [])
        if len(ms) > 1 or len(ds) > 1:
            collisions.append({"normalized": key, "matrix_ids": ms, "metadata_ids": ds})
        elif len(ms) == 1 and len(ds) == 1:
            add(ms[0], ds[0], "normalized")
    if collisions:
        records.append(_rec(
            "M-01", "M-01.normalization_collision", scope, Outcome.NEED_FACT,
            f"{len(collisions)} group(s) of distinct IDs become identical after "
            "normalization; none is chosen",
            {"study": study_s, "collisions": collisions,
             "consequence": "IDs in these groups are not matched until it is known "
                            "which is which."},
        ))

    # tier 3: positional, only with explicit documented order
    positional = None
    if documented_order is not True:
        positional = "not applied: documented_order was not set to True"
    elif matches:
        positional = "not applied: tier 1 or 2 already matched IDs"
    elif blocked:
        positional = ("not applied: a documented mapping could not be applied, "
                      "so no samples are matched by position")
    elif collisions:
        positional = ("not applied: normalized IDs collide, so identities are "
                      "unresolved and no samples are matched by position")
    elif len(m_ids) != len(d_ids):
        positional = (f"not applied: counts differ ({len(m_ids)} matrix IDs, "
                      f"{len(d_ids)} metadata IDs)")
    elif dup_m or dup_d:
        positional = "not applied: duplicate IDs in an input list"
    else:
        for x, d in zip(m_ids, d_ids):
            add(x, d, "positional")
        records.append(_rec(
            "M-01", "M-01.positional", scope, Outcome.NOTE,
            "samples matched by position because tiers 1 and 2 matched nothing, "
            "counts are equal and the file order was declared documented",
            {"study": study_s, "n_matches": len(matches),
             "matches": [dict(m) for m in matches]},
        ))

    order = {x: i for i, x in enumerate(m_ids)}
    matches.sort(key=lambda m: order[m["matrix_id"]])

    by_tier: dict[str, int] = {}
    for m in matches:
        if m["tier"] != "positional":
            by_tier[m["tier"]] = by_tier.get(m["tier"], 0) + 1
    if by_tier:
        shown = [m for m in matches if m["tier"] != "positional"]
        records.append(_rec(
            "M-01", "M-01.match", scope, Outcome.PASS,
            f"{len(shown)} sample(s) matched by exact, documented-mapping or "
            "normalized ID",
            {"study": study_s, "n_matches": len(shown), "by_tier": by_tier,
             "matches": [dict(m) for m in shown]},
        ))

    # M-02: candidates only, for IDs still unmatched
    rem_m, rem_d = remaining()
    pool: dict[str, list[str]] = defaultdict(list)
    for x in rem_d:
        key = _squash(x)
        if key:
            pool[key].append(x)
    plain = []
    for x in rem_m:
        cands = pool.get(_squash(x), []) if _squash(x) else []
        if cands:
            records.append(_rec(
                "M-02", "M-02.candidates", scope, Outcome.NEED_FACT,
                f"matrix ID '{x}' has no exact or normalized match; "
                f"{len(cands)} candidate(s) differ only by case or separators",
                {"study": study_s, "matrix_id": x, "candidates": list(cands),
                 "relation": _RELATION,
                 "evidence": "candidate IDs differ from the matrix ID only in case "
                             "or separator characters",
                 "consequence": "No match is made. If a candidate is correct the "
                                "sample takes that metadata row; if none is, the "
                                "sample has no metadata."},
            ))
        else:
            plain.append(x)
    if plain:
        records.append(_rec(
            "M-01", "M-01.unmatched", scope, Outcome.NEED_FACT,
            f"{len(plain)} matrix sample(s) have no metadata match and no candidate",
            {"study": study_s, "matrix_ids": plain, "positional": positional,
             "consequence": "These samples cannot be assigned metadata until their "
                            "metadata row is identified."},
        ))

    unmatched_matrix = [x for x in m_ids if x not in matched_m]
    unmatched_metadata = [x for x in d_ids if x not in matched_d]
    note_ids = [x for x in unmatched_metadata if x not in dup_d_set]
    if note_ids:
        records.append(_rec(
            "M-01", "M-01.unmatched_metadata", scope, Outcome.NOTE,
            f"{len(note_ids)} metadata sample ID(s) have no matrix sample",
            {"study": study_s, "metadata_ids": note_ids},
        ))
    return MatchResult(matches, unmatched_matrix, unmatched_metadata, records)


def _cell_missing(value) -> bool:
    """True for None, pd.NA, pd.NaT, NaN, NumPy NaT and blank text (scalar checks only)."""
    if value is None or value is pd.NA or value is pd.NaT:
        return True
    if isinstance(value, (np.datetime64, np.timedelta64)):
        return bool(np.isnat(value))
    if isinstance(value, (float, np.floating)) and value != value:
        return True
    return isinstance(value, str) and value.strip() == ""


def _as_table(metadata) -> pd.DataFrame:
    if isinstance(metadata, pd.DataFrame):
        return metadata
    if isinstance(metadata, (list, tuple)) and all(isinstance(r, Mapping) for r in metadata):
        return pd.DataFrame(list(metadata), dtype=object)
    raise TypeError("metadata must be a DataFrame or a list of row mappings")


def tier_a_check(metadata, required_fields, scope="matrix") -> list[AssessmentRecord]:
    """M-03: every required Tier A field must be present and filled for every sample.

    One ``need_fact`` record per field that is absent, duplicated, or has missing
    values; a single ``pass`` record when all fields are complete. Values are not
    interpreted (label mapping belongs to M-06).
    """
    if isinstance(required_fields, str):
        required_fields = [required_fields]
    if required_fields is None:
        raise ValueError("required_fields must name at least one field")
    fields = list(dict.fromkeys(str(f) for f in required_fields))
    if not fields:
        raise ValueError("required_fields must name at least one field")

    df = _as_table(metadata)
    labels = [str(c) for c in df.columns]
    n_rows = len(df)
    records: list[AssessmentRecord] = []

    for name in fields:
        positions = [i for i, c in enumerate(labels) if c == name]
        ev = {"field": name, "n_samples": n_rows, "available_fields": list(labels)}
        if len(positions) > 1:
            ev.update(reason="duplicated_column",
                      consequence="The field cannot be used until one column carries it.")
            basis = f"required Tier A field '{name}' appears in more than one metadata column"
        elif not positions:
            ev.update(reason="absent",
                      consequence="Compatibility cannot be assessed without this field.")
            basis = f"required Tier A field '{name}' is missing from the metadata"
        elif n_rows == 0:
            ev.update(reason="no_rows",
                      consequence="Compatibility cannot be assessed without metadata rows.")
            basis = f"required Tier A field '{name}' has no metadata rows"
        else:
            values = df.iloc[:, positions[0]].tolist()
            missing_rows = [i for i, v in enumerate(values) if _cell_missing(v)]
            if not missing_rows:
                continue
            ev.update(reason="incomplete", n_missing=len(missing_rows),
                      missing_rows=missing_rows,
                      consequence="Samples without this value cannot be assigned to a "
                                  "group until it is supplied.")
            basis = (f"required Tier A field '{name}' has no value for "
                     f"{len(missing_rows)} of {n_rows} sample(s)")
        records.append(_rec("M-03", f"M-03.{name}", scope, Outcome.NEED_FACT, basis, ev))

    if not records:
        records.append(_rec(
            "M-03", "M-03.tier_a", scope, Outcome.PASS,
            "all required Tier A fields are present for every sample",
            {"fields": fields, "n_samples": n_rows},
        ))
    return records


def _safe_value(value):
    """JSON-safe view of a cell: text stays text, anything else is shown by ``repr``."""
    if isinstance(value, str):
        return str(value)
    try:
        return repr(value)
    except Exception:
        return f"<unrepresentable {type(value).__name__}>"


def find_metadata_duplicates(metadata, id_column, scope="matrix") -> list[AssessmentRecord]:
    """M-01: classify duplicate metadata sample IDs as identical or conflicting rows.

    Rows are grouped by ``str(id_cell)``, exactly as ``match_samples`` groups
    duplicate metadata IDs, so both report the same IDs. Every duplicated ID gives
    one ``need_fact`` record whether its rows are identical or conflicting. No row
    is removed, merged or chosen as the correct one.

    Rows are compared on every column except the ID column. Text cells compare
    exactly (no trimming, no case folding). Typed cells from API callers follow the
    exact-cell rule of ``duplicates._same``: None, NaN, ``pd.NA``, ``pd.NaT`` and
    NumPy NaT form one missing class, and cells of different kinds are never equal
    (``5`` and ``"5"``, ``1`` and ``1.0``). Positions are 0-based positions among the
    parsed data rows, not file line numbers or index labels.

    If the ID column is absent or its label is duplicated, one
    ``M-01.metadata_id_column`` record is returned and nothing is grouped. Blank or
    missing IDs (``_cell_missing``) are reported in one ``M-01.metadata_id_column``
    record; their rows are kept and still take part in grouping. No duplicates
    returns an empty list. ``metadata`` is never modified.
    """
    df = _as_table(metadata)
    name = str(id_column)
    labels = [str(c) for c in df.columns]
    n_rows = len(df)

    id_positions = [j for j, c in enumerate(labels) if c == name]
    if len(id_positions) != 1:
        if id_positions:
            reason = "duplicated_column"
            basis = (f"the metadata sample-ID column '{name}' appears in more than one "
                     "column; duplicate IDs were not assessed")
            extra = {"column_positions": id_positions}
        else:
            reason = "absent"
            basis = (f"the metadata sample-ID column '{name}' is missing from the "
                     "metadata; duplicate IDs were not assessed")
            extra = {}
        return [_rec(
            "M-01", "M-01.metadata_id_column", scope, Outcome.NEED_FACT, basis,
            {"id_column": name, "reason": reason, "n_rows": n_rows,
             "available_columns": list(labels), **extra,
             "consequence": "Metadata rows cannot be identified, so duplicate IDs were "
                            "not assessed until the sample-ID column is identified."},
        )]

    id_pos = id_positions[0]
    raw_ids = df.iloc[:, id_pos].tolist()
    ids = [str(x) for x in raw_ids]
    records: list[AssessmentRecord] = []

    blank_rows = [i for i, x in enumerate(raw_ids) if _cell_missing(x)]
    if blank_rows:
        records.append(_rec(
            "M-01", "M-01.metadata_id_column", scope, Outcome.NEED_FACT,
            f"{len(blank_rows)} of {n_rows} metadata row(s) have a blank or missing "
            f"sample ID in column '{name}'",
            {"id_column": name, "reason": "blank_ids", "n_blank": len(blank_rows),
             "row_positions": blank_rows, "n_rows": n_rows,
             "consequence": "These rows are retained and still take part in duplicate "
                            "grouping; their sample identity is unknown."},
        ))

    other = [(j, labels[j], df.iloc[:, j].tolist())
             for j in range(len(labels)) if j != id_pos]
    rows_of: dict[str, list[int]] = defaultdict(list)
    for i, x in enumerate(ids):
        rows_of[x].append(i)
    blank_set = set(blank_rows)

    for dup_id in _duplicated(ids):
        rows = rows_of[dup_id]
        differing = []
        for j, label, values in other:
            cells = [values[i] for i in rows]
            if not all(_same(cells[0], c) for c in cells[1:]):
                differing.append({
                    "field": label, "position": j,
                    "values": [_safe_value(c) for c in cells],
                    "types": [type(c).__name__ for c in cells],
                })
        identical = not differing
        kept = (f"all {len(rows)} rows are retained, none is removed or selected as "
                "the correct row")
        if identical:
            basis = (f"duplicate metadata ID '{dup_id}' in {len(rows)} rows with "
                     f"identical values in all {len(other)} other field(s); {kept}")
        else:
            names = ", ".join(f"'{d['field']}'" for d in differing)
            basis = (f"duplicate metadata ID '{dup_id}' in {len(rows)} rows that differ "
                     f"in {len(differing)} of {len(other)} other field(s): {names}; {kept}")
        records.append(_rec(
            "M-01", "M-01.duplicate_metadata_rows", scope, Outcome.NEED_FACT, basis,
            {"id": dup_id, "id_column": name, "row_positions": list(rows),
             "n_rows": len(rows),
             "classification": "identical" if identical else "conflicting",
             "n_fields_compared": len(other), "differing_fields": differing,
             "blank": any(i in blank_set for i in rows),
             "all_rows_retained": True,
             "consequence": f"{kept[0].upper()}{kept[1:]}; which row applies is "
                            "unresolved."},
        ))
    return records
