"""Inspect GPL570 GEO annotation (probe -> gene mapping structure). Read-only."""
import collections as C
import gzip
import io
import os

import pandas as pd

p = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw", "platforms", "GPL570", "GPL570.annot.gz")
txt = gzip.open(p, "rt", encoding="utf-8", errors="replace").read()
head = [l for l in txt.split("\n")[:40] if l.startswith("!") or l.startswith("^")]
print("\n".join(h[:200] for h in head[:15]))
start = txt.index("!platform_table_begin") + len("!platform_table_begin\n")
end = txt.index("!platform_table_end")
df = pd.read_csv(io.StringIO(txt[start:end]), sep="\t", dtype=str)
print("columns:", list(df.columns))
print("rows:", len(df))
sym = df["Gene symbol"].fillna("")
eid = df["Gene ID"].fillna("")
print("probes with no symbol:", int((sym == "").sum()))
print("probes mapping to >1 gene (/// in symbol):", int(sym.str.contains("///").sum()))
single = sym[(sym != "") & ~sym.str.contains("///")]
pc = single.value_counts()
print("distinct single-gene symbols:", len(pc), "symbols with >1 probe:", int((pc > 1).sum()),
      "max probes/gene:", pc.max(), pc.head(5).to_dict())
print("AFFX control probes:", int(df["ID"].str.startswith("AFFX").sum()))
print("probes with Entrez ID:", int((eid != "").sum()))
