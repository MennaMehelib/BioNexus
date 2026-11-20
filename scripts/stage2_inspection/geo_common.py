"""
Stage 2 inspection helpers (NOT BioNexus product code).

Purpose: list and download GEO files for the Development Set ONLY,
recording provenance (URL, size, sha256, timestamp).

SAFETY: A hard allowlist prevents any access to Validation or Unseen accessions.
The Unseen Set (U1-U3) is locked until Stage 8 per docs/datasets/dataset_selection.md.
"""
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone

ALLOWED = {"GSE13355", "GSE30999", "GSE54456", "GSE41663", "GSE63979", "GSE67785"}
FORBIDDEN = {"GSE52471", "GSE121212", "GSE205748"}  # Unseen set - never touch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW_DIR = os.path.join(ROOT, "data", "raw", "development")
DERIVED_DIR = os.path.join(ROOT, "data", "derived", "development")
PROV_LOG = os.path.join(RAW_DIR, "download_log.jsonl")


def guard(acc: str) -> None:
    if acc in FORBIDDEN:
        sys.exit(f"REFUSED: {acc} is in the LOCKED UNSEEN SET.")
    if acc not in ALLOWED:
        sys.exit(f"REFUSED: {acc} is not in the Stage 2 Development allowlist.")


def series_base(acc: str) -> str:
    guard(acc)
    num = acc[3:]
    stub = "GSE" + (num[:-3] if len(num) > 3 else "") + "nnn"
    return f"https://ftp.ncbi.nlm.nih.gov/geo/series/{stub}/{acc}/"


def list_dir(url: str):
    with urllib.request.urlopen(url, timeout=60) as r:
        html = r.read().decode("utf-8", "replace")
    out = []
    for m in re.finditer(r'<a href="([^"?/][^"]*)">[^<]*</a>\s+(\S+ \S+)\s+(\S+)', html):
        out.append((m.group(1), m.group(2), m.group(3)))
    return out


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(acc: str, url: str, subdir: str = "") -> str:
    guard(acc)
    if acc not in url:
        sys.exit(f"REFUSED: URL {url} does not belong to {acc}")
    dest_dir = os.path.join(RAW_DIR, acc, subdir)
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, url.rsplit("/", 1)[-1])
    if os.path.exists(dest):
        print("exists:", dest)
        return dest
    tmp = dest + ".part"
    import subprocess
    for attempt in range(5):
        rc = subprocess.call(["curl.exe", "-s", "-S", "-L", "-C", "-", "--retry", "3",
                              "-o", tmp, url])
        if rc == 0:
            break
        print("retry", attempt, "rc", rc)
        time.sleep(5)
    else:
        sys.exit(f"FAILED {url}")
    os.replace(tmp, dest)
    rec = {
        "accession": acc,
        "url": url,
        "local_path": os.path.relpath(dest, ROOT),
        "size_bytes": os.path.getsize(dest),
        "sha256": sha256(dest),
        "downloaded_utc": datetime.now(timezone.utc).isoformat(),
    }
    with open(PROV_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    print("downloaded:", rec)
    return dest
