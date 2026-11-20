"""Residual Stage 2 checks that were not yet recorded as artifacts (Development Set only, read-only).

  A4 GSE41663 : patient count vs. series design text, provenance link to GSE11903, per-sample negatives.
  A3 GSE54456 : feature-class heuristic (same rules as A6), sample-order vs metadata.
  A6 GSE67785 : age/sex parsed from sample titles; group balance.
  GPL570      : probe->symbol coverage against A3/A6 symbol sets (harmonization feasibility evidence).
  Cross       : GSM overlap among GPL570 datasets; ID-classifier behaviour on A5 custom IDs.

Output: data/derived/development/_cross_dataset/residual_checks.json
Inspection tooling only - NOT BioNexus product code.
"""
import collections as C
import gzip
import io
import json
import os
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from geo_common import DERIVED_DIR, RAW_DIR, ROOT  # noqa
from profiling import classify_id, parse_series_matrix  # noqa


def sm(acc):
    return parse_series_matrix(os.path.join(RAW_DIR, acc, "matrix", f"{acc}_series_matrix.txt.gz"))


def feature_class(sym):
    """Heuristic symbol-prefix class. EVIDENCE ONLY - not an authoritative biotype."""
    s = str(sym)
    if re.match(r"^MIR\d", s): return "MIR*"
    if re.match(r"^SNOR[AD]", s) or s.startswith("SCARNA"): return "SNO*/SCARNA*"
    if re.match(r"^LINC\d", s): return "LINC*"
    if re.search(r"-AS\d*$", s): return "*-AS*"
    if s.startswith("LOC"): return "LOC*"
    if re.match(r"^C\d+orf\d+", s) or re.match(r"^C[XY]orf\d+", s): return "CXorfY"
    if re.match(r"^(RNU|RN7S|RNA5|RNY)", s): return "RNU/RN7S*"
    return "other_symbol"


res = {}

# ---- A4 GSE41663
_, m4, t4 = sm("GSE41663")
title = m4["!Sample_title"]
pid = title.str.extract(r"^PsOEt-(\d+)-")[0]
desc = m4["!Sample_description"]
letters = desc.str.extract(r"^([A-Z]+)_")[0]
src_gsm = desc.str.extract(r"\((GSM\d+)\)")[0]
X4 = t4.iloc[:, 1:].to_numpy(float)
res["A4_GSE41663"] = {
    "n_samples": int(len(m4)),
    "distinct_patient_ids_from_title": int(pid.nunique()),
    "distinct_patient_letters_from_description": int(letters.nunique()),
    "title_id_to_letter_is_1to1": bool(pd.crosstab(pid, letters).astype(bool).sum(1).eq(1).all()
                                       and pd.crosstab(pid, letters).astype(bool).sum(0).eq(1).all()),
    "series_design_states": "From 14 patients ...",
    "samples_with_GSE11903_GSM_reference": int(src_gsm.notna().sum()),
    "distinct_GSE11903_GSMs_referenced": int(src_gsm.nunique()),
    "per_sample_frac_negative_min_max": [float((X4 < 0).mean(0).min()), float((X4 < 0).mean(0).max())],
    "per_sample_median_min_max": [float(np.median(X4, 0).min()), float(np.median(X4, 0).max())],
    "timepoint_counts": m4["!Sample_characteristics_ch1.2"].value_counts().to_dict(),
    "patients_missing_week12": sorted(set(pid) - set(pid[m4["!Sample_characteristics_ch1.2"].str.contains("Week12")]), key=int),
    "patients_missing_week4": sorted(set(pid) - set(pid[m4["!Sample_characteristics_ch1.2"].str.contains("Week4")]), key=int),
}

# ---- A3 GSE54456
a3 = pd.read_csv(os.path.join(RAW_DIR, "GSE54456/suppl/GSE54456_RPKM_samples.txt.gz"), sep="\t", index_col=0)
_, m3, _ = sm("GSE54456")
res["A3_GSE54456"] = {
    "feature_class_counts": dict(C.Counter(feature_class(x) for x in a3.index)),
    "matrix_col_order_equals_metadata_title_order": list(a3.columns) == list(m3["!Sample_title"]),
    "matrix_cols_equal_metadata_titles_as_set": set(a3.columns) == set(m3["!Sample_title"]),
    "matrix_headers_are_GSM": bool(all(str(c).startswith("GSM") for c in a3.columns)),
    "group_counts": m3["!Sample_characteristics_ch1"].value_counts().to_dict(),
}

# ---- A6 GSE67785
_, m6, _ = sm("GSE67785")
p = m6["!Sample_title"].str.extract(r"Patient (\d+) \((\w\w), ([MF]), (\d+)\)")
res["A6_GSE67785"] = {
    "title_parse_failures": int(p[0].isna().sum()),
    "patients": int(p[0].nunique()),
    "group_counts": p[1].value_counts().to_dict(),
    "sex_counts_per_patient": p.drop_duplicates(0)[2].value_counts().to_dict(),
    "age_min_median_max": [int(p[3].astype(int).min()), float(p[3].astype(int).median()), int(p[3].astype(int).max())],
    "title_sex_consistent_with_characteristic": bool(
        (p[2].map({"M": "gender: male", "F": "gender: female"}) == m6["!Sample_characteristics_ch1.3"]).all()),
}
a6 = pd.read_csv(os.path.join(DERIVED_DIR, "GSE67785/DERIVED_assembled_count.tsv.gz"), sep="\t", index_col=0)
res["A6_GSE67785"]["feature_class_counts"] = dict(C.Counter(feature_class(x) for x in a6.index))

# ---- GPL570 coverage vs RNA-seq symbol sets
txt = gzip.open(os.path.join(ROOT, "data/raw/platforms/GPL570/GPL570.annot.gz"), "rt", encoding="utf-8", errors="replace").read()
s, e = txt.index("!platform_table_begin") + len("!platform_table_begin\n"), txt.index("!platform_table_end")
ann = pd.read_csv(io.StringIO(txt[s:e]), sep="\t", dtype=str)
sym = ann["Gene symbol"].fillna("")
single = set(sym[(sym != "") & ~sym.str.contains("///")])
res["GPL570_vs_RNAseq_symbols"] = {
    "annotation_date": re.search(r"!Annotation_date = (.+)", txt).group(1).strip(),
    "gpl570_single_gene_symbols": len(single),
    "shared_with_A3": len(single & set(a3.index)), "A3_symbols": int(len(a3.index)),
    "shared_with_A6": len(single & set(a6.index)), "A6_symbols": int(len(a6.index)),
    "shared_all_three": len(single & set(a3.index) & set(a6.index)),
}

# ---- Cross: GSM overlap among GPL570 sets; classifier on A5 IDs
gsms = {acc: set(sm(acc)[1]["!Sample_geo_accession"]) for acc in ("GSE13355", "GSE30999", "GSE41663")}
res["cross_GSM_overlap_GPL570"] = {f"{a}&{b}": len(gsms[a] & gsms[b])
                                   for i, a in enumerate(gsms) for b in list(gsms)[i + 1:]}
a5_ids = pd.read_csv(os.path.join(RAW_DIR, "GSE63979/suppl/GSE63979_ReadCount_42samples.txt.gz"), sep="\t").index
res["A5_id_classifier_behaviour"] = {
    "classify_id_counts": dict(C.Counter(classify_id(x) for x in a5_ids)),
    "note": "Generic symbol regex labels custom assembly IDs (G<number>) as 'symbol_like' - FALSE POSITIVE risk.",
    "A5_ids_that_equal_an_A3_or_A6_symbol": int(len(set(a5_ids) & (set(a3.index) | set(a6.index)))),
}

od = os.path.join(DERIVED_DIR, "_cross_dataset")
os.makedirs(od, exist_ok=True)
with open(os.path.join(od, "residual_checks.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, default=str)
print(json.dumps(res, indent=1, default=str))
