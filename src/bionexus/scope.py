"""T1.6 Scope gate (G-01, ACCEPT-M1).

Decides whether a *declared* organism / technology / level (+ optional id_type)
fall within BioNexus V1 scope. Declaration-only: never inspects the expression
matrix, never infers identifier types, and never applies value-based checks.
Every declared field is checked (no short-circuiting); ``declared`` is never
mutated.
"""

from __future__ import annotations

from .records import AssessmentRecord, Outcome

_RULE_ID = "G-01"
_RULE_VERSION = "0.1"

_ORGANISM_IN_SCOPE = {"human", "homo-sapiens"}
_ORGANISM_OUT_OF_SCOPE = {"mouse", "mus-musculus"}
_TECHNOLOGY_IN_SCOPE = {"rna-seq", "rnaseq"}
_TECHNOLOGY_OUT_OF_SCOPE = {"microarray"}
_LEVEL_IN_SCOPE = {"gene", "gene-level"}
_LEVEL_OUT_OF_SCOPE = {"transcript", "transcript-level"}

_ID_TYPE_ACCEPTED = {
    "ensembl-gene", "entrez-gene", "symbol", "probe", "reporter", "unknown",
}
# Accepted, non-unknown identifier types that may take part in the consistency
# check (technology is in-scope RNA-seq).
_ID_TYPE_CONSISTENCY_RECOGNIZED = {
    "ensembl-gene", "entrez-gene", "symbol", "probe", "reporter",
}
_ID_TYPE_CONSISTENCY_NEED_FACT = {"probe", "reporter"}


def _safe(value):
    """JSON-safe, non-aliasing view of any caller value: str kept, anything else repr()."""
    if isinstance(value, str):
        return value
    try:
        return repr(value)
    except Exception:
        return f"<unrepresentable {type(value).__name__}>"


def _normalize(value):
    """str(value).strip().lower(), then collapse runs of spaces/underscores to one hyphen.

    Implemented without ``re`` so the module stays free of regex/accession logic.
    """
    try:
        s = str(value).strip().lower()
    except Exception:
        s = ""
    out = []
    prev_sep = False
    for ch in s:
        if ch == " " or ch == "_":
            if not prev_sep:
                out.append("-")
            prev_sep = True
        else:
            out.append(ch)
            prev_sep = False
    return "".join(out)


def _is_missing(value):
    """Missing = absent/None/empty/whitespace-only (only for strings)."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def scope_gate(declared: dict, scope: str = "matrix") -> list[AssessmentRecord]:
    """Assess declared metadata against V1 scope.

    Returns a list of ``AssessmentRecord`` (rule_id ``G-01``, version ``0.1``,
    confidence ``None``, limitations ``()``). Never mutates ``declared``.
    """
    records = []

    def record(check_id, field, value, normalized, outcome, basis, evidence):
        records.append(AssessmentRecord(
            check_id=check_id,
            rule_id=_RULE_ID,
            rule_version=_RULE_VERSION,
            scope=scope,
            outcome=outcome,
            evidence=evidence,
            confidence=None,
            limitations=(),
            decision_basis=basis,
        ))

    def check_field(field, value, in_scope, out_of_scope, accepted_label):
        if _is_missing(value):
            record(f"G-01.{field}", field, value, None, Outcome.NEED_FACT,
                   f"declared {field} is missing; accepted V1 values: {accepted_label}",
                   {"field": field, "declared": _safe(value), "declared_type": type(value).__name__, "normalized": None})
            return
        normalized = _normalize(value)
        if normalized in in_scope:
            record(f"G-01.{field}", field, value, normalized, Outcome.PASS,
                   f"declared {field} '{_safe(value)}' is in V1 scope",
                   {"field": field, "declared": _safe(value), "declared_type": type(value).__name__, "normalized": normalized})
        elif normalized in out_of_scope:
            record(f"G-01.{field}", field, value, normalized, Outcome.BLOCKED,
                   f"declared {field} '{_safe(value)}' is out of V1 scope",
                   {"field": field, "declared": _safe(value), "declared_type": type(value).__name__, "normalized": normalized})
        else:
            record(f"G-01.{field}", field, value, normalized, Outcome.NEED_FACT,
                   f"declared {field} '{_safe(value)}' is not a recognized V1 value; "
                   f"accepted: {accepted_label}",
                   {"field": field, "declared": _safe(value), "declared_type": type(value).__name__, "normalized": normalized})

    # --- the three core fields, each checked independently ---
    check_field("organism", declared.get("organism"),
                _ORGANISM_IN_SCOPE, _ORGANISM_OUT_OF_SCOPE, "human, homo-sapiens")

    tech_value = declared.get("technology")
    check_field("technology", tech_value,
                _TECHNOLOGY_IN_SCOPE, _TECHNOLOGY_OUT_OF_SCOPE, "rna-seq, rnaseq")

    check_field("level", declared.get("level"),
                _LEVEL_IN_SCOPE, _LEVEL_OUT_OF_SCOPE, "gene, gene-level")

    # --- id_type (optional) ---
    id_type_value = declared.get("id_type")
    normalized_id = None
    if not _is_missing(id_type_value):
        normalized_id = _normalize(id_type_value)
        if normalized_id == "unknown":
            pass  # accepted but carries no information: no record
        elif normalized_id not in _ID_TYPE_ACCEPTED:
            record("G-01.id_type", "id_type", id_type_value, normalized_id,
                   Outcome.NEED_FACT,
                   f"declared id_type '{_safe(id_type_value)}' is not a recognized V1 identifier type; "
                   f"accepted: ensembl-gene, entrez-gene, symbol, probe, reporter, unknown",
                   {"field": "id_type", "declared": _safe(id_type_value),
                    "declared_type": type(id_type_value).__name__,
                    "normalized": normalized_id})
        # accepted non-unknown id_type: no id_type record of its own

    # --- consistency (only when tech is recognized in-scope RNA-seq AND the
    #     id_type is a recognized non-unknown identifier type) ---
    tech_normalized = None if _is_missing(tech_value) else _normalize(tech_value)
    if tech_normalized in _TECHNOLOGY_IN_SCOPE:
        if not _is_missing(id_type_value) and normalized_id in _ID_TYPE_CONSISTENCY_RECOGNIZED:
            if normalized_id in _ID_TYPE_CONSISTENCY_NEED_FACT:
                record("G-01.consistency", "consistency",
                       {"technology": _safe(tech_value), "id_type": _safe(id_type_value)}, None,
                       Outcome.NEED_FACT,
                       "declared RNA-seq but declared identifiers are probe/reporter IDs; "
                       "confirm the technology and the identifier type",
                       {"check": "G-01.consistency", "technology": _safe(tech_value),
                        "id_type": _safe(id_type_value), "normalized_id_type": normalized_id})
            else:
                record("G-01.consistency", "consistency",
                       {"technology": _safe(tech_value), "id_type": _safe(id_type_value)}, None,
                       Outcome.PASS,
                       "declared RNA-seq with recognized gene identifiers; scope-consistent",
                       {"check": "G-01.consistency", "technology": _safe(tech_value),
                        "id_type": _safe(id_type_value), "normalized_id_type": normalized_id})

    return records
