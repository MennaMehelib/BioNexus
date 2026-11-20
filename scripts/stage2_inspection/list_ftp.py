"""List GEO FTP directories (matrix/, suppl/, soft/, miniml/) for Development Set only."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from geo_common import ALLOWED, RAW_DIR, list_dir, series_base  # noqa

out = {}
for acc in sorted(ALLOWED):
    base = series_base(acc)
    out[acc] = {}
    for sub in ("matrix/", "suppl/", "soft/", "miniml/"):
        try:
            out[acc][sub] = list_dir(base + sub)
        except Exception as e:  # noqa
            out[acc][sub] = f"ERROR {e}"
        print(acc, sub, out[acc][sub])

os.makedirs(RAW_DIR, exist_ok=True)
with open(os.path.join(RAW_DIR, "ftp_listing.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1)
