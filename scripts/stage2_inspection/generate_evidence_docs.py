"""
generate_evidence_docs.py
Generates the comprehensive Stage 2 Evidence Documents:
1. docs/stage2/datasets/GSE13355_evidence.md
2. docs/stage2/datasets/GSE30999_evidence.md
3. docs/stage2/datasets/GSE41663_evidence.md
4. docs/stage2/datasets/GSE54456_evidence.md
5. docs/stage2/datasets/GSE63979_evidence.md
6. docs/stage2/datasets/GSE67785_evidence.md
7. docs/stage2/STAGE2_SCIENTIFIC_EVIDENCE_REPORT.md
8. docs/stage2/SUPERVISOR_PRESENTATION_SUMMARY.md
"""

import os
import json
from pathlib import Path

BASE_DIR = Path("d:/BioNexus")
STAGE2_DIR = BASE_DIR / "docs" / "stage2"
DATASETS_DOC_DIR = STAGE2_DIR / "datasets"
DATASETS_DOC_DIR.mkdir(parents=True, exist_ok=True)

# Load evidence summary
with open(BASE_DIR / "data/derived/development/stage2_evidence_summary.json", "r") as f:
    evidence = json.load(f)

print("Loaded evidence summary with keys:", list(evidence["datasets"].keys()))
