"""End-to-end integration tests for T1.8 intake runner and rule-gap handling (J-05)."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from bionexus.cli import main, run_intake
from bionexus.fileio import first_column_as_index, parse_matrix
from bionexus.provenance import sha256_file
from bionexus.records import AssessmentRecord, Outcome, State
from bionexus.rules import RuleRegistry

FIXTURES_ROOT = Path(__file__).parent / "fixtures"
MANIFEST_PATH = FIXTURES_ROOT / "expected_outcomes.json"
MANIFEST = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
FIXTURES = MANIFEST["fixtures"]
FIXTURE_BY_ID = {f["id"]: f for f in FIXTURES}
REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_RECORD_KEYS = {
    "check_id",
    "rule_id",
    "rule_version",
    "scope",
    "outcome",
    "evidence",
    "confidence",
    "limitations",
    "decision_basis",
}
# Frozen id -> expected_state map for F01-F27 (superseded raw hash 68ab9bc1...d293)
FROZEN_ORIGINAL_STATES = {
    "F01": "compatible",
    "F02": "compatible",
    "F03": "compatible",
    "F04": "incompatible",
    "F05": "requires_manual_review",
    "F06": "incompatible",
    "F07": "incompatible",
    "F08": "incompatible",
    "F09": "requires_manual_review",
    "F10": "compatible",
    "F11": "requires_manual_review",
    "F12": "requires_manual_review",
    "F13": "requires_manual_review",
    "F14": "incompatible",
    "F15": "requires_manual_review",
    "F16": "compatible",
    "F17": "requires_manual_review",
    "F18": "requires_manual_review",
    "F19": "compatible",
    "F20": "requires_manual_review",
    "F21": "compatible_with_warnings",
    "F22": "requires_manual_review",
    "F23": "requires_manual_review",
    "F24": "requires_manual_review",
    "F25": "compatible",
    "F26": "requires_manual_review",
    "F27": "requires_manual_review",
}


def _load_annotation(spec: dict, fdir: Path) -> list[str] | None:
    rel = spec.get("annotation_genes")
    if rel is None:
        return None
    lines = (fdir / rel).read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip()]


def _validate_records_payload(payload: dict, registry: RuleRegistry) -> None:
    assert set(payload.keys()) == {"scope", "state", "records"}
    assert isinstance(payload["scope"], str) and payload["scope"]
    State(payload["state"])
    assert isinstance(payload["records"], list) and payload["records"]
    for raw in payload["records"]:
        assert set(raw.keys()) == REQUIRED_RECORD_KEYS
        assert isinstance(raw["check_id"], str) and raw["check_id"]
        assert isinstance(raw["rule_id"], str) and raw["rule_id"]
        assert isinstance(raw["scope"], str) and raw["scope"]
        registry.status(raw["rule_id"])  # must exist in rules_register.json
        rec = AssessmentRecord(
            check_id=raw["check_id"],
            rule_id=raw["rule_id"],
            rule_version=raw["rule_version"],
            scope=raw["scope"],
            outcome=Outcome(raw["outcome"]),
            evidence=raw["evidence"],
            confidence=raw["confidence"],
            limitations=tuple(raw["limitations"]),
            decision_basis=raw["decision_basis"],
        )
        json.dumps(rec.to_dict(), allow_nan=False)


def _find_records(
    payload: dict,
    *,
    rule_id: str | None = None,
    outcome: str | None = None,
    check_id: str | None = None,
):
    return [
        r for r in payload["records"]
        if (rule_id is None or r["rule_id"] == rule_id)
        and (outcome is None or r["outcome"] == outcome)
        and (check_id is None or r["check_id"] == check_id)
    ]


def _m01_steps(prov_payload: dict, operation: str | None = None) -> list[dict]:
    return [
        s for s in prov_payload["steps"]
        if s["rule_id"] == "M-01"
        and (operation is None or s["parameters"].get("operation") == operation)
    ]


def _run_fixture(fid: str, out_dir: Path):
    spec = FIXTURE_BY_ID[fid]
    fdir = FIXTURES_ROOT / spec["dir"]
    matrix_path = fdir / spec["matrix"]
    metadata_path = fdir / spec["metadata"]
    ann = _load_annotation(spec, fdir)
    run_intake(
        matrix_path=matrix_path,
        metadata_path=metadata_path,
        out_dir=out_dir,
        declared=dict(spec["declared"]),
        metadata_id_column=spec["metadata_id_column"],
        annotation_genes=ann,
    )
    records_payload = json.loads((out_dir / "records.json").read_text(encoding="utf-8"))
    prov_payload = json.loads((out_dir / "provenance.json").read_text(encoding="utf-8"))
    return spec, fdir, records_payload, prov_payload


def _write_case(tmp_path: Path, name: str, metadata_text: str, matrix_text: str | None = None):
    in_dir = tmp_path / f"in_{name}"
    in_dir.mkdir(parents=True, exist_ok=True)
    m = in_dir / "matrix.tsv"
    md = in_dir / "metadata.tsv"
    if matrix_text is None:
        matrix_text = "gene\tS1\tS2\nG1\t10\t3\nG2\t0\t100\nG3\t5\t0\nG4\t1\t2\n"
    m.write_text(matrix_text, encoding="utf-8", newline="\n")
    md.write_text(metadata_text, encoding="utf-8", newline="\n")
    return m, md


# ---------------------------------------------------------- Manifest hash lock
def test_manifest_canonical_sha256_matches_pinned_hash():
    pinned = (FIXTURES_ROOT / "expected_outcomes.sha256").read_text(encoding="utf-8").strip()
    canonical = json.dumps(MANIFEST, sort_keys=True, separators=(",", ":")).encode("utf-8")
    actual = hashlib.sha256(canonical).hexdigest()
    assert actual == pinned


def test_original_27_fixture_states_unchanged():
    assert len(FIXTURES) == 31
    actual = {f["id"]: f["expected_state"] for f in FIXTURES if f["id"] in FROZEN_ORIGINAL_STATES}
    assert actual == FROZEN_ORIGINAL_STATES


# ------------------------------------------------------------------ AC1/2/5/6
@pytest.mark.parametrize("spec", FIXTURES, ids=[f["id"] for f in FIXTURES])
def test_fixture_expected_outcome(spec, tmp_path):
    fdir = FIXTURES_ROOT / spec["dir"]
    before_files = sorted(p.name for p in fdir.iterdir())
    assert set(before_files) == set(spec["file_hashes"].keys())
    for fname, expected_sha in spec["file_hashes"].items():
        assert sha256_file(fdir / fname) == expected_sha

    out_dir = tmp_path / "out"
    ann = _load_annotation(spec, fdir)
    run_intake(
        matrix_path=fdir / spec["matrix"],
        metadata_path=fdir / spec["metadata"],
        out_dir=out_dir,
        declared=dict(spec["declared"]),
        metadata_id_column=spec["metadata_id_column"],
        annotation_genes=ann,
    )

    # AC2: input directory untouched and original bytes strictly identical
    assert sorted(p.name for p in fdir.iterdir()) == before_files
    for fname, expected_sha in spec["file_hashes"].items():
        assert sha256_file(fdir / fname) == expected_sha

    # AC6: records.json schema + strict JSON
    records_text = (out_dir / "records.json").read_text(encoding="utf-8")
    records_payload = json.loads(records_text)
    json.dumps(records_payload, allow_nan=False)
    _validate_records_payload(records_payload, RuleRegistry())

    # AC1: pre-registered combined state, required records, forbidden rule IDs
    assert records_payload["state"] == spec["expected_state"]
    for req in spec["required_records"]:
        hits = _find_records(
            records_payload,
            rule_id=req["rule_id"],
            outcome=req["outcome"],
            check_id=req["check_id"],
        )
        assert hits, f"{spec['id']} missing required record {req}"
    present_rules = {r["rule_id"] for r in records_payload["records"]}
    for forbidden in spec["forbidden_rule_ids"]:
        assert forbidden not in present_rules, f"{spec['id']} unexpectedly ran {forbidden}"

    # Expected derived artifacts presence/absence
    oriented_file = out_dir / "oriented_matrix.tsv"
    matches_file = out_dir / "sample_matches.json"
    rep_file = out_dir / "representation_evidence.json"
    assert oriented_file.exists() is spec["expect_oriented_matrix"]
    assert matches_file.exists() is spec["expect_sample_matches"]
    assert rep_file.exists() is spec["expect_representation_evidence"]

    # AC5: value equality on derived matrices (no value change except axis transpose)
    if oriented_file.exists():
        orig_parsed = parse_matrix(fdir / spec["matrix"])
        assert orig_parsed.df is not None
        orig_idx = first_column_as_index(orig_parsed.df)
        expected_df = orig_idx.astype(object).T if spec["expect_transposed"] else orig_idx

        derived_parsed = parse_matrix(oriented_file)
        assert derived_parsed.df is not None
        derived_idx = first_column_as_index(derived_parsed.df)
        assert [str(x) for x in derived_idx.index] == [str(x) for x in expected_df.index]
        assert [str(x) for x in derived_idx.columns] == [str(x) for x in expected_df.columns]
        assert derived_idx.values.tolist() == expected_df.values.tolist()

    # V-02 provenance.json strict JSON + hash integrity
    prov_payload = json.loads((out_dir / "provenance.json").read_text(encoding="utf-8"))
    json.dumps(prov_payload, allow_nan=False)
    input_hashes = {Path(i["path"]).name: i["sha256"] for i in prov_payload["inputs"]}
    assert input_hashes[Path(spec["matrix"]).name] == spec["file_hashes"][spec["matrix"]]
    assert input_hashes[Path(spec["metadata"]).name] == spec["file_hashes"][spec["metadata"]]
    for step in prov_payload["steps"]:
        for out_entry in step["outputs"]:
            p = Path(out_entry["path"])
            assert p.exists()
            assert out_entry["sha256"] == sha256_file(p)
            assert set(out_entry["software_versions"]) == {"bionexus", "python", "pandas", "numpy"}


# ----------------------------------------------------------- G-01 P / N / E
def test_G01_P_human_rnaseq_gene_accepted(tmp_path):
    _, _, payload, _ = _run_fixture("F01", tmp_path / "out")
    assert payload["state"] == "compatible"
    assert _find_records(payload, rule_id="G-01", outcome="pass", check_id="G-01.organism")
    assert _find_records(payload, rule_id="G-01", outcome="pass", check_id="G-01.technology")
    assert _find_records(payload, rule_id="G-01", outcome="pass", check_id="G-01.level")


def test_G01_N_out_of_scope_microarray_halts_downstream(tmp_path):
    out_dir = tmp_path / "out"
    _, _, payload, prov = _run_fixture("F06", out_dir)
    assert payload["state"] == "incompatible"
    assert _find_records(payload, rule_id="G-01", outcome="blocked", check_id="G-01.technology")
    for downstream in ("G-03", "M-01", "M-03", "R-01", "R-02", "M-04"):
        assert not _find_records(payload, rule_id=downstream)
    assert not _m01_steps(prov)


def test_G01_E_need_fact_runs_evidence_without_resolving_scope(tmp_path):
    # Characterization (D5): organism undeclared gives G-01 NEED_FACT; independent
    # checks run (including R-01 candidate PASS), yet state stays requires_manual_review.
    spec = FIXTURE_BY_ID["F01"]
    fdir = FIXTURES_ROOT / spec["dir"]
    declared = {"technology": "RNA-seq", "level": "gene", "study": "StudyA"}
    out_dir = tmp_path / "out"
    run_intake(
        fdir / spec["matrix"],
        fdir / spec["metadata"],
        out_dir,
        declared=declared,
        metadata_id_column=spec["metadata_id_column"],
    )
    payload = json.loads((out_dir / "records.json").read_text(encoding="utf-8"))
    assert _find_records(payload, rule_id="G-01", outcome="need_fact", check_id="G-01.organism")
    assert _find_records(payload, rule_id="G-02", outcome="pass", check_id="G-02.parse")
    assert _find_records(payload, rule_id="G-03", outcome="pass", check_id="G-03.orientation")
    assert _find_records(payload, rule_id="M-01", outcome="pass", check_id="M-01.match")
    assert _find_records(payload, rule_id="M-03", outcome="pass", check_id="M-03.tier_a")
    assert _find_records(payload, rule_id="M-04", outcome="pass", check_id="M-04.none")
    assert _find_records(payload, rule_id="R-01", outcome="pass", check_id="R-01.candidate")
    assert (out_dir / "oriented_matrix.tsv").exists()
    assert (out_dir / "sample_matches.json").exists()
    assert (out_dir / "representation_evidence.json").exists()
    assert not _find_records(payload, rule_id="G-01", outcome="blocked")
    assert not _find_records(payload, rule_id="J-05")
    assert payload["state"] == "requires_manual_review"


# ----------------------------------------------------------- G-02 P / N / E
def test_G02_P_bom_csv_quoted_parsed_cleanly(tmp_path):
    _, _, payload, _ = _run_fixture("F02", tmp_path / "out")
    assert payload["state"] == "compatible"
    assert _find_records(payload, rule_id="G-02", outcome="pass", check_id="G-02.parse")
    assert (tmp_path / "out" / "parsed_matrix.tsv").exists()


def test_G02_N_binary_matrix_blocked_halts_downstream(tmp_path):
    _, _, payload, _ = _run_fixture("F04", tmp_path / "out")
    assert payload["state"] == "incompatible"
    assert _find_records(payload, rule_id="G-02", outcome="blocked", check_id="G-02.parse")
    assert not (tmp_path / "out" / "parsed_matrix.tsv").exists()


def test_G02_E_ragged_header_resolved_and_preserved(tmp_path):
    _, _, payload, _ = _run_fixture("F03", tmp_path / "out")
    assert payload["state"] == "compatible"
    assert _find_records(payload, rule_id="G-02", outcome="resolved", check_id="G-02.ragged_header")


# ----------------------------------------------------------- G-03 P / N / E
def test_G03_P_transposed_matrix_resolved_exact_values(tmp_path):
    out_dir = tmp_path / "out"
    _, _, payload, _ = _run_fixture("F10", out_dir)
    assert payload["state"] == "compatible"
    assert _find_records(payload, rule_id="G-03", outcome="resolved", check_id="G-03.orientation")
    text = (out_dir / "oriented_matrix.tsv").read_text(encoding="utf-8")
    assert "9007199254740993" in text


def test_G03_N_disagreeing_signals_stops_orientation_dependent_stages(tmp_path):
    out_dir = tmp_path / "out"
    _, _, payload, _ = _run_fixture("F12", out_dir)
    assert payload["state"] == "requires_manual_review"
    assert _find_records(payload, rule_id="G-03", outcome="need_fact")
    assert _find_records(payload, rule_id="M-03", outcome="pass")
    assert not _find_records(payload, rule_id="M-01")
    assert not _find_records(payload, rule_id="R-01")
    assert not _find_records(payload, rule_id="M-04")
    assert not (out_dir / "oriented_matrix.tsv").exists()


def test_G03_E_square_matrix_stops_downstream_but_keeps_m03(tmp_path):
    out_dir = tmp_path / "out"
    spec, fdir, payload, prov = _run_fixture("F11", out_dir)
    assert payload["state"] == "requires_manual_review"
    assert _find_records(payload, rule_id="G-03", outcome="need_fact")
    assert _find_records(payload, rule_id="M-03", outcome="pass")
    assert not _find_records(payload, rule_id="M-01")
    # ID validation still ran before orientation stopped the pipeline
    _assert_id_provenance(
        prov,
        id_col=spec["metadata_id_column"],
        expected_valid=True,
        expected_matching=False,
        out_dir=out_dir,
        metadata_path=fdir / spec["metadata"],
    )


# ----------------------------------------------------------- G-04 P / N / E
def test_G04_P_originals_byte_identical_after_intake(tmp_path):
    spec, fdir, payload, _ = _run_fixture("F01", tmp_path / "out")
    assert sha256_file(fdir / spec["matrix"]) == spec["file_hashes"][spec["matrix"]]
    assert sha256_file(fdir / spec["metadata"]) == spec["file_hashes"][spec["metadata"]]
    g04 = _find_records(payload, rule_id="G-04", outcome="pass")
    assert len(g04) == 2


def test_G04_N_unreadable_input_missing_file(tmp_path):
    spec = FIXTURE_BY_ID["F01"]
    fdir = FIXTURES_ROOT / spec["dir"]
    missing = tmp_path / "missing_dir" / "does_not_exist.tsv"
    out_dir = tmp_path / "out"
    run_intake(
        missing,
        fdir / spec["metadata"],
        out_dir,
        declared=dict(spec["declared"]),
        metadata_id_column=spec["metadata_id_column"],
    )
    payload = json.loads((out_dir / "records.json").read_text(encoding="utf-8"))
    assert payload["state"] == "incompatible"
    blocked = _find_records(payload, rule_id="G-04", outcome="blocked", check_id="G-04.verify_unchanged")
    assert len(blocked) == 1
    assert blocked[0]["scope"] == str(missing)
    assert blocked[0]["decision_basis"].startswith("input file unreadable")
    assert blocked[0]["evidence"]["stage"] == "S0"
    assert "expected_sha256" not in blocked[0]["evidence"]
    assert not _find_records(payload, rule_id="J-05")


def test_G04_N_unreadable_input_directory_path(tmp_path):
    spec = FIXTURE_BY_ID["F01"]
    fdir = FIXTURES_ROOT / spec["dir"]
    bad_dir = tmp_path / "dir_as_matrix"
    bad_dir.mkdir()
    out_dir = tmp_path / "out"
    run_intake(
        bad_dir,
        fdir / spec["metadata"],
        out_dir,
        declared=dict(spec["declared"]),
        metadata_id_column=spec["metadata_id_column"],
    )
    payload = json.loads((out_dir / "records.json").read_text(encoding="utf-8"))
    assert payload["state"] == "incompatible"
    blocked = _find_records(payload, rule_id="G-04", outcome="blocked", check_id="G-04.verify_unchanged")
    assert len(blocked) == 1
    rec = blocked[0]
    assert rec["scope"] == str(bad_dir)
    assert rec["decision_basis"].startswith("input file unreadable")
    assert rec["evidence"]["error_type"] in rec["decision_basis"]
    assert rec["evidence"]["stage"] == "S0"
    assert "expected_sha256" not in rec["evidence"]
    for later in ("G-02", "G-01", "G-03", "M-01", "M-03", "R-01", "M-04"):
        assert not _find_records(payload, rule_id=later)
    assert (out_dir / "records.json").exists()
    assert (out_dir / "provenance.json").exists()


def test_G04_N_unreadable_input_transient_sha256_failure(tmp_path, monkeypatch):
    import bionexus.cli as cli_mod

    spec = FIXTURE_BY_ID["F01"]
    fdir = FIXTURES_ROOT / spec["dir"]
    real_sha = cli_mod.sha256_file
    calls = {"n": 0}

    def flaky_sha(path):
        calls["n"] += 1
        if calls["n"] == 1:
            raise PermissionError("transient read error")
        return real_sha(path)

    monkeypatch.setattr(cli_mod, "sha256_file", flaky_sha)
    out_dir = tmp_path / "out"
    run_intake(
        fdir / spec["matrix"],
        fdir / spec["metadata"],
        out_dir,
        declared=dict(spec["declared"]),
        metadata_id_column=spec["metadata_id_column"],
    )
    payload = json.loads((out_dir / "records.json").read_text(encoding="utf-8"))
    blocked = _find_records(payload, rule_id="G-04", outcome="blocked", check_id="G-04.verify_unchanged")
    assert len(blocked) == 1
    assert blocked[0]["decision_basis"].startswith("input file unreadable")
    assert "hash differs" not in blocked[0]["decision_basis"]


@pytest.mark.skipif(
    os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="POSIX chmod 000 unreadable-file check is not reliable on Windows or as root",
)
def test_G04_N_unreadable_existing_file_chmod_000(tmp_path):
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    m = in_dir / "matrix.tsv"
    md = in_dir / "metadata.tsv"
    m.write_text("gene\tS1\nG1\t1\n", encoding="utf-8")
    md.write_text("sample_id\tcondition\ttissue\torganism\nS1\tctrl\tskin\thuman\n", encoding="utf-8")
    os.chmod(m, 0o000)
    try:
        out_dir = tmp_path / "out"
        run_intake(
            m,
            md,
            out_dir,
            declared=dict(FIXTURE_BY_ID["F01"]["declared"]),
            metadata_id_column="sample_id",
        )
        payload = json.loads((out_dir / "records.json").read_text(encoding="utf-8"))
        blocked = _find_records(payload, rule_id="G-04", outcome="blocked", check_id="G-04.verify_unchanged")
        assert len(blocked) == 1 and blocked[0]["evidence"]["stage"] == "S0"
    finally:
        os.chmod(m, 0o644)


def test_G04_E_identical_input_paths_do_not_bypass_downstream_as_compatible(tmp_path):
    """Identical Path for matrix and metadata must not trigger S0 early exit as compatible."""
    in_dir = tmp_path / "in"
    in_dir.mkdir()

    # 1. Binary NUL-byte file + out-of-scope declaration passed for both --matrix and --metadata
    bad_bin = in_dir / "bad.bin"
    bad_bin.write_bytes(b"\x00\x01\x02not_a_matrix")
    out_bin = tmp_path / "out_bin"
    rc_bin = main([
        "intake",
        "--matrix", str(bad_bin),
        "--metadata", str(bad_bin),
        "--metadata-id-column", "sample_id",
        "--declared", "organism=mouse", "technology=microarray",
        "--out", str(out_bin),
    ])
    assert rc_bin == 0
    payload_bin = json.loads((out_bin / "records.json").read_text(encoding="utf-8"))
    assert payload_bin["state"] == "incompatible"
    assert _find_records(payload_bin, rule_id="G-02", outcome="blocked", check_id="G-02.parse")

    # 2. Valid TSV matrix + out-of-scope declaration passed as identical Path
    tsv = in_dir / "matrix.tsv"
    tsv.write_text("gene\tS1\tS2\nG1\t10\t3\nG2\t0\t100\n", encoding="utf-8")
    out_scope = tmp_path / "out_scope"
    run_intake(
        tsv,
        tsv,
        out_scope,
        declared={"organism": "mouse", "technology": "microarray"},
        metadata_id_column="sample_id",
    )
    payload_scope = json.loads((out_scope / "records.json").read_text(encoding="utf-8"))
    assert payload_scope["state"] == "incompatible"
    assert _find_records(payload_scope, rule_id="G-02", outcome="pass", check_id="G-02.parse")
    assert _find_records(payload_scope, rule_id="G-01", outcome="blocked", check_id="G-01.organism")
    assert _find_records(payload_scope, rule_id="G-01", outcome="blocked", check_id="G-01.technology")

    # 3. Valid TSV matrix + in-scope declaration (no sample_id column) passed as identical Path
    out_inscope = tmp_path / "out_inscope"
    run_intake(
        tsv,
        tsv,
        out_inscope,
        declared=dict(FIXTURE_BY_ID["F01"]["declared"]),
        metadata_id_column="sample_id",
    )
    payload_inscope = json.loads((out_inscope / "records.json").read_text(encoding="utf-8"))
    assert payload_inscope["state"] == "requires_manual_review"
    assert _find_records(payload_inscope, rule_id="G-02", outcome="pass", check_id="G-02.parse")
    assert _find_records(payload_inscope, rule_id="M-01", outcome="need_fact", check_id="M-01.metadata_id_column")


def test_G04_E_out_dir_colliding_with_input_dir_refused(tmp_path):
    in_dir = tmp_path / "inputs"
    in_dir.mkdir()
    m = in_dir / "matrix.tsv"
    md = in_dir / "metadata.tsv"
    m.write_text("gene\tS1\tS2\nG1\t1\t2\nG2\t3\t4\n", encoding="utf-8")
    md.write_text("sample_id\tcondition\ttissue\torganism\nS1\tctrl\tskin\thuman\nS2\tcase\tskin\thuman\n", encoding="utf-8")
    before_m, before_md = sha256_file(m), sha256_file(md)
    # Containment error must take precedence over non-empty error
    with pytest.raises(ValueError, match="must not collide"):
        run_intake(
            m,
            md,
            in_dir,
            declared=dict(FIXTURE_BY_ID["F01"]["declared"]),
            metadata_id_column="sample_id",
        )
    assert sorted(p.name for p in in_dir.iterdir()) == ["matrix.tsv", "metadata.tsv"]
    assert sha256_file(m) == before_m and sha256_file(md) == before_md


# ----------------------------------------------------------- R-01 P / N / E
def test_R01_P_integer_counts_confirmed(tmp_path):
    _, _, payload, _ = _run_fixture("F01", tmp_path / "out")
    assert _find_records(payload, rule_id="R-01", outcome="pass")


def test_R01_N_declared_r1_with_non_integers_blocked(tmp_path):
    _, _, payload, _ = _run_fixture("F14", tmp_path / "out")
    assert payload["state"] == "incompatible"
    assert _find_records(payload, rule_id="R-01", outcome="blocked", check_id="R-01.declared_r1")


def test_R01_E_constant_sum_million_does_not_infer_cpm_or_enable_r03(tmp_path):
    out_dir = tmp_path / "out"
    _, _, payload, _ = _run_fixture("F15", out_dir)
    assert RuleRegistry().is_enabled("R-03") is False
    assert not _find_records(payload, rule_id="R-03")
    rep = json.loads((out_dir / "representation_evidence.json").read_text(encoding="utf-8"))
    assert rep["col_sums"] == [1000000, 1000000]
    rep_records = [r for r in payload["records"] if r["rule_id"] in {"R-01", "R-02", "R-03"}]
    text = json.dumps(rep).lower() + json.dumps(rep_records).lower()
    assert "cpm" not in text and "tpm" not in text and "rpkm" not in text


# ----------------------------------------------------------- R-02 P / N / E
def test_R02_P_declared_linear_passes(tmp_path):
    _, _, payload, _ = _run_fixture("F16", tmp_path / "out")
    assert payload["state"] == "compatible"
    assert _find_records(payload, rule_id="R-02", outcome="pass", check_id="R-02.declared_linear")


def test_R02_N_undeclared_non_integer_need_fact(tmp_path):
    _, _, payload, _ = _run_fixture("F13", tmp_path / "out")
    assert payload["state"] == "requires_manual_review"
    assert _find_records(payload, rule_id="R-02", outcome="need_fact", check_id="R-02.undeclared")


def test_R02_E_declared_linear_negatives_and_other_label_note(tmp_path):
    _, _, payload_neg, _ = _run_fixture("F18", tmp_path / "neg")
    assert _find_records(payload_neg, rule_id="R-02", outcome="need_fact", check_id="R-02.declared_linear")

    spec = FIXTURE_BY_ID["F18"]
    fdir = FIXTURES_ROOT / spec["dir"]
    declared = dict(spec["declared"], representation="log2")
    out2 = tmp_path / "log2"
    run_intake(
        fdir / spec["matrix"],
        fdir / spec["metadata"],
        out2,
        declared=declared,
        metadata_id_column=spec["metadata_id_column"],
    )
    payload_log2 = json.loads((out2 / "records.json").read_text(encoding="utf-8"))
    assert _find_records(payload_log2, rule_id="R-02", outcome="note", check_id="R-02.declared")
    assert not _find_records(payload_log2, rule_id="J-05")


# ----------------------------------------------------------- R-05 P / N / E
def test_R05_P_complete_annotation_universe_no_limitation(tmp_path):
    spec = FIXTURE_BY_ID["F01"]
    fdir = FIXTURES_ROOT / spec["dir"]
    out_dir = tmp_path / "out"
    run_intake(
        fdir / spec["matrix"],
        fdir / spec["metadata"],
        out_dir,
        declared=dict(spec["declared"]),
        metadata_id_column=spec["metadata_id_column"],
        annotation_genes=["G1", "G2", "G3", "G4"],
    )
    payload = json.loads((out_dir / "records.json").read_text(encoding="utf-8"))
    rep = json.loads((out_dir / "representation_evidence.json").read_text(encoding="utf-8"))
    assert payload["state"] == "compatible"
    assert rep["annotation_fraction"] == 1.0
    assert not _find_records(payload, rule_id="R-05", outcome="limitation")


def test_R05_N_subset_annotation_universe_limitation(tmp_path):
    _, _, payload, _ = _run_fixture("F21", tmp_path / "out")
    assert payload["state"] == "compatible_with_warnings"
    lim = _find_records(payload, rule_id="R-05", outcome="limitation")
    assert len(lim) == 1 and lim[0]["evidence"]["absent"] == 2


def test_R05_E_empty_annotation_universe_note_no_fraction(tmp_path):
    spec = FIXTURE_BY_ID["F01"]
    fdir = FIXTURES_ROOT / spec["dir"]
    out_dir = tmp_path / "out"
    run_intake(
        fdir / spec["matrix"],
        fdir / spec["metadata"],
        out_dir,
        declared=dict(spec["declared"]),
        metadata_id_column=spec["metadata_id_column"],
        annotation_genes=[],
    )
    payload = json.loads((out_dir / "records.json").read_text(encoding="utf-8"))
    rep = json.loads((out_dir / "representation_evidence.json").read_text(encoding="utf-8"))
    assert rep["annotation_fraction"] is None
    assert _find_records(payload, rule_id="R-05", outcome="note")


# ----------------------------------------------------------- R-06 P / N / E
def test_R06_P_complete_matrix_no_na_records(tmp_path):
    _, _, payload, _ = _run_fixture("F01", tmp_path / "out")
    assert not _find_records(payload, rule_id="R-06")


def test_R06_N_whole_sample_na_need_fact(tmp_path):
    _, _, payload, _ = _run_fixture("F20", tmp_path / "out")
    assert payload["state"] == "requires_manual_review"
    ws = _find_records(payload, rule_id="R-06", outcome="need_fact", check_id="R-06.whole_sample_na")
    assert ws and ws[0]["evidence"]["whole_sample_na"] == ["S2"]


def test_R06_E_partial_na_note_without_imputation(tmp_path):
    out_dir = tmp_path / "out"
    _, _, payload, _ = _run_fixture("F19", out_dir)
    assert payload["state"] == "compatible"
    assert _find_records(payload, rule_id="R-06", outcome="note", check_id="R-06.na_genes")
    rep = json.loads((out_dir / "representation_evidence.json").read_text(encoding="utf-8"))
    assert rep["na_genes"] == ["G2"]


# ----------------------------------------------------------- J-04 P / N / E
def test_J04_P_all_pass_yields_compatible(tmp_path):
    _, _, payload, _ = _run_fixture("F01", tmp_path / "out")
    assert payload["state"] == "compatible"


def test_J04_N_blocked_and_need_fact_precedence(tmp_path):
    _, _, blocked_payload, _ = _run_fixture("F14", tmp_path / "blocked")
    assert blocked_payload["state"] == "incompatible"
    _, _, nf_payload, _ = _run_fixture("F13", tmp_path / "nf")
    assert nf_payload["state"] == "requires_manual_review"


def test_J04_E_limitation_gives_compatible_with_warnings(tmp_path):
    _, _, payload, _ = _run_fixture("F21", tmp_path / "out")
    assert payload["state"] == "compatible_with_warnings"


# ----------------------------------------------------------- J-05 P / N / E
def test_J05_P_undefined_declared_key_emits_rule_gap_not_assessable(tmp_path):
    _, _, payload, _ = _run_fixture("F27", tmp_path / "out")
    assert payload["state"] == "requires_manual_review"
    gaps = _find_records(payload, rule_id="J-05", outcome="not_assessable", check_id="rule_gap")
    assert len(gaps) == 1
    assert gaps[0]["decision_basis"] == "rule gap: BioNexus cannot assess this case yet"
    assert "normalization_method" in gaps[0]["evidence"]["description"]


def test_J05_N_covered_case_emits_no_rule_gap(tmp_path):
    _, _, payload, _ = _run_fixture("F01", tmp_path / "out")
    assert not _find_records(payload, rule_id="J-05")


def test_J05_E_multiple_unknown_keys_and_programming_errors_not_converted(tmp_path):
    spec = FIXTURE_BY_ID["F01"]
    fdir = FIXTURES_ROOT / spec["dir"]
    declared = dict(spec["declared"], custom_alpha="1", custom_beta="2")
    out_dir = tmp_path / "out"
    run_intake(
        fdir / spec["matrix"],
        fdir / spec["metadata"],
        out_dir,
        declared=declared,
        metadata_id_column=spec["metadata_id_column"],
    )
    payload = json.loads((out_dir / "records.json").read_text(encoding="utf-8"))
    gaps = _find_records(payload, rule_id="J-05", outcome="not_assessable", check_id="rule_gap")
    assert len(gaps) == 2

    # Programming errors must NOT be swallowed or converted into RuleGap
    with pytest.raises((TypeError, AttributeError)):
        run_intake(
            fdir / spec["matrix"],
            fdir / spec["metadata"],
            tmp_path / "err",
            declared="not_a_dict",  # type: ignore[arg-type]
            metadata_id_column=spec["metadata_id_column"],
        )


# ----------------------------------------------------------- V-02 P / N / E
def test_V02_P_provenance_records_all_input_and_output_hashes_and_versions(tmp_path):
    out_dir = tmp_path / "out"
    spec, fdir, _, prov = _run_fixture("F01", out_dir)
    assert set(prov["software_versions"]) == {"bionexus", "python", "pandas", "numpy"}
    rules_logged = {s["rule_id"] for s in prov["steps"]}
    assert {"G-02", "G-03", "M-01", "R-01", "V-02"} <= rules_logged
    logged_outputs = {Path(o["path"]).name: o["sha256"] for s in prov["steps"] for o in s["outputs"]}
    for name in (
        "parsed_matrix.tsv",
        "oriented_matrix.tsv",
        "sample_matches.json",
        "representation_evidence.json",
        "records.json",
    ):
        assert logged_outputs[name] == sha256_file(out_dir / name)


def test_V02_N_failed_parse_logs_no_derived_matrix_step(tmp_path):
    out_dir = tmp_path / "out"
    _, _, _, prov = _run_fixture("F04", out_dir)
    step_rules = [s["rule_id"] for s in prov["steps"]]
    assert "G-02" not in step_rules
    assert "G-03" not in step_rules
    assert "V-02" in step_rules


def test_V02_E_provenance_roundtrips_strict_json(tmp_path):
    out_dir = tmp_path / "out"
    _run_fixture("F21", out_dir)
    text = (out_dir / "provenance.json").read_text(encoding="utf-8")
    loaded = json.loads(text)
    assert json.loads(json.dumps(loaded, allow_nan=False)) == loaded


# ---------------------------------------------------------- D1 CLI & API tests
def test_M01_N_cli_omitted_metadata_id_column_exits_2(tmp_path):
    spec = FIXTURE_BY_ID["F01"]
    fdir = FIXTURES_ROOT / spec["dir"]
    parent_exists = tmp_path / "existing_parent"
    parent_exists.mkdir()
    out_under_parent = parent_exists / "out"
    out_new = tmp_path / "nonexistent_parent" / "out"
    for out_p in (out_under_parent, out_new):
        rc = main([
            "intake",
            "--matrix", str(fdir / spec["matrix"]),
            "--metadata", str(fdir / spec["metadata"]),
            "--out", str(out_p),
        ])
        assert rc == 2
        assert not out_p.exists()


def test_M01_E_cli_omitted_metadata_id_column_plus_bad_arg_exits_2(tmp_path):
    spec = FIXTURE_BY_ID["F01"]
    fdir = FIXTURES_ROOT / spec["dir"]
    out_p = tmp_path / "out"
    rc = main([
        "intake",
        "--matrix", str(fdir / spec["matrix"]),
        "--metadata", str(fdir / spec["metadata"]),
        "--declared", "malformed_no_equals",
        "--out", str(out_p),
    ])
    assert rc == 2
    assert not out_p.exists()


def test_M01_E_cli_empty_string_metadata_id_column_completes_absent(tmp_path):
    spec = FIXTURE_BY_ID["F01"]
    fdir = FIXTURES_ROOT / spec["dir"]
    out_p = tmp_path / "out"
    rc = main([
        "intake",
        "--matrix", str(fdir / spec["matrix"]),
        "--metadata", str(fdir / spec["metadata"]),
        "--metadata-id-column", "",
        "--declared", *(f"{k}={v}" for k, v in spec["declared"].items()),
        "--out", str(out_p),
    ])
    assert rc == 0
    payload = json.loads((out_p / "records.json").read_text(encoding="utf-8"))
    rec = _find_records(payload, rule_id="M-01", outcome="need_fact", check_id="M-01.metadata_id_column")
    assert len(rec) == 1 and rec[0]["evidence"]["reason"] == "absent"
    assert not _find_records(payload, check_id="M-03.sample_id")


def test_M01_N_run_intake_requires_str_metadata_id_column(tmp_path):
    spec = FIXTURE_BY_ID["F01"]
    fdir = FIXTURES_ROOT / spec["dir"]
    out_p = tmp_path / "out"
    with pytest.raises(TypeError):
        run_intake(
            fdir / spec["matrix"],
            fdir / spec["metadata"],
            out_p,
            declared=dict(spec["declared"]),
        )  # type: ignore[call-arg]
    assert not out_p.exists()
    for bad in (None, 123):
        with pytest.raises(TypeError):
            run_intake(
                fdir / spec["matrix"],
                fdir / spec["metadata"],
                out_p,
                declared=dict(spec["declared"]),
                metadata_id_column=bad,  # type: ignore[arg-type]
            )
        assert not out_p.exists()


def test_M01_P_metadata_id_leading_zeros_preserved_as_text(tmp_path):
    m, md = _write_case(
        tmp_path,
        "leading_zeros",
        "sample_id\tcondition\ttissue\torganism\n007\tctrl\tskin\thuman\n008\tcase\tskin\thuman\n",
        "gene\t007\t008\nG1\t10\t3\nG2\t0\t100\nG3\t5\t0\nG4\t1\t2\n",
    )
    out_dir = tmp_path / "out"
    run_intake(
        m,
        md,
        out_dir,
        declared=dict(FIXTURE_BY_ID["F01"]["declared"]),
        metadata_id_column="sample_id",
    )
    matches = json.loads((out_dir / "sample_matches.json").read_text(encoding="utf-8"))
    assert [(x["matrix_id"], x["sample_id"]) for x in matches["matches"]] == [
        ("007", "007"),
        ("008", "008"),
    ]


# ------------------------------------------- D6 / D6a Record-routing & Provenance
def _assert_id_provenance(
    prov: dict,
    *,
    id_col: str,
    expected_valid: bool,
    expected_matching: bool,
    out_dir: Path,
    metadata_path: Path,
    oriented_path: Path | None = None,
):
    val_steps = _m01_steps(prov, "metadata_id_validation_and_duplicate_classification")
    assert len(val_steps) == 1
    assert val_steps[0]["parameters"] == {
        "operation": "metadata_id_validation_and_duplicate_classification",
        "metadata_id_column": id_col,
        "id_column_valid": expected_valid,
    }
    assert val_steps[0]["inputs"] == [str(metadata_path)]
    assert val_steps[0]["outputs"] == []

    match_steps = _m01_steps(prov, "sample_matching")
    matches_path = out_dir / "sample_matches.json"
    expected_oriented = (
        oriented_path if oriented_path is not None else out_dir / "oriented_matrix.tsv"
    )
    if expected_matching:
        assert len(match_steps) == 1
        assert match_steps[0]["inputs"] == [str(expected_oriented), str(metadata_path)]
        assert len(match_steps[0]["outputs"]) == 1
        assert Path(match_steps[0]["outputs"][0]["path"]).name == "sample_matches.json"
        assert match_steps[0]["outputs"][0]["sha256"] == sha256_file(matches_path)
        assert matches_path.exists()
    else:
        assert match_steps == []
        assert not matches_path.exists()


def test_M01_N_record_routing_absent_column_and_f24(tmp_path):
    # F24 + explicit absent column ("patient")
    out_f24 = tmp_path / "out_f24"
    spec_f24, fdir_f24, payload_f24, prov_f24 = _run_fixture("F24", out_f24)
    assert not _find_records(payload_f24, check_id="M-03.sample_id")
    assert not _find_records(payload_f24, check_id="M-01.match")
    assert not _find_records(payload_f24, check_id="M-01.unmatched")
    assert not _find_records(payload_f24, check_id="M-01.duplicate_metadata_ids")
    assert not _find_records(payload_f24, check_id="M-01.duplicate_metadata_rows")
    col_rec = _find_records(payload_f24, check_id="M-01.metadata_id_column")
    assert len(col_rec) == 1 and col_rec[0]["evidence"]["reason"] == "absent"
    assert _find_records(payload_f24, rule_id="M-03", outcome="pass", check_id="M-03.tier_a")
    _assert_id_provenance(
        prov_f24,
        id_col="sample_id",
        expected_valid=False,
        expected_matching=False,
        out_dir=out_f24,
        metadata_path=fdir_f24 / spec_f24["metadata"],
    )

    # Absent "patient" via CLI main -> exit 0
    m, md = _write_case(
        tmp_path,
        "absent_patient",
        "sample_id\tcondition\ttissue\torganism\nS1\tctrl\tskin\thuman\nS2\tcase\tskin\thuman\n",
    )
    out2 = tmp_path / "out_patient"
    rc = main([
        "intake", "--matrix", str(m), "--metadata", str(md),
        "--metadata-id-column", "patient",
        "--declared", *(f"{k}={v}" for k, v in FIXTURE_BY_ID["F01"]["declared"].items()),
        "--out", str(out2),
    ])
    assert rc == 0
    p2 = json.loads((out2 / "records.json").read_text(encoding="utf-8"))
    prov2 = json.loads((out2 / "provenance.json").read_text(encoding="utf-8"))
    c2 = _find_records(p2, check_id="M-01.metadata_id_column")
    assert len(c2) == 1 and c2[0]["evidence"]["reason"] == "absent"
    assert not _find_records(p2, check_id="M-03.sample_id")
    _assert_id_provenance(
        prov2,
        id_col="patient",
        expected_valid=False,
        expected_matching=False,
        out_dir=out2,
        metadata_path=md,
    )


def test_M01_N_record_routing_duplicated_column_label(tmp_path):
    m, md = _write_case(
        tmp_path,
        "dup_col",
        "sample_id\tsample_id\tcondition\ttissue\torganism\nS1\tS2\tctrl\tskin\thuman\nS2\tS1\tcase\tskin\thuman\n",
    )
    out_dir = tmp_path / "out"
    rc = main([
        "intake", "--matrix", str(m), "--metadata", str(md),
        "--metadata-id-column", "sample_id",
        "--declared", *(f"{k}={v}" for k, v in FIXTURE_BY_ID["F01"]["declared"].items()),
        "--out", str(out_dir),
    ])
    assert rc == 0
    payload = json.loads((out_dir / "records.json").read_text(encoding="utf-8"))
    prov = json.loads((out_dir / "provenance.json").read_text(encoding="utf-8"))
    col_rec = _find_records(payload, check_id="M-01.metadata_id_column")
    assert len(col_rec) == 1 and col_rec[0]["evidence"]["reason"] == "duplicated_column"
    assert col_rec[0]["evidence"]["column_positions"] == [0, 1]
    assert col_rec[0]["evidence"]["n_rows"] == 2
    assert not _find_records(payload, check_id="M-01.duplicate_metadata_rows")
    assert not _find_records(payload, check_id="M-01.duplicate_metadata_ids")
    assert not _find_records(payload, check_id="M-03.sample_id")
    assert _find_records(payload, rule_id="M-03", outcome="pass", check_id="M-03.tier_a")
    _assert_id_provenance(
        prov,
        id_col="sample_id",
        expected_valid=False,
        expected_matching=False,
        out_dir=out_dir,
        metadata_path=md,
    )


def test_M01_E_record_routing_single_blank_id(tmp_path):
    m, md = _write_case(
        tmp_path,
        "single_blank",
        "sample_id\tcondition\ttissue\torganism\n\tctrl\tskin\thuman\nS2\tcase\tskin\thuman\n",
    )
    out_dir = tmp_path / "out"
    rc = main([
        "intake", "--matrix", str(m), "--metadata", str(md),
        "--metadata-id-column", "sample_id",
        "--declared", *(f"{k}={v}" for k, v in FIXTURE_BY_ID["F01"]["declared"].items()),
        "--out", str(out_dir),
    ])
    assert rc == 0
    payload = json.loads((out_dir / "records.json").read_text(encoding="utf-8"))
    prov = json.loads((out_dir / "provenance.json").read_text(encoding="utf-8"))
    col_rec = _find_records(payload, check_id="M-01.metadata_id_column")
    assert len(col_rec) == 1 and col_rec[0]["evidence"]["reason"] == "blank_ids"
    assert col_rec[0]["evidence"]["n_blank"] == 1
    assert col_rec[0]["evidence"]["n_rows"] == 2
    assert not _find_records(payload, check_id="M-01.duplicate_metadata_rows")
    assert not _find_records(payload, check_id="M-01.duplicate_metadata_ids")
    assert not _find_records(payload, check_id="M-03.sample_id")
    assert _find_records(payload, rule_id="M-03", outcome="pass", check_id="M-03.tier_a")
    _assert_id_provenance(
        prov,
        id_col="sample_id",
        expected_valid=False,
        expected_matching=False,
        out_dir=out_dir,
        metadata_path=md,
    )


def test_M01_E_record_routing_repeated_whitespace_and_blank_ids(tmp_path):
    # Note (D6c declined limitation): do not assert blank-group wording beyond blank: true
    # and the sibling M-01.metadata_id_column record.
    m, md = _write_case(
        tmp_path,
        "ws_blank",
        "sample_id\tcondition\ttissue\torganism\n   \tctrl\tskin\thuman\n   \tctrl\tskin\thuman\n",
    )
    out_ws = tmp_path / "out_ws"
    rc = main([
        "intake", "--matrix", str(m), "--metadata", str(md),
        "--metadata-id-column", "sample_id",
        "--declared", *(f"{k}={v}" for k, v in FIXTURE_BY_ID["F01"]["declared"].items()),
        "--out", str(out_ws),
    ])
    assert rc == 0
    p_ws = json.loads((out_ws / "records.json").read_text(encoding="utf-8"))
    prov_ws = json.loads((out_ws / "provenance.json").read_text(encoding="utf-8"))
    col_ws = _find_records(p_ws, check_id="M-01.metadata_id_column")
    row_ws = _find_records(p_ws, check_id="M-01.duplicate_metadata_rows")
    assert len(col_ws) == 1 and col_ws[0]["evidence"]["reason"] == "blank_ids"
    assert len(row_ws) == 1 and row_ws[0]["evidence"]["blank"] is True
    assert row_ws[0]["evidence"]["all_rows_retained"] is True
    assert not _find_records(p_ws, check_id="M-01.duplicate_metadata_ids")
    assert not _find_records(p_ws, check_id="M-03.sample_id")
    _assert_id_provenance(
        prov_ws,
        id_col="sample_id",
        expected_valid=False,
        expected_matching=False,
        out_dir=out_ws,
        metadata_path=md,
    )

    # F31 repeated empty-string IDs
    out_f31 = tmp_path / "out_f31"
    spec_f31, fdir_f31, p_f31, prov_f31 = _run_fixture("F31", out_f31)
    col_31 = _find_records(p_f31, check_id="M-01.metadata_id_column")
    row_31 = _find_records(p_f31, check_id="M-01.duplicate_metadata_rows")
    assert len(col_31) == 1 and col_31[0]["evidence"]["reason"] == "blank_ids"
    assert col_31[0]["evidence"]["n_blank"] >= 2
    assert len(row_31) == 1 and row_31[0]["evidence"]["blank"] is True and row_31[0]["evidence"]["id"] == ""
    assert row_31[0]["evidence"]["all_rows_retained"] is True
    assert not _find_records(p_f31, check_id="M-01.duplicate_metadata_ids")
    assert not _find_records(p_f31, check_id="M-03.sample_id")
    assert _find_records(p_f31, rule_id="M-03", outcome="pass", check_id="M-03.tier_a")
    _assert_id_provenance(
        prov_f31,
        id_col="sample_id",
        expected_valid=False,
        expected_matching=False,
        out_dir=out_f31,
        metadata_path=fdir_f31 / spec_f31["metadata"],
    )


def test_M01_N_record_routing_repeated_nonblank_identical_and_conflicting(tmp_path):
    # F29: repeated non-blank identical
    out_f29 = tmp_path / "out_f29"
    spec_f29, fdir_f29, p29, prov29 = _run_fixture("F29", out_f29)
    assert not _find_records(p29, check_id="M-01.metadata_id_column")
    assert not _find_records(p29, check_id="M-03.sample_id")
    r29 = _find_records(p29, check_id="M-01.duplicate_metadata_rows")
    assert len(r29) == 1
    assert r29[0]["evidence"]["blank"] is False
    assert r29[0]["evidence"]["classification"] == "identical"
    assert r29[0]["evidence"]["all_rows_retained"] is True
    assert _find_records(p29, check_id="M-01.duplicate_metadata_ids", outcome="need_fact")
    _assert_id_provenance(
        prov29,
        id_col="sample_id",
        expected_valid=True,
        expected_matching=True,
        out_dir=out_f29,
        metadata_path=fdir_f29 / spec_f29["metadata"],
        oriented_path=out_f29 / "oriented_matrix.tsv",
    )

    # F30: repeated non-blank conflicting
    out_f30 = tmp_path / "out_f30"
    spec_f30, fdir_f30, p30, prov30 = _run_fixture("F30", out_f30)
    assert not _find_records(p30, check_id="M-01.metadata_id_column")
    assert not _find_records(p30, check_id="M-03.sample_id")
    r30 = _find_records(p30, check_id="M-01.duplicate_metadata_rows")
    assert len(r30) == 1
    assert r30[0]["evidence"]["blank"] is False
    assert r30[0]["evidence"]["classification"] == "conflicting"
    assert r30[0]["evidence"]["all_rows_retained"] is True
    assert [d["field"] for d in r30[0]["evidence"]["differing_fields"]] == ["condition"]
    assert _find_records(p30, check_id="M-01.duplicate_metadata_ids", outcome="need_fact")
    _assert_id_provenance(
        prov30,
        id_col="sample_id",
        expected_valid=True,
        expected_matching=True,
        out_dir=out_f30,
        metadata_path=fdir_f30 / spec_f30["metadata"],
        oriented_path=out_f30 / "oriented_matrix.tsv",
    )


def test_M01_E_record_routing_repeated_nonblank_plus_one_blank(tmp_path):
    m, md = _write_case(
        tmp_path,
        "mixed_nonblank_blank",
        "sample_id\tcondition\ttissue\torganism\nS1\tctrl\tskin\thuman\nS1\tctrl\tskin\thuman\n\tcase\tskin\thuman\n",
    )
    out_dir = tmp_path / "out"
    rc = main([
        "intake", "--matrix", str(m), "--metadata", str(md),
        "--metadata-id-column", "sample_id",
        "--declared", *(f"{k}={v}" for k, v in FIXTURE_BY_ID["F01"]["declared"].items()),
        "--out", str(out_dir),
    ])
    assert rc == 0
    payload = json.loads((out_dir / "records.json").read_text(encoding="utf-8"))
    prov = json.loads((out_dir / "provenance.json").read_text(encoding="utf-8"))
    col_rec = _find_records(payload, check_id="M-01.metadata_id_column")
    row_rec = _find_records(payload, check_id="M-01.duplicate_metadata_rows")
    assert len(col_rec) == 1 and col_rec[0]["evidence"]["reason"] == "blank_ids"
    assert len(row_rec) == 1 and row_rec[0]["evidence"]["id"] == "S1" and row_rec[0]["evidence"]["blank"] is False
    assert row_rec[0]["evidence"]["all_rows_retained"] is True
    assert not _find_records(payload, check_id="M-01.duplicate_metadata_ids")
    assert not _find_records(payload, check_id="M-03.sample_id")
    assert _find_records(payload, rule_id="M-03", outcome="pass", check_id="M-03.tier_a")
    _assert_id_provenance(
        prov,
        id_col="sample_id",
        expected_valid=False,
        expected_matching=False,
        out_dir=out_dir,
        metadata_path=md,
    )


def test_M01_P_alternate_id_column_gsm_succeeds(tmp_path):
    # F28 + case-4 check: sample_id absent, gsm valid -> no M-03.sample_id, matching succeeds
    out_dir = tmp_path / "out"
    spec_f28, fdir_f28, payload, prov = _run_fixture("F28", out_dir)
    assert payload["state"] == "compatible"
    assert not _find_records(payload, check_id="M-03.sample_id")
    assert not _find_records(payload, check_id="M-01.metadata_id_column")
    assert _find_records(payload, check_id="M-01.match", outcome="pass")
    _assert_id_provenance(
        prov,
        id_col="gsm",
        expected_valid=True,
        expected_matching=True,
        out_dir=out_dir,
        metadata_path=fdir_f28 / spec_f28["metadata"],
        oriented_path=out_dir / "oriented_matrix.tsv",
    )


# ----------------------------------------------------------- D3 / M2 Output Dir
def test_G04_N_nonempty_output_dir_refused(tmp_path):
    spec = FIXTURE_BY_ID["F01"]
    fdir = FIXTURES_ROOT / spec["dir"]

    # Regular file in out_dir
    out1 = tmp_path / "out_regular"
    out1.mkdir()
    keep = out1 / "existing.txt"
    keep.write_text("precious", encoding="utf-8")
    before = sha256_file(keep)
    with pytest.raises(ValueError, match="not empty"):
        run_intake(
            fdir / spec["matrix"],
            fdir / spec["metadata"],
            out1,
            declared=dict(spec["declared"]),
            metadata_id_column="sample_id",
        )
    assert sha256_file(keep) == before
    assert os.listdir(out1) == ["existing.txt"]
    rc = main([
        "intake",
        "--matrix", str(fdir / spec["matrix"]),
        "--metadata", str(fdir / spec["metadata"]),
        "--metadata-id-column", "sample_id",
        "--out", str(out1),
    ])
    assert rc == 1
    assert os.listdir(out1) == ["existing.txt"]

    # Hidden file only (.keep)
    out2 = tmp_path / "out_hidden"
    out2.mkdir()
    (out2 / ".keep").write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="not empty"):
        run_intake(
            fdir / spec["matrix"],
            fdir / spec["metadata"],
            out2,
            declared=dict(spec["declared"]),
            metadata_id_column="sample_id",
        )
    assert os.listdir(out2) == [".keep"]

    # Subfolder only
    out3 = tmp_path / "out_sub"
    (out3 / "sub").mkdir(parents=True)
    with pytest.raises(ValueError, match="not empty"):
        run_intake(
            fdir / spec["matrix"],
            fdir / spec["metadata"],
            out3,
            declared=dict(spec["declared"]),
            metadata_id_column="sample_id",
        )
    assert os.listdir(out3) == ["sub"]


def test_G04_P_existing_empty_output_dir_accepted(tmp_path):
    spec = FIXTURE_BY_ID["F01"]
    fdir = FIXTURES_ROOT / spec["dir"]
    empty_dir = tmp_path / "empty_out"
    empty_dir.mkdir()
    res = run_intake(
        fdir / spec["matrix"],
        fdir / spec["metadata"],
        empty_dir,
        declared=dict(spec["declared"]),
        metadata_id_column="sample_id",
    )
    assert res.state is State.COMPATIBLE
    assert (empty_dir / "records.json").exists()
    assert (empty_dir / "provenance.json").exists()


def test_G04_E_dangling_symlink_output_path_refused(tmp_path):
    spec = FIXTURE_BY_ID["F01"]
    fdir = FIXTURES_ROOT / spec["dir"]
    link = tmp_path / "dangling_out"
    try:
        link.symlink_to(tmp_path / "does_not_exist_target")
    except OSError as exc:
        pytest.skip(f"symlinks not supported in this environment: {exc}")
    with pytest.raises(ValueError):
        run_intake(
            fdir / spec["matrix"],
            fdir / spec["metadata"],
            link,
            declared=dict(spec["declared"]),
            metadata_id_column="sample_id",
        )


@pytest.mark.skipif(
    os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="POSIX chmod 000 unlistable dir check is not reliable on Windows or as root",
)
def test_G04_E_unlistable_output_dir_returns_1(tmp_path):
    spec = FIXTURE_BY_ID["F01"]
    fdir = FIXTURES_ROOT / spec["dir"]
    out_dir = tmp_path / "unlistable"
    out_dir.mkdir()
    os.chmod(out_dir, 0o000)
    try:
        rc = main([
            "intake",
            "--matrix", str(fdir / spec["matrix"]),
            "--metadata", str(fdir / spec["metadata"]),
            "--metadata-id-column", "sample_id",
            "--out", str(out_dir),
        ])
        assert rc == 1
    finally:
        os.chmod(out_dir, 0o755)


def test_V02_E_stale_outputs_not_logged_in_provenance(tmp_path, monkeypatch):
    import bionexus.cli as cli_mod

    out_dir = tmp_path / "stale_out"
    out_dir.mkdir()
    (out_dir / "parsed_matrix.tsv").write_text("stale\t1\n", encoding="utf-8")
    (out_dir / "oriented_matrix.tsv").write_text("stale\t2\n", encoding="utf-8")
    (out_dir / "sample_matches.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(cli_mod, "_validate_out_dir", lambda p, _inputs: p)
    spec = FIXTURE_BY_ID["F04"]  # parse blocked
    fdir = FIXTURES_ROOT / spec["dir"]
    run_intake(
        fdir / spec["matrix"],
        fdir / spec["metadata"],
        out_dir,
        declared=dict(spec["declared"]),
        metadata_id_column=spec["metadata_id_column"],
    )
    prov = json.loads((out_dir / "provenance.json").read_text(encoding="utf-8"))
    assert [s["rule_id"] for s in prov["steps"]] == ["V-02"]
    assert [Path(o["path"]).name for s in prov["steps"] for o in s["outputs"]] == ["records.json"]


@pytest.mark.parametrize("fid", ["F01", "F04", "F06", "F11", "F24"])
def test_V02_P_output_dir_files_match_provenance_invariant(fid, tmp_path):
    out_dir = tmp_path / "out"
    _, _, _, prov = _run_fixture(fid, out_dir)
    actual_names = {p.name for p in out_dir.iterdir()}
    prov_names = {Path(o["path"]).name for s in prov["steps"] for o in s["outputs"]}
    assert actual_names == prov_names | {"provenance.json"}


# ---------------------------------------------- CLI / 1-col / char / AC8
def test_cli_subprocess_intake_exit_zero_across_scientific_states(tmp_path):
    for fid in ("F01", "F06", "F27", "F28"):
        spec = FIXTURE_BY_ID[fid]
        fdir = FIXTURES_ROOT / spec["dir"]
        out_dir = tmp_path / fid
        cmd = [
            sys.executable, "-m", "bionexus.cli", "intake",
            "--matrix", str(fdir / spec["matrix"]),
            "--metadata", str(fdir / spec["metadata"]),
            "--metadata-id-column", spec["metadata_id_column"],
            "--out", str(out_dir),
        ]
        if spec["declared"]:
            cmd.append("--declared")
            cmd.extend(f"{k}={v}" for k, v in spec["declared"].items())
        proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        payload = json.loads((out_dir / "records.json").read_text(encoding="utf-8"))
        assert payload["state"] == spec["expected_state"]
        assert (out_dir / "provenance.json").exists()
        if fid == "F06":
            lines = [ln for ln in proc.stdout.strip().splitlines() if ln.strip()]
            assert len(lines) == 1 and "out of V1 scope" in lines[0]


def test_cli_nonzero_exit_on_invalid_args_and_malformed_declared(tmp_path):
    spec = FIXTURE_BY_ID["F01"]
    fdir = FIXTURES_ROOT / spec["dir"]
    # Missing required --metadata
    assert main([
        "intake",
        "--matrix", str(fdir / spec["matrix"]),
        "--metadata-id-column", "sample_id",
        "--out", str(tmp_path / "o1"),
    ]) != 0
    # Malformed --declared entry without '='
    assert main([
        "intake",
        "--matrix", str(fdir / spec["matrix"]),
        "--metadata", str(fdir / spec["metadata"]),
        "--metadata-id-column", "sample_id",
        "--declared", "not_key_value",
        "--out", str(tmp_path / "o2"),
    ]) != 0
    # Duplicate --declared key
    assert main([
        "intake",
        "--matrix", str(fdir / spec["matrix"]),
        "--metadata", str(fdir / spec["metadata"]),
        "--metadata-id-column", "sample_id",
        "--declared", "organism=human", "organism=mouse",
        "--out", str(tmp_path / "o3"),
    ]) != 0
    # Unapproved CLI flag rejected
    assert main([
        "intake",
        "--matrix", str(fdir / spec["matrix"]),
        "--metadata", str(fdir / spec["metadata"]),
        "--metadata-id-column", "sample_id",
        "--annotation-genes", "foo.txt",
        "--out", str(tmp_path / "o4"),
    ]) != 0


def test_cli_nonzero_exit_on_output_collision_or_file_path(tmp_path):
    spec = FIXTURE_BY_ID["F01"]
    fdir = FIXTURES_ROOT / spec["dir"]
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    m = in_dir / "matrix.tsv"
    md = in_dir / "metadata.tsv"
    m.write_bytes((fdir / spec["matrix"]).read_bytes())
    md.write_bytes((fdir / spec["metadata"]).read_bytes())
    rc = main([
        "intake",
        "--matrix", str(m),
        "--metadata", str(md),
        "--metadata-id-column", "sample_id",
        "--out", str(in_dir),
    ])
    assert rc == 1
    existing_file = tmp_path / "not_a_dir"
    existing_file.write_text("x", encoding="utf-8")
    rc2 = main([
        "intake",
        "--matrix", str(m),
        "--metadata", str(md),
        "--metadata-id-column", "sample_id",
        "--out", str(existing_file),
    ])
    assert rc2 == 1


def test_single_column_metadata_csv_reader_reaches_m01_and_m03(tmp_path):
    m = tmp_path / "in" / "matrix.tsv"
    md = tmp_path / "in" / "metadata.tsv"
    m.parent.mkdir()
    m.write_text("gene\tS1\tS2\nG1\t10\t3\nG2\t0\t100\nG3\t5\t0\nG4\t1\t2\n", encoding="utf-8")
    # Complete text parsed via io.StringIO + csv.reader (with blank row & quoted field)
    md.write_text('\ufeffsample_id\n\n"S1"\nS2\n', encoding="utf-8")
    out1 = tmp_path / "out1"
    run_intake(
        m, md, out1,
        declared=dict(FIXTURE_BY_ID["F01"]["declared"]),
        metadata_id_column="sample_id",
    )
    p1 = json.loads((out1 / "records.json").read_text(encoding="utf-8"))
    assert _find_records(p1, rule_id="M-01", outcome="pass", check_id="M-01.match")
    for field in ("condition", "tissue", "organism"):
        assert _find_records(p1, rule_id="M-03", outcome="need_fact", check_id=f"M-03.{field}")

    # Header-only 1-column metadata -> G-02 BLOCKED
    md_hdr = tmp_path / "in" / "meta_hdr.tsv"
    md_hdr.write_text("sample_id\n", encoding="utf-8")
    out2 = tmp_path / "out2"
    run_intake(
        m, md_hdr, out2,
        declared=dict(FIXTURE_BY_ID["F01"]["declared"]),
        metadata_id_column="sample_id",
    )
    p2 = json.loads((out2 / "records.json").read_text(encoding="utf-8"))
    assert _find_records(p2, rule_id="G-02", outcome="blocked", check_id="G-02.parse")
    assert p2["state"] == "incompatible"

    # Unclosed quote in 1-column metadata -> G-02 NOT_ASSESSABLE
    md_bad = tmp_path / "in" / "meta_bad.tsv"
    md_bad.write_text('sample_id\n"S1\nS2\n', encoding="utf-8")
    out3 = tmp_path / "out3"
    run_intake(
        m, md_bad, out3,
        declared=dict(FIXTURE_BY_ID["F01"]["declared"]),
        metadata_id_column="sample_id",
    )
    p3 = json.loads((out3 / "records.json").read_text(encoding="utf-8"))
    assert _find_records(p3, rule_id="G-02", outcome="not_assessable", check_id="G-02.parse")
    assert p3["state"] == "requires_manual_review"


@pytest.mark.parametrize("bad_bytes", [b"", b"\xff\xfe\x00\x01"], ids=["empty", "non_utf8"])
def test_characterization_metadata_parse_failure(tmp_path, bad_bytes):
    """Characterization test (D5: no authoritative U3 text).

    Documents current runner behavior when the matrix parses cleanly but metadata
    parsing fails: no exception, main returns 0, metadata gets G-02.parse BLOCKED,
    M-01/M-03 metadata checks and M-01 provenance steps do not run, and matrix-only
    stages (G-03, R-01, M-04) still run, yielding combined state incompatible.
    """
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    m = in_dir / "matrix.tsv"
    md = in_dir / "metadata.tsv"
    m.write_text("gene\tS1\tS2\nG1\t10\t3\nG2\t0\t100\nG3\t5\t0\nG4\t1\t2\n", encoding="utf-8")
    md.write_bytes(bad_bytes)
    out_dir = tmp_path / "out"
    rc = main([
        "intake",
        "--matrix", str(m),
        "--metadata", str(md),
        "--metadata-id-column", "sample_id",
        "--declared", *(f"{k}={v}" for k, v in FIXTURE_BY_ID["F01"]["declared"].items()),
        "--out", str(out_dir),
    ])
    assert rc == 0
    payload = json.loads((out_dir / "records.json").read_text(encoding="utf-8"))
    prov = json.loads((out_dir / "provenance.json").read_text(encoding="utf-8"))
    assert payload["state"] == "incompatible"
    assert [r for r in _find_records(payload, rule_id="G-02", outcome="blocked", check_id="G-02.parse") if r["scope"] == str(md)]
    assert not _find_records(payload, check_id="M-01.metadata_id_column")
    assert not _find_records(payload, rule_id="M-01")
    assert not _find_records(payload, rule_id="M-03")
    assert not _m01_steps(prov)
    assert _find_records(payload, rule_id="G-03", outcome="pass")
    assert _find_records(payload, rule_id="R-01", outcome="pass")
    assert _find_records(payload, rule_id="M-04", outcome="pass")


def test_coverage_report_script_ac8():
    proc = subprocess.run(
        [sys.executable, "scripts/coverage_report.py", "--json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads(proc.stdout)
    assert len(report["m1_implemented"]) == 15
    assert len(report["not_scheduled_in_M1"]) == 10
    for rule_id, counts in report["m1_implemented"].items():
        assert counts["P"] >= 1, rule_id
        assert counts["N"] >= 1, rule_id
        assert counts["E"] >= 1, rule_id
