"""Provenance and hashing (G-04 input integrity, V-02 provenance per derived file)."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from pathlib import Path

from .records import AssessmentRecord, Outcome

_CHUNK = 1024 * 1024  # read size only; has no scientific meaning


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def make_read_only(path) -> None:
    """Set the read-only permission; file content is not touched."""
    mode = os.stat(path).st_mode
    os.chmod(path, mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))


def _software_versions() -> dict:
    import numpy
    import pandas

    from . import __version__

    return {
        "bionexus": __version__,
        "python": sys.version.split()[0],
        "pandas": pandas.__version__,
        "numpy": numpy.__version__,
    }


class ProvenanceLog:
    def __init__(self):
        self._versions = _software_versions()
        self._inputs: list[dict] = []
        self._steps: list[dict] = []

    def add_input(self, path) -> None:
        self._inputs.append({"path": str(path), "sha256": sha256_file(path)})

    def add_step(
        self,
        rule_id: str,
        rule_version: str,
        parameters: dict,
        inputs: list[str],
        outputs: list[str],
    ) -> None:
        self._steps.append(
            {
                "rule_id": rule_id,
                "rule_version": rule_version,
                "parameters": parameters,
                "inputs": [str(p) for p in inputs],
                "outputs": [
                    {
                        "path": str(p),
                        "sha256": sha256_file(p),
                        "software_versions": dict(self._versions),
                    }
                    for p in outputs
                ],
            }
        )

    def to_dict(self) -> dict:
        return {
            "software_versions": dict(self._versions),
            "inputs": list(self._inputs),
            "steps": list(self._steps),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def write(self, path) -> None:
        Path(path).write_text(self.to_json(), encoding="utf-8")


def verify_unchanged(path, expected_hash: str) -> AssessmentRecord:
    """G-04: pass if the file hash equals expected_hash, otherwise blocked."""
    evidence = {"path": str(path), "expected_sha256": expected_hash}
    try:
        actual = sha256_file(path)
    except OSError as exc:
        evidence["error"] = f"{type(exc).__name__}: {exc}"
        outcome, basis = Outcome.BLOCKED, "input file unreadable"
    else:
        evidence["actual_sha256"] = actual
        if actual == expected_hash:
            outcome, basis = Outcome.PASS, "hash identical to expected"
        else:
            outcome, basis = Outcome.BLOCKED, "hash differs from expected: file changed"
    return AssessmentRecord(
        check_id="G-04.verify_unchanged",
        rule_id="G-04",
        rule_version="0.1",
        scope=str(path),
        outcome=outcome,
        evidence=evidence,
        confidence=None,
        limitations=(),
        decision_basis=basis,
    )
