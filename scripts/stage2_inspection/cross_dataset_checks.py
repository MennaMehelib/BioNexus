"""Cross-dataset identifier and sample checks among Development datasets only."""
import gzip
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from geo_common import DERIVED_DIR, RAW_DIR  # noqa
from profiling import parse_series_matrix  # noqa

a3 = pd.read_csv(os.path.join(RAW_DIR, "GSE54456/suppl/GSE54456_RPKM_samples.txt.gz"), sep="\t", index_col=0)
a6 = pd.read_csv(os.path.join(DERIVED_DIR, "GSE67785/DERIVED_assembled_count.tsv.gz"), sep="\t", index_col=0)
s3, s6 = set(a3.index), set(a6.index)
print("A3 symbols", len(s3), "A6 symbols", len(s6), "shared", len(s3 & s6),
      "A3-only", len(s3 - s6), "A6-only", len(s6 - s3))
print("A3-only examples", sorted(s3 - s6)[:25])
print("A6-only examples", sorted(s6 - s3)[:25])
up3 = {x.upper() for x in s3}
up6 = {x.upper() for x in s6}
print("shared after uppercase", len(up3 & up6))

# Probe sets A1 vs A2 vs A4
probes = {}
for acc in ("GSE13355", "GSE30999", "GSE41663"):
    _, _, t = parse_series_matrix(os.path.join(RAW_DIR, acc, "matrix", f"{acc}_series_matrix.txt.gz"))
    probes[acc] = list(t["ID_REF"])
print("A1==A2 probe list (order)", probes["GSE13355"] == probes["GSE30999"],
      "A1==A4", probes["GSE13355"] == probes["GSE41663"],
      "sets equal", set(probes["GSE13355"]) == set(probes["GSE30999"]) == set(probes["GSE41663"]))

# A3 duplicated-value columns? (detect identical samples)
c = np.corrcoef(np.log1p(a3.values.T))
np.fill_diagonal(c, 0)
print("A3 max inter-sample corr (log1p RPKM)", c.max().round(4))
