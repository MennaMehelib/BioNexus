"""
Generic, dataset-agnostic profiling helpers for Stage 2 inspection.
(Inspection tooling only - NOT the BioNexus ingestion pipeline.)

All functions read original files read-only. Nothing is written back to data/raw.
"""
import gzip
import io
import math
import re
from collections import Counter, OrderedDict

import numpy as np
import pandas as pd

ID_PATTERNS = OrderedDict([
    ("ensembl_gene_versioned", re.compile(r"^ENSG\d{11}\.\d+$")),
    ("ensembl_gene", re.compile(r"^ENSG\d{11}$")),
    ("ensembl_transcript", re.compile(r"^ENST\d{11}(\.\d+)?$")),
    ("affy_probe", re.compile(r"^\d+(_[a-z]+)*_at$|^AFFX[-_].+")),
    ("illumina_probe", re.compile(r"^ILMN_\d+$")),
    ("refseq", re.compile(r"^[NX][MR]_\d+(\.\d+)?$")),
    ("entrez_numeric", re.compile(r"^\d+$")),
    ("cufflinks_xloc", re.compile(r"^XLOC_\d+$")),
    ("cufflinks_tcons", re.compile(r"^TCONS_\d+$")),
    ("cufflinks_cuff", re.compile(r"^CUFF\.\d+(\.\d+)?$")),
    ("symbol_like", re.compile(r"^[A-Za-z][A-Za-z0-9\-\.]*(@)?$")),
])


def classify_id(x: str) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)) or str(x).strip() == "":
        return "EMPTY"
    s = str(x).strip()
    for name, pat in ID_PATTERNS.items():
        if pat.match(s):
            return name
    return "other"


def open_text(path):
    if path.endswith(".gz"):
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8", errors="replace")
    return open(path, "r", encoding="utf-8", errors="replace")


def parse_series_matrix(path):
    """Return (series_meta: dict[list], sample_meta: DataFrame, table: DataFrame|None)."""
    series, sample_rows, table_lines = {}, [], []
    in_table = False
    with open_text(path) as f:
        for line in f:
            line = line.rstrip("\n").rstrip("\r")
            if line.startswith("!series_matrix_table_begin"):
                in_table = True
                continue
            if line.startswith("!series_matrix_table_end"):
                in_table = False
                continue
            if in_table:
                table_lines.append(line)
            elif line.startswith("!Series_"):
                k, _, v = line.partition("\t")
                series.setdefault(k, []).append(v.strip('"'))
            elif line.startswith("!Sample_"):
                parts = line.split("\t")
                sample_rows.append([parts[0]] + [p.strip('"') for p in parts[1:]])
    # sample metadata: keys may repeat (characteristics_ch1) -> suffix index
    cnt = Counter()
    cols = OrderedDict()
    for r in sample_rows:
        k = r[0]
        cnt[k] += 1
        key = k if cnt[k] == 1 else f"{k}.{cnt[k]}"
        cols[key] = r[1:]
    smeta = pd.DataFrame(cols)
    table = None
    if table_lines:
        table = pd.read_csv(io.StringIO("\n".join(table_lines)), sep="\t",
                            quotechar='"', low_memory=False)
    return series, smeta, table


def profile_numeric(df: pd.DataFrame, id_col: str, sample_cols):
    """Profile a features x samples numeric block. Returns dict."""
    X = df[sample_cols].apply(pd.to_numeric, errors="coerce")
    raw_nonnum = int((X.isna() & df[sample_cols].notna()).sum().sum())
    V = X.to_numpy(dtype=float)
    finite = np.isfinite(V)
    vals = V[finite]
    res = OrderedDict()
    res["n_rows"] = int(V.shape[0])
    res["n_sample_cols"] = int(V.shape[1])
    res["n_nan"] = int(np.isnan(V).sum())
    res["n_inf"] = int(np.isinf(V).sum())
    res["non_numeric_cells_coerced_to_nan"] = raw_nonnum
    res["rows_with_any_nan"] = int(np.isnan(V).any(axis=1).sum())
    res["cols_with_any_nan"] = int(np.isnan(V).any(axis=0).sum())
    res["min"] = float(vals.min()) if vals.size else None
    res["max"] = float(vals.max()) if vals.size else None
    res["n_negative"] = int((vals < 0).sum())
    res["n_zero"] = int((vals == 0).sum())
    res["frac_zero"] = float((vals == 0).mean()) if vals.size else None
    res["frac_integer"] = float((np.mod(vals, 1) == 0).mean()) if vals.size else None
    nz = vals[vals != 0]
    res["frac_integer_nonzero"] = float((np.mod(nz, 1) == 0).mean()) if nz.size else None
    q = [0, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 0.999, 1]
    res["quantiles"] = {str(k): float(v) for k, v in zip(q, np.quantile(vals, q))} if vals.size else {}
    sums = np.nansum(V, axis=0)
    res["col_sum_min"] = float(sums.min())
    res["col_sum_median"] = float(np.median(sums))
    res["col_sum_max"] = float(sums.max())
    res["col_sum_cv"] = float(sums.std() / sums.mean()) if sums.mean() else None
    med = np.nanmedian(V, axis=0)
    res["col_median_min"] = float(np.nanmin(med))
    res["col_median_max"] = float(np.nanmax(med))
    with np.errstate(invalid="ignore"):
        rowmax = np.nanmax(np.where(np.isnan(V), -np.inf, V), axis=1)
        rowmin = np.nanmin(np.where(np.isnan(V), np.inf, V), axis=1)
    res["all_zero_rows"] = int(((V == 0) | np.isnan(V)).all(axis=1).sum() - np.isnan(V).all(axis=1).sum())
    res["all_nan_rows"] = int(np.isnan(V).all(axis=1).sum())
    zero_frac_row = (V == 0).mean(axis=1)
    res["rows_zero_ge_50pct"] = int((zero_frac_row >= 0.5).sum())
    res["rows_zero_ge_90pct"] = int((zero_frac_row >= 0.9).sum())
    res["constant_rows"] = int((rowmax == rowmin).sum())
    res["constant_nonzero_rows"] = int(((rowmax == rowmin) & (rowmax != 0)).sum())
    # log-scale heuristics evidence (not decisions)
    res["frac_values_gt_20"] = float((vals > 20).mean()) if vals.size else None
    res["frac_values_gt_100"] = float((vals > 100).mean()) if vals.size else None
    res["frac_values_gt_1000"] = float((vals > 1000).mean()) if vals.size else None
    # IDs
    ids = df[id_col].astype(str)
    res["id_column"] = id_col
    res["n_unique_ids"] = int(ids.nunique())
    res["n_duplicate_id_rows"] = int(ids.duplicated(keep=False).sum())
    res["n_empty_ids"] = int((df[id_col].isna() | (ids.str.strip() == "")).sum())
    res["id_class_counts"] = dict(Counter(classify_id(x) for x in df[id_col]).most_common())
    res["id_examples_head"] = ids.head(5).tolist()
    res["id_examples_tail"] = ids.tail(5).tolist()
    # Samples
    sc = list(sample_cols)
    res["n_duplicate_sample_cols"] = int(pd.Series(sc).duplicated(keep=False).sum())
    res["sample_col_examples"] = sc[:5] + ["..."] + sc[-3:]
    return res


def tpm_like(df, sample_cols):
    s = df[sample_cols].apply(pd.to_numeric, errors="coerce").sum(axis=0)
    return {"col_sum_min": float(s.min()), "col_sum_max": float(s.max())}


def summarize_sample_meta(smeta: pd.DataFrame, max_levels=12):
    """For each !Sample_ column, list number of distinct values and top levels."""
    out = OrderedDict()
    for c in smeta.columns:
        vc = smeta[c].value_counts(dropna=False)
        out[c] = {"n_distinct": int(vc.size),
                  "top": {str(k): int(v) for k, v in vc.head(max_levels).items()}}
    return out
