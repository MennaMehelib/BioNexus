"""BioNexus V1 M1 intake runner and CLI (S0-S3 + J-05 rule-gap handling)."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .duplicates import find_duplicates
from .fileio import ParseResult, first_column_as_index, parse_matrix
from .metadata import find_metadata_duplicates, match_samples, tier_a_check
from .orientation import detect_orientation
from .provenance import ProvenanceLog, sha256_file, verify_unchanged
from .records import (
    AssessmentRecord,
    Outcome,
    RuleGap,
    State,
    combine_outcomes,
    rule_gap_record,
)
from .representation import evidence_record
from .scope import scope_gate

RULE_VERSION = "0.1"
_RECOGNIZED_DECLARED_KEYS = frozenset(
    {"organism", "technology", "level", "id_type", "representation", "study"}
)
_TIER_A_FIELDS = ("condition", "tissue", "organism")


@dataclass(frozen=True)
class IntakeResult:
    scope: str
    state: State
    records: list[AssessmentRecord]
    out_dir: Path
    records_path: Path
    provenance_path: Path
    refusal_reason: str | None = None


def _validate_out_dir(out_dir: Path, input_paths: list[Path]) -> Path:
    resolved_out = out_dir.resolve()
    for inp in input_paths:
        resolved_inp = inp.resolve()
        if resolved_out == resolved_inp or resolved_out == resolved_inp.parent:
            raise ValueError(
                f"output directory {out_dir} must not collide with input path or directory {inp}"
            )
    if os.path.lexists(out_dir) and not out_dir.is_dir():
        raise ValueError(f"output path {out_dir} exists and is not a directory")
    if out_dir.is_dir():
        entries = sorted(os.listdir(out_dir))
        if entries:
            preview = ", ".join(entries[:3])
            raise ValueError(
                f"output directory {out_dir} is not empty ({len(entries)} entries, "
                f"e.g. {preview}); choose a new or empty directory; nothing was modified"
            )
        return out_dir
    try:
        out_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise ValueError(
            f"output path {out_dir} already exists and could not be created; "
            "nothing was overwritten"
        ) from exc
    return out_dir


def _parse_metadata(metadata_path: Path) -> ParseResult:
    """Parse metadata read-only via parse_matrix, supporting single-column tables."""
    res = parse_matrix(metadata_path)
    if res.df is not None:
        return res
    if (
        len(res.records) == 1
        and res.records[0].outcome is Outcome.NOT_ASSESSABLE
        and res.records[0].decision_basis
        == "no tab, comma or semicolon delimiter found in the content"
    ):
        text = metadata_path.read_bytes().decode("utf-8")
        change_log: list[str] = []
        if text.startswith("\ufeff"):
            text = text[1:]
            change_log.append("removed UTF-8 BOM")
        rows = [
            row
            for row in csv.reader(
                io.StringIO(text, newline=""), delimiter="\t", quotechar='"', strict=True
            )
            if row
        ]
        if len(rows) < 2:
            return ParseResult(
                None,
                [],
                [
                    AssessmentRecord(
                        check_id="G-02.parse",
                        rule_id="G-02",
                        rule_version=RULE_VERSION,
                        scope=str(metadata_path),
                        outcome=Outcome.BLOCKED,
                        evidence={
                            "delimiter": "none_single_column",
                            "header_labels": len(rows[0]) if rows else 0,
                        },
                        confidence=None,
                        limitations=(),
                        decision_basis="file has a header but no data rows",
                    )
                ],
            )
        if all(len(r) == 1 for r in rows):
            df = pd.DataFrame(rows[1:], columns=rows[0], dtype=object)
            return ParseResult(
                df,
                change_log,
                [
                    AssessmentRecord(
                        check_id="G-02.parse",
                        rule_id="G-02",
                        rule_version=RULE_VERSION,
                        scope=str(metadata_path),
                        outcome=Outcome.PASS,
                        evidence={
                            "delimiter": "none_single_column",
                            "n_rows": len(rows) - 1,
                            "n_columns": 1,
                        },
                        confidence=None,
                        limitations=(),
                        decision_basis="file parsed structurally (single-column metadata)",
                    )
                ],
            )
    return res


def _write_matrix_tsv(df: pd.DataFrame, path: Path) -> None:
    """Write exact string tokens without changing formatting or dropping duplicates."""
    index_label = "" if df.index.name is None else str(df.index.name)
    header = [index_label] + [str(c) for c in df.columns]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        for r in range(df.shape[0]):
            writer.writerow([df.index[r]] + [df.iloc[r, c] for c in range(df.shape[1])])


def _write_json(path: Path, payload: dict) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")


def run_intake(
    matrix_path: str | Path,
    metadata_path: str | Path,
    out_dir: str | Path,
    declared: Mapping[str, str] | None = None,
    *,
    metadata_id_column: str,
    annotation_genes: Iterable[str] | None = None,
) -> IntakeResult:
    """Run the M1 intake pipeline (S0-S3) into out_dir without altering originals."""
    if declared is None:
        declared_dict: dict[str, str] = {}
    elif isinstance(declared, Mapping):
        declared_dict = dict(declared)
    else:
        raise TypeError("declared must be a mapping or None")
    if not isinstance(metadata_id_column, str):
        raise TypeError("metadata_id_column must be a str")

    matrix_p = Path(matrix_path)
    metadata_p = Path(metadata_path)
    out_p = _validate_out_dir(Path(out_dir), [matrix_p, metadata_p])

    raw_study = declared_dict.get("study")
    scope = str(raw_study).strip() if isinstance(raw_study, str) and raw_study.strip() else "matrix"

    records: list[AssessmentRecord] = []
    prov = ProvenanceLog()
    written_outputs: set[Path] = set()
    refusal_reason: str | None = None

    # S0: read-only input hashing
    input_hashes: dict[Path, str] = {}
    s0_failed = False
    for inp in (matrix_p, metadata_p):
        try:
            h = sha256_file(inp)
        except OSError as exc:
            s0_failed = True
            records.append(
                AssessmentRecord(
                    check_id="G-04.verify_unchanged",
                    rule_id="G-04",
                    rule_version=RULE_VERSION,
                    scope=str(inp),
                    outcome=Outcome.BLOCKED,
                    evidence={
                        "stage": "S0",
                        "path": str(inp),
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                    confidence=None,
                    limitations=(),
                    decision_basis=f"input file unreadable ({type(exc).__name__})",
                )
            )
        else:
            input_hashes[inp] = h
            prov.add_input(inp)

    def _finalize() -> IntakeResult:
        for inp, expected in input_hashes.items():
            records.append(verify_unchanged(inp, expected))
        state = combine_outcomes(records)
        records_path = out_p / "records.json"
        _write_json(
            records_path,
            {
                "scope": scope,
                "state": state.value,
                "records": [r.to_dict() for r in records],
            },
        )
        written_outputs.add(records_path)
        if records_path in written_outputs:
            prov.add_step(
                "V-02",
                RULE_VERSION,
                {"state": state.value},
                [str(p) for p in input_hashes],
                [str(records_path)],
            )
        prov_path = out_p / "provenance.json"
        prov.write(prov_path)
        return IntakeResult(
            scope=scope,
            state=state,
            records=records,
            out_dir=out_p,
            records_path=records_path,
            provenance_path=prov_path,
            refusal_reason=refusal_reason,
        )

    if s0_failed:
        return _finalize()

    # S1: parse matrix and metadata (never touch originals)
    parsed_matrix_path = out_p / "parsed_matrix.tsv"
    matrix_res = parse_matrix(matrix_p, out_path=parsed_matrix_path)
    records.extend(matrix_res.records)
    if matrix_res.df is None:
        return _finalize()
    written_outputs.add(parsed_matrix_path)
    if parsed_matrix_path in written_outputs:
        prov.add_step(
            "G-02",
            RULE_VERSION,
            {"change_log": list(matrix_res.change_log)},
            [str(matrix_p)],
            [str(parsed_matrix_path)],
        )

    indexed_df = first_column_as_index(matrix_res.df)
    meta_res = _parse_metadata(metadata_p)
    records.extend(meta_res.records)
    metadata_df = meta_res.df

    # Scope gate (G-01) and J-05 RuleGap checks
    scope_recs = scope_gate(declared_dict, scope=scope)
    records.extend(scope_recs)
    for key in sorted(k for k in declared_dict if k not in _RECOGNIZED_DECLARED_KEYS):
        records.append(
            rule_gap_record(
                RuleGap(
                    scope=scope,
                    description=f"declared key '{key}' is not covered by any M1 rule",
                    missing=f"rule handling for declared attribute '{key}'",
                )
            )
        )

    blocked_scope = [r for r in scope_recs if r.outcome is Outcome.BLOCKED]
    if blocked_scope:
        refusal_reason = "out of V1 scope: " + "; ".join(
            r.decision_basis for r in blocked_scope
        )
        return _finalize()

    # M-01 ID-column validation and metadata duplicate classification (T18-D6)
    metadata_sample_ids: list[str] | None = None
    id_column_valid = False
    if metadata_df is not None:
        id_records = find_metadata_duplicates(
            metadata_df, metadata_id_column, scope=scope
        )
        records.extend(id_records)
        id_column_valid = not any(
            r.check_id == "M-01.metadata_id_column" for r in id_records
        )
        if id_column_valid:
            id_pos = next(
                j
                for j, col in enumerate(metadata_df.columns)
                if str(col) == metadata_id_column
            )
            metadata_sample_ids = [
                str(x) for x in metadata_df.iloc[:, id_pos].tolist()
            ]
        prov.add_step(
            "M-01",
            RULE_VERSION,
            {
                "operation": "metadata_id_validation_and_duplicate_classification",
                "metadata_id_column": metadata_id_column,
                "id_column_valid": id_column_valid,
            },
            [str(metadata_p)],
            [],
        )

    # Orientation (G-03)
    orient_res = detect_orientation(
        indexed_df, metadata_sample_ids=metadata_sample_ids, scope=scope
    )
    records.extend(orient_res.records)
    if any(r.outcome is Outcome.NEED_FACT for r in orient_res.records):
        # Stop orientation-dependent stages; still run metadata-only M-03
        if metadata_df is not None:
            records.extend(tier_a_check(metadata_df, list(_TIER_A_FIELDS), scope=scope))
        return _finalize()

    oriented_df = orient_res.df_oriented
    oriented_path = out_p / "oriented_matrix.tsv"
    _write_matrix_tsv(oriented_df, oriented_path)
    written_outputs.add(oriented_path)
    transposed = any(r.outcome is Outcome.RESOLVED for r in orient_res.records)
    if oriented_path in written_outputs:
        prov.add_step(
            "G-03",
            RULE_VERSION,
            {"transposed": transposed},
            [str(parsed_matrix_path)],
            [str(oriented_path)],
        )

    # S2: sample matching (M-01, M-02) & Tier A completeness (M-03)
    if id_column_valid and metadata_sample_ids is not None:
        match_res = match_samples(
            [str(c) for c in oriented_df.columns],
            metadata_sample_ids,
            study=declared_dict.get("study"),
            scope=scope,
        )
        records.extend(match_res.records)
        matches_path = out_p / "sample_matches.json"
        _write_json(
            matches_path,
            {
                "study": declared_dict.get("study"),
                "matches": match_res.matches,
                "unmatched_matrix": match_res.unmatched_matrix,
                "unmatched_metadata": match_res.unmatched_metadata,
            },
        )
        written_outputs.add(matches_path)
        if matches_path in written_outputs:
            prov.add_step(
                "M-01",
                RULE_VERSION,
                {
                    "operation": "sample_matching",
                    "study": declared_dict.get("study"),
                    "metadata_id_column": metadata_id_column,
                },
                [str(oriented_path), str(metadata_p)],
                [str(matches_path)],
            )

    if metadata_df is not None:
        records.extend(tier_a_check(metadata_df, list(_TIER_A_FIELDS), scope=scope))

    # S3: representation evidence (R-01, R-02, R-05, R-06)
    rep_res = evidence_record(
        oriented_df,
        declared=declared_dict.get("representation"),
        annotation_genes=annotation_genes,
        scope=scope,
    )
    records.extend(rep_res.records)
    rep_path = out_p / "representation_evidence.json"
    _write_json(rep_path, rep_res.to_dict())
    written_outputs.add(rep_path)
    if rep_path in written_outputs:
        prov.add_step(
            "R-01",
            RULE_VERSION,
            {"declared": declared_dict.get("representation")},
            [str(oriented_path)],
            [str(rep_path)],
        )

    # Duplicates (M-04, non-destructive)
    records.extend(find_duplicates(oriented_df, scope=scope))

    return _finalize()


def _parse_declared_pairs(items: list[list[str]]) -> dict[str, str]:
    declared: dict[str, str] = {}
    for group in items:
        for item in group:
            if "=" not in item:
                raise ValueError(f"invalid --declared item {item!r}: expected k=v")
            key, value = item.split("=", 1)
            if not key:
                raise ValueError(f"invalid --declared item {item!r}: empty key")
            if key in declared:
                raise ValueError(f"duplicate --declared key {key!r}")
            declared[key] = value
    return declared


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bionexus")
    sub = parser.add_subparsers(dest="command", required=True)
    intake_p = sub.add_parser("intake", help="Run M1 intake and representation evidence")
    intake_p.add_argument("--matrix", required=True, help="Path to expression matrix")
    intake_p.add_argument("--metadata", required=True, help="Path to metadata table")
    intake_p.add_argument(
        "--metadata-id-column",
        required=True,
        metavar="NAME",
        help="metadata column that holds the sample IDs",
    )
    intake_p.add_argument(
        "--declared",
        nargs="+",
        action="append",
        default=[],
        metavar="K=V",
        help="Declared metadata key=value pairs",
    )
    intake_p.add_argument("--out", required=True, help="Output directory")

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        return code if isinstance(code, int) else 1

    try:
        declared = _parse_declared_pairs(args.declared)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        res = run_intake(
            matrix_path=args.matrix,
            metadata_path=args.metadata,
            out_dir=args.out,
            declared=declared,
            metadata_id_column=args.metadata_id_column,
        )
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if res.refusal_reason:
        print(res.refusal_reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
