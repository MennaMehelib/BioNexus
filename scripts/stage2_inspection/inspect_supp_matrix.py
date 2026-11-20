"""Inspect a delimited supplementary expression matrix (read-only).
Usage: python inspect_supp_matrix.py GSExxxx relative/path/in/raw [sep]
"""
import json
import os
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from geo_common import DERIVED_DIR, RAW_DIR, guard  # noqa
from profiling import profile_numeric  # noqa

acc, rel = sys.argv[1], sys.argv[2]
sep = sys.argv[3] if len(sys.argv) > 3 else "\t"
guard(acc)
path = os.path.join(RAW_DIR, acc, rel)
df = pd.read_csv(path, sep=sep, dtype=str, keep_default_na=False, low_memory=False)
df.columns = [c if c.strip() else "<EMPTY_HEADER>" for c in df.columns]
id_col = df.columns[0]
num_like = []
non_num = []
for c in df.columns[1:]:
    conv = pd.to_numeric(df[c].replace("", np.nan), errors="coerce")
    (num_like if conv.notna().mean() > 0.95 else non_num).append(c)
res = {"file": rel, "shape_raw": list(df.shape), "header_first_col": id_col,
       "numeric_cols": len(num_like), "non_numeric_cols": non_num,
       "empty_string_cells": int((df[num_like] == "").sum().sum())}
num = df[[id_col] + num_like].replace("", np.nan)
res["profile"] = profile_numeric(num, id_col, num_like)
ids = df[id_col]
# Gene-symbol hazards (evidence only)
res["ids_date_like_excel"] = sorted(set(ids[ids.str.match(r"^\d{1,2}-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)$", case=False)]))[:30]
res["ids_lowercase_present"] = int(ids.str.match(r"^[a-z]").sum())
res["ids_with_whitespace"] = int((ids != ids.str.strip()).sum())
dups = ids[ids.duplicated(keep=False)]
res["duplicate_id_examples"] = dups.value_counts().head(15).to_dict()
V = num[num_like].apply(pd.to_numeric, errors="coerce").to_numpy(float)
# decimal precision evidence
flat = V[np.isfinite(V)]
for d in (0, 1, 2, 3, 4):
    res[f"frac_exact_at_{d}dp"] = float(np.isclose(flat * 10**d, np.round(flat * 10**d)).mean())
res["per_sample_sum_quantiles"] = np.quantile(np.nansum(V, 0), [0, .25, .5, .75, 1]).tolist()
lv = np.log2(flat[flat > 0])
res["log2_of_positive_quantiles"] = np.quantile(lv, [0, .05, .25, .5, .75, .95, 1]).tolist() if lv.size else None
res["frac_values_lt_1_among_positive"] = float((flat[flat > 0] < 1).mean())
out = os.path.join(DERIVED_DIR, acc)
os.makedirs(out, exist_ok=True)
name = re.sub(r"[^\w.]+", "_", os.path.basename(rel))
with open(os.path.join(out, f"profile_{name}.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, default=str)
print(json.dumps(res, indent=1, default=str))
