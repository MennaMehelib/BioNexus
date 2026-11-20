"""Validate existing Stage 2 raw + derived artifacts (read-only for data/raw).

Checks:
  1. Every raw file recorded in download_log.jsonl still exists, has the same size and SHA-256.
  2. Raw files are read-only (immutability safeguard).
  3. Raw files present on disk but NOT in the download log are reported (provenance gap).
  4. Derived JSON profiles parse; derived sample-metadata TSVs have the expected record counts.
  5. GSE67785 derived assembled matrices are re-built IN MEMORY from the original RAW tar and
     compared cell-by-cell with the stored derived copies (nothing is overwritten).
  6. SHA-256 of every derived artifact is recorded (derived-artifact manifest).

Output: data/derived/development/_validation/stage2_artifact_validation.json
Inspection tooling only - NOT BioNexus product code.
"""
import gzip
import hashlib
import io
import json
import os
import re
import stat
import sys
import tarfile
from datetime import datetime, timezone

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from geo_common import DERIVED_DIR, FORBIDDEN, PROV_LOG, RAW_DIR, ROOT  # noqa

PLATFORM_DIR = os.path.join(ROOT, "data", "raw", "platforms")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(p):
    return os.path.relpath(p, ROOT).replace("\\", "/")


out = {"generated_utc": datetime.now(timezone.utc).isoformat(), "python": sys.version.split()[0],
       "pandas": pd.__version__, "numpy": np.__version__}

# Safety: no forbidden accession anywhere under data/
hits = []
for base, dirs, files in os.walk(os.path.join(ROOT, "data")):
    for n in dirs + files:
        if any(f in n for f in FORBIDDEN):
            hits.append(os.path.join(base, n))
out["unseen_set_paths_found"] = [rel(h) for h in hits]

# 1-2. Raw integrity vs download log
records = [json.loads(l) for l in open(PROV_LOG, encoding="utf-8") if l.strip()]
raw_checks, logged = [], set()
for r in records:
    p = os.path.join(ROOT, r["local_path"])
    logged.add(os.path.normcase(os.path.abspath(p)))
    e = {"file": rel(p), "exists": os.path.exists(p)}
    if e["exists"]:
        e["size_match"] = os.path.getsize(p) == r["size_bytes"]
        e["sha256_match"] = sha256(p) == r["sha256"]
        e["read_only"] = not (os.stat(p).st_mode & stat.S_IWRITE)
    raw_checks.append(e)
out["raw_files_checked"] = len(raw_checks)
out["raw_all_ok"] = all(c.get("exists") and c.get("size_match") and c.get("sha256_match") for c in raw_checks)
out["raw_all_read_only"] = all(c.get("read_only") for c in raw_checks)
out["raw_checks"] = raw_checks

# 3. Raw files not in log
unlogged = []
for root_dir in (RAW_DIR, PLATFORM_DIR):
    for base, _, files in os.walk(root_dir):
        for n in files:
            p = os.path.join(base, n)
            if n in ("download_log.jsonl", "ftp_listing.json"):
                continue
            if os.path.normcase(os.path.abspath(p)) not in logged:
                unlogged.append({"file": rel(p), "size": os.path.getsize(p), "sha256": sha256(p),
                                 "read_only": not (os.stat(p).st_mode & stat.S_IWRITE)})
out["raw_files_not_in_download_log"] = unlogged

# 4. Derived profile / metadata consistency
derived = {}
for acc in sorted(os.listdir(DERIVED_DIR)):
    d = os.path.join(DERIVED_DIR, acc)
    if not os.path.isdir(d) or acc.startswith("_"):
        continue
    info = {}
    prof_p = os.path.join(d, "series_matrix_profile.json")
    meta_p = os.path.join(d, "sample_metadata_from_series_matrix.tsv")
    if os.path.exists(prof_p):
        prof = json.load(open(prof_p, encoding="utf-8"))
        info["profile_parses"] = True
        info["n_sample_meta_records_in_profile"] = prof.get("n_sample_meta_records")
        info["has_expression_table"] = "profile" in prof
    if os.path.exists(meta_p):
        m = pd.read_csv(meta_p, sep="\t", dtype=str, keep_default_na=False)
        info["metadata_tsv_rows"] = len(m)
        info["metadata_rows_match_profile"] = len(m) == info.get("n_sample_meta_records_in_profile")
        info["metadata_gsm_unique"] = bool(m["!Sample_geo_accession"].is_unique)
    for f in os.listdir(d):
        if f.endswith(".json") and f != "series_matrix_profile.json":
            json.load(open(os.path.join(d, f), encoding="utf-8"))
            info.setdefault("other_json_parse_ok", []).append(f)
    derived[acc] = info
out["derived_checks"] = derived

# 5. GSE67785 derived matrices vs in-memory re-assembly from original tar
acc = "GSE67785"
tar = tarfile.open(os.path.join(RAW_DIR, acc, "suppl", f"{acc}_RAW.tar"))
frames = {}
for mem in tar.getmembers():
    raw = gzip.decompress(tar.extractfile(mem).read()).decode("utf-8", "replace")
    frames[re.match(r"(GSM\d+)", mem.name).group(1)] = pd.read_csv(
        io.StringIO(raw), sep=" ", quotechar='"', dtype=str, keep_default_na=False)
recon = {}
for col in ("FPKM", "count"):
    first = next(iter(frames.values()))
    mat = pd.DataFrame({g: df[col].astype(float).values for g, df in frames.items()}, index=first["gene_symbol"])
    stored = pd.read_csv(os.path.join(DERIVED_DIR, acc, f"DERIVED_assembled_{col}.tsv.gz"), sep="\t", index_col=0)
    same_shape = stored.shape == mat.shape
    recon[col] = {
        "stored_shape": list(stored.shape), "rebuilt_shape": list(mat.shape),
        "same_index": same_shape and list(stored.index) == list(mat.index),
        "same_columns": same_shape and list(stored.columns) == list(mat.columns),
        "max_abs_diff": float(np.nanmax(np.abs(stored.values - mat.values))) if same_shape else None,
        "exact_equal": bool(same_shape and np.array_equal(stored.values, mat.values)),
    }
out["gse67785_derived_rebuild_check"] = recon

# 6. Derived manifest
manifest = []
for base, _, files in os.walk(DERIVED_DIR):
    if "_validation" in base:
        continue
    for n in sorted(files):
        p = os.path.join(base, n)
        manifest.append({"file": rel(p), "size": os.path.getsize(p), "sha256": sha256(p)})
out["derived_manifest"] = manifest

vd = os.path.join(DERIVED_DIR, "_validation")
os.makedirs(vd, exist_ok=True)
with open(os.path.join(vd, "stage2_artifact_validation.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1)
summary = {k: out[k] for k in ("unseen_set_paths_found", "raw_files_checked", "raw_all_ok", "raw_all_read_only",
                               "raw_files_not_in_download_log", "derived_checks", "gse67785_derived_rebuild_check")}
print(json.dumps(summary, indent=1))
