"""Inspect GSE67785 per-sample files directly from the RAW tar (no extraction, read-only).
Writes derived assembled matrices (counts, FPKM) to data/derived for analysis only."""
import collections as C
import gzip
import io
import json
import os
import re
import sys
import tarfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from geo_common import DERIVED_DIR, RAW_DIR  # noqa
from profiling import parse_series_matrix, profile_numeric  # noqa

acc = "GSE67785"
tar = tarfile.open(os.path.join(RAW_DIR, acc, "suppl", f"{acc}_RAW.tar"))
out_dir = os.path.join(DERIVED_DIR, acc)
os.makedirs(out_dir, exist_ok=True)
res = {"members": []}
frames = {}
headers = C.Counter()
for m in tar.getmembers():
    raw = gzip.decompress(tar.extractfile(m).read()).decode("utf-8", "replace")
    lines = raw.split("\n")
    if not res["members"]:
        res["first_member_head"] = lines[:6]
        res["first_member_tail"] = lines[-4:]
    df = pd.read_csv(io.StringIO(raw), sep=" ", quotechar='"', dtype=str, keep_default_na=False)
    headers[tuple(df.columns)] += 1
    res["members"].append({"name": m.name, "rows": len(df), "cols": list(df.columns)})
    frames[m.name] = df
res["distinct_headers"] = [list(h) + [n] for h, n in headers.items()]

# assemble (derived) - only if headers identical
cols = list(next(iter(frames.values())).columns)
id_col = cols[0]
same_ids = len({tuple(df[id_col]) for df in frames.values()}) == 1
res["identical_feature_order_across_files"] = same_ids
gsm = {n: re.match(r"(GSM\d+)", n).group(1) for n in frames}
for c in cols[1:]:
    mat = pd.DataFrame({gsm[n]: df[c].values for n, df in frames.items()})
    mat.insert(0, id_col, next(iter(frames.values()))[id_col].values)
    numeric_ok = pd.to_numeric(mat.iloc[:, 1].replace("", np.nan), errors="coerce").notna().mean()
    if numeric_ok > 0.9:
        res[f"profile_{c}"] = profile_numeric(mat, id_col, list(mat.columns[1:]))
        V = mat.iloc[:, 1:].apply(pd.to_numeric, errors="coerce").to_numpy(float)
        flat = V[np.isfinite(V)]
        pos = flat[flat > 0]
        res[f"extra_{c}"] = {
            "log2_positive_quantiles": np.quantile(np.log2(pos), [0, .05, .5, .95, 1]).tolist() if pos.size else None,
            "frac_lt_1_among_positive": float((pos < 1).mean()) if pos.size else None,
            "col_sums": np.quantile(np.nansum(V, 0), [0, .5, 1]).tolist(),
        }
        mat.to_csv(os.path.join(out_dir, f"DERIVED_assembled_{re.sub(r'\\W+', '_', c)}.tsv.gz"),
                   sep="\t", index=False, compression="gzip")
    else:
        res[f"non_numeric_column_{c}"] = mat.iloc[:5, 1].tolist()

ids = next(iter(frames.values()))[id_col]
res["id_pattern_counts"] = dict(C.Counter(re.sub(r"\d+", "9", x) for x in ids).most_common(15))
res["n_ids"] = int(len(ids))
res["n_unique_ids"] = int(ids.nunique())
res["dup_id_examples"] = ids[ids.duplicated(keep=False)].value_counts().head(10).to_dict()
res["special_rows"] = ids[ids.str.startswith("__")].tolist()

with open(os.path.join(out_dir, "raw_tar_profile.json"), "w", encoding="utf-8") as fh:
    json.dump(res, fh, indent=1, default=str)
print(json.dumps({k: v for k, v in res.items() if k != "members"}, indent=1, default=str))
print("member rows:", C.Counter(m["rows"] for m in res["members"]))
