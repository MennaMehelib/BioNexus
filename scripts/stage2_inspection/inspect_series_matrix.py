"""Inspect a GEO series matrix file (read-only). Usage: python inspect_series_matrix.py GSExxxx"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from geo_common import DERIVED_DIR, RAW_DIR, guard  # noqa
from profiling import parse_series_matrix, profile_numeric, summarize_sample_meta  # noqa

acc = sys.argv[1]
guard(acc)
path = os.path.join(RAW_DIR, acc, "matrix", f"{acc}_series_matrix.txt.gz")
series, smeta, table = parse_series_matrix(path)
out_dir = os.path.join(DERIVED_DIR, acc)
os.makedirs(out_dir, exist_ok=True)

report = {"source_file": os.path.relpath(path), "series": series,
          "n_sample_meta_records": int(len(smeta)),
          "sample_meta_summary": summarize_sample_meta(smeta)}
if table is not None and len(table):
    id_col = table.columns[0]
    sample_cols = list(table.columns[1:])
    report["table_header_first_col"] = id_col
    report["table_shape_incl_id_col"] = list(table.shape)
    report["profile"] = profile_numeric(table, id_col, sample_cols)
    gsm_meta = smeta.get("!Sample_geo_accession")
    if gsm_meta is not None:
        a, b = set(sample_cols), set(gsm_meta)
        report["matrix_cols_not_in_meta"] = sorted(a - b)
        report["meta_gsm_not_in_matrix"] = sorted(b - a)
        report["col_order_equals_meta_order"] = list(sample_cols) == list(gsm_meta)
    # per-sample distribution summary (for normalization evidence)
    X = table[sample_cols].apply(lambda s: s.astype(float)).to_numpy()
    q = np.nanquantile(X, [0.05, 0.5, 0.95], axis=0)
    report["per_sample_q05_range"] = [float(q[0].min()), float(q[0].max())]
    report["per_sample_median_range"] = [float(q[1].min()), float(q[1].max())]
    report["per_sample_q95_range"] = [float(q[2].min()), float(q[2].max())]
else:
    report["table"] = "EMPTY (no expression table in series matrix)"

smeta.to_csv(os.path.join(out_dir, "sample_metadata_from_series_matrix.tsv"), sep="\t", index=False)
with open(os.path.join(out_dir, "series_matrix_profile.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=1, default=str)
print(json.dumps(report, indent=1, default=str)[:20000])
