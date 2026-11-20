"""Download Development Set files needed for inspection (allowlisted)."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from geo_common import download, series_base  # noqa

PLAN = {
    "GSE13355": ["matrix/GSE13355_series_matrix.txt.gz", "suppl/filelist.txt"],
    "GSE30999": ["matrix/GSE30999_series_matrix.txt.gz", "suppl/filelist.txt"],
    "GSE41663": ["matrix/GSE41663_series_matrix.txt.gz", "suppl/filelist.txt"],
    "GSE54456": ["matrix/GSE54456_series_matrix.txt.gz", "soft/GSE54456_family.soft.gz",
                 "suppl/GSE54456_RPKM_samples.txt.gz", "suppl/GSE54456_MAoverlappedsamples.txt.gz"],
    "GSE63979": ["matrix/GSE63979_series_matrix.txt.gz", "soft/GSE63979_family.soft.gz",
                 "suppl/GSE63979_ReadCount_42samples.txt.gz", "suppl/GSE63979_assembly.filtered.gtf.gz"],
    "GSE67785": ["matrix/GSE67785_series_matrix.txt.gz", "soft/GSE67785_family.soft.gz",
                 "suppl/GSE67785_RAW.tar", "suppl/filelist.txt"],
}

only = sys.argv[1:] or list(PLAN)
for acc in only:
    for rel in PLAN[acc]:
        sub, name = rel.split("/")
        download(acc, series_base(acc) + rel, sub)
