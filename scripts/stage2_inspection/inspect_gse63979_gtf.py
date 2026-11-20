"""Inspect GSE63979 assembly GTF (read-only): attributes, feature-type annotation availability, ID coverage."""
import collections as C
import gzip
import json
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from geo_common import DERIVED_DIR, RAW_DIR  # noqa

base = os.path.join(RAW_DIR, "GSE63979", "suppl")
keys, feat, src = C.Counter(), C.Counter(), C.Counter()
genes = C.defaultdict(lambda: {"tx": set(), "exons": set(), "chrom": None, "strand": set(), "start": 1e18, "end": 0})
pat = re.compile(r'(\S+) "([^"]*)"')
for line in gzip.open(os.path.join(base, "GSE63979_assembly.filtered.gtf.gz"), "rt"):
    if line.startswith("#"):
        continue
    f = line.rstrip("\n").split("\t")
    feat[f[2]] += 1
    src[f[1]] += 1
    attrs = dict(pat.findall(f[8]))
    keys.update(attrs.keys())
    g = genes[attrs["gene_id"]]
    g["chrom"] = f[0]
    g["strand"].add(f[6])
    g["tx"].add(attrs.get("transcript_id"))
    g["start"] = min(g["start"], int(f[3]))
    g["end"] = max(g["end"], int(f[4]))
    if f[2] == "exon":
        g["exons"].add((f[3], f[4]))

ids = set(pd.read_csv(os.path.join(base, "GSE63979_ReadCount_42samples.txt.gz"), sep="\t").index)
res = {
    "feature_types": dict(feat), "sources": dict(src), "attribute_keys": dict(keys),
    "n_genes_in_gtf": len(genes),
    "chrom_counts": dict(sorted(C.Counter(g["chrom"] for g in genes.values()).items())),
    "mono_exonic_genes": sum(1 for g in genes.values() if len(g["exons"]) == 1),
    "genes_unstranded": sum(1 for g in genes.values() if "." in g["strand"]),
    "transcripts_per_gene": dict(sorted(C.Counter(min(len(g["tx"]), 10) for g in genes.values()).items())),
    "matrix_ids_in_gtf": len(ids & set(genes)),
    "matrix_ids_not_in_gtf": len(ids - set(genes)),
    "gtf_ids_not_in_matrix": len(set(genes) - ids),
}
os.makedirs(os.path.join(DERIVED_DIR, "GSE63979"), exist_ok=True)
with open(os.path.join(DERIVED_DIR, "GSE63979", "gtf_profile.json"), "w") as fh:
    json.dump(res, fh, indent=1)
print(json.dumps(res, indent=1))
