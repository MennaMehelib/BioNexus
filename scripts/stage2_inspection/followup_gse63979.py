"""A5 (GSE63979) follow-up: library size by group, ID overlap with A1/A3 (development only)."""
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from geo_common import RAW_DIR  # noqa
from profiling import parse_series_matrix  # noqa

N = pd.read_csv(os.path.join(RAW_DIR, "GSE63979/suppl/GSE63979_ReadCount_42samples.txt.gz"), sep="\t")
_, m, _ = parse_series_matrix(os.path.join(RAW_DIR, "GSE63979/matrix/GSE63979_series_matrix.txt.gz"))
key = m["!Sample_title"].str.rsplit("_", n=1).str[0]
grp = dict(zip(key, m["!Sample_characteristics_ch1"].str.replace("tissue type: ", "")))
gsm = dict(zip(key, m["!Sample_geo_accession"]))
lib = N.sum(0)
df = pd.DataFrame({"lib_M": (lib / 1e6).round(2), "group": [grp[c] for c in lib.index], "gsm": [gsm[c] for c in lib.index]})
print(df.groupby("group")["lib_M"].describe().round(2).to_string())
print("lowest libs:\n", df.sort_values("lib_M").head(5).to_string())
print("detected genes (count>0) per sample min/median/max:", (N > 0).sum(0).min(), int((N > 0).sum(0).median()), (N > 0).sum(0).max())

_, m1, _ = parse_series_matrix(os.path.join(RAW_DIR, "GSE13355/matrix/GSE13355_series_matrix.txt.gz"))
a1 = {}
for t in m1["!Sample_title"]:
    i, g = re.match(r"Individual_(\d+)_(\w\w)_", t).groups()
    a1.setdefault(i, set()).add(g)
num = lambda x: re.sub(r"^\D+", "", x)
hits = [(c, grp[c], sorted(a1[num(c)])) for c in lib.index if num(c) in a1]
print("A5 IDs whose numeric part matches an A1 individual:", len(hits))
for h in hits:
    print("  ", h)
_, m3, _ = parse_series_matrix(os.path.join(RAW_DIR, "GSE54456/matrix/GSE54456_series_matrix.txt.gz"))
t3 = set(m3["!Sample_title"])
print("A5 non-uninvolved IDs present in A3:", [c for c in lib.index if grp[c] != "Uninvolved skin" and c in t3])
