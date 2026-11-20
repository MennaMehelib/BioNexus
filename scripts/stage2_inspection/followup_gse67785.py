"""Follow-up checks for GSE67785 (reads derived assembled matrices + original series matrix)."""
import collections as C
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from geo_common import DERIVED_DIR, RAW_DIR  # noqa
from profiling import classify_id, parse_series_matrix  # noqa

d = os.path.join(DERIVED_DIR, "GSE67785")
F = pd.read_csv(os.path.join(d, "DERIVED_assembled_FPKM.tsv.gz"), sep="\t", index_col=0)
N = pd.read_csv(os.path.join(d, "DERIVED_assembled_count.tsv.gz"), sep="\t", index_col=0)
print("other IDs:", [i for i in F.index if classify_id(i) == "other"])
pos = F.values[F.values > 0]
print("FPKM positive < 1e-10:", int((pos < 1e-10).sum()), "smallest:", np.sort(pos)[:5])
print("FPKM > 1e5 count:", int((F.values > 1e5).sum()), F.stack().sort_values().tail(5).to_dict())
print("count==0 & FPKM>0 cells:", int(((N.values == 0) & (F.values > 0)).sum()),
      "count>0 & FPKM==0 cells:", int(((N.values > 0) & (F.values == 0)).sum()))
print("genes all-zero counts but some FPKM>0:", int(((N == 0).all(axis=1) & (F > 0).any(axis=1)).sum()))
print("genes all-zero FPKM but some count>0:", int(((F == 0).all(axis=1) & (N > 0).any(axis=1)).sum()))
r = [np.corrcoef(np.log1p(F[c]), np.log1p(N[c]))[0, 1] for c in F.columns]
print("per-sample log1p corr FPKM vs count: min %.3f median %.3f" % (min(r), np.median(r)))
ids = F.index.to_series()
cls = C.Counter()
for i in ids:
    if i.startswith("MIR"): cls["MIR*"] += 1
    elif i.startswith("SNORD") or i.startswith("SNORA"): cls["SNO*"] += 1
    elif i.startswith("LINC"): cls["LINC*"] += 1
    elif i.startswith("LOC"): cls["LOC*"] += 1
    elif "-AS" in i: cls["*-AS*"] += 1
    elif i.startswith("RNU") or i.startswith("RN7S"): cls["RNU/RN7S*"] += 1
    else: cls["other_symbol"] += 1
print("A6 symbol-prefix classes (heuristic):", dict(cls))
# expression of MIR features
mir = ids[ids.str.match(r"^MIR\d")]
print("MIR features with any count>0:", int((N.loc[mir] > 0).any(axis=1).sum()), "of", len(mir))

s, m, _ = parse_series_matrix(os.path.join(RAW_DIR, "GSE67785", "matrix", "GSE67785_series_matrix.txt.gz"))
for k in ["!Series_title", "!Series_summary", "!Series_overall_design", "!Series_platform_id", "!Series_pubmed_id", "!Series_contact_institute", "!Series_relation"]:
    print(k, s.get(k))
cols = ["!Sample_geo_accession", "!Sample_title", "!Sample_characteristics_ch1", "!Sample_characteristics_ch1.2", "!Sample_characteristics_ch1.3"]
print(m[cols].to_string())
print("matrix col order == meta order:", list(F.columns) == list(m["!Sample_geo_accession"]))
lib = N.sum(0)
grp = dict(zip(m["!Sample_geo_accession"], m["!Sample_characteristics_ch1"]))
print(pd.DataFrame({"lib": lib, "grp": [grp[c] for c in lib.index]}).groupby("grp")["lib"].describe())
