"""Compile stage2_evidence_summary.json (structured findings across Development Set)."""
import json
import os
from datetime import datetime, timezone

summary = {
    "generated_utc": datetime.now(timezone.utc).isoformat(),
    "stage": "Stage 2 - Scientific & File Inspection",
    "scope": "Development Set A (A1-A6) + Platform GPL570",
    "unseen_set_status": "LOCKED (U1-U3: GSE52471, GSE121212, GSE205748 untouched)",
    "datasets": {
        "A1_GSE13355": {
            "accession": "GSE13355",
            "title": "Gene expression data of skin from psoriatic patients and normal controls",
            "platform": "GPL570 (Affymetrix Human Genome U133 Plus 2.0)",
            "technology": "Microarray (cRNA target)",
            "source_file": "data/raw/development/GSE13355/matrix/GSE13355_series_matrix.txt.gz",
            "dimensions": {"rows": 54675, "cols": 180},
            "orientation": "genes_rows__samples_cols",
            "representation": {
                "detected": "adjusted_log2_residuals",
                "value_range": [-5.967644, 7.355422],
                "median": -0.006913,
                "negative_fraction": 0.51508,
                "zero_fraction": 1.93e-06,
                "author_processing": "RMA followed by linear model adjustment on log scale for batch and sex"
            },
            "identifiers": {
                "namespace": "affymetrix_probe_id",
                "total_unique": 54675,
                "control_probes": 62,
                "single_symbol_coverage": 42904,
                "multi_symbol_coverage": 2214,
                "unannotated_coverage": 9557
            },
            "samples": {
                "total": 180,
                "unique_donors": 122,
                "groups": {"NN_control": 64, "PN_uninvolved": 58, "PP_lesional": 58},
                "pairing": "58 paired cases (PP+PN) + 64 single controls (NN)",
                "shared_donors": {"with_GSE54456": 43}
            },
            "decision": "compatible_with_warnings",
            "visualizations": [
                "data/derived/development/visualizations/GSE13355/gse13355_expression_distribution.png",
                "data/derived/development/visualizations/GSE13355/gse13355_sample_composition.png"
            ]
        },
        "A2_GSE30999": {
            "accession": "GSE30999",
            "title": "Expression data from skin biopsy samples from patients with moderate-to-severe psoriasis",
            "platform": "GPL570 (Affymetrix Human Genome U133 Plus 2.0)",
            "technology": "Microarray (cRNA target)",
            "source_file": "data/raw/development/GSE30999/matrix/GSE30999_series_matrix.txt.gz",
            "dimensions": {"rows": 54675, "cols": 170},
            "orientation": "genes_rows__samples_cols",
            "representation": {
                "detected": "log2_gcrma_normalized",
                "value_range": [1.54, 16.10],
                "median": 2.67,
                "negative_fraction": 0.0,
                "zero_fraction": 0.0,
                "author_processing": "Normalized by GCRMA (rounded to 2 decimal places)"
            },
            "identifiers": {
                "namespace": "affymetrix_probe_id",
                "total_unique": 54675,
                "probe_order_match_A1": True
            },
            "samples": {
                "total": 170,
                "unique_donors": 89,
                "groups": {"LS_lesional": 85, "NL_non_lesional": 85, "NN_control": 0},
                "pairing_discrepancy": "81 complete pairs (162 samples) + 8 singletons (4 LS only, 4 NL only)",
                "collection_sites": 10
            },
            "decision": "compatible_with_warnings",
            "visualizations": [
                "data/derived/development/visualizations/GSE30999/gse30999_expression_distribution.png",
                "data/derived/development/visualizations/GSE30999/gse30999_sample_pairing.png"
            ]
        },
        "A3_GSE54456": {
            "accession": "GSE54456",
            "title": "Transcriptome analysis of psoriasis in a large case-control sample",
            "platform": "GPL9052 (Illumina Genome Analyzer IIx)",
            "technology": "RNA-seq (Poly-A single-end 80bp)",
            "source_file": "data/raw/development/GSE54456/suppl/GSE54456_RPKM_samples.txt.gz",
            "dimensions": {"rows": 21510, "cols": 174},
            "orientation": "genes_rows__samples_cols",
            "representation": {
                "detected": "linear_rpkm",
                "value_range": [0.0, 35651.046],
                "median": 2.861,
                "negative_fraction": 0.0,
                "zero_fraction": 0.14128,
                "all_zero_features": 411,
                "column_sums": [398632, 670208],
                "author_processing": "Exon counts normalized to RPKM via TopHat 1.3.3"
            },
            "identifiers": {
                "namespace": "hgnc_gene_symbol",
                "total_unique": 21510,
                "shared_with_A6": 19448,
                "excel_corruptions": 0
            },
            "samples": {
                "total": 174,
                "unique_donors": 174,
                "groups": {"PP_lesional": 92, "NN_control": 82, "PN_uninvolved": 0},
                "shared_donors": {"with_GSE13355": 43, "with_GSE63979": 27}
            },
            "decision": "compatible_with_warnings",
            "visualizations": [
                "data/derived/development/visualizations/GSE54456/gse54456_expression_distribution.png",
                "data/derived/development/visualizations/GSE54456/gse54456_sample_composition.png"
            ]
        },
        "A4_GSE41663": {
            "accession": "GSE41663",
            "title": "Re-analysis by microarray using cDNA target of samples from psoriasis patients enrolled in an etanercept trial",
            "platform": "GPL570 (Affymetrix Human Genome U133 Plus 2.0)",
            "technology": "Microarray (cDNA target)",
            "source_file": "data/raw/development/GSE41663/matrix/GSE41663_series_matrix.txt.gz",
            "dimensions": {"rows": 54675, "cols": 81},
            "orientation": "genes_rows__samples_cols",
            "representation": {
                "detected": "linear_intensity_with_negatives",
                "value_range": [-1733.61, 55202.58],
                "median": 119.52,
                "negative_fraction": 0.09022,
                "probes_with_any_negative": 18026,
                "author_processing": "Rosetta Resolver Intensity Profile Builder error-weighted background subtraction"
            },
            "identifiers": {
                "namespace": "affymetrix_probe_id",
                "total_unique": 54675,
                "probe_order_match_A1": True
            },
            "samples": {
                "total": 81,
                "unique_donors": 15,
                "groups": {
                    "Pre_dose_NL": 15, "Pre_dose_LS": 15,
                    "Week_1_LS": 15, "Week_2_LS": 15, "Week_4_LS": 13, "Week_12_LS": 8
                },
                "treatment_arms": "30 baseline untreated + 51 post-etanercept samples"
            },
            "decision": "requires_manual_review",
            "visualizations": [
                "data/derived/development/visualizations/GSE41663/gse41663_expression_distribution.png",
                "data/derived/development/visualizations/GSE41663/gse41663_longitudinal_treatment.png"
            ]
        },
        "A5_GSE63979": {
            "accession": "GSE63979",
            "title": "Analysis of long non-coding RNAs in normal and psoriatic skin",
            "platform": "GPL9052 (Illumina Genome Analyzer IIx)",
            "technology": "RNA-seq (Poly-A single-end 80bp)",
            "source_file": "data/raw/development/GSE63979/suppl/GSE63979_ReadCount_42samples.txt.gz",
            "dimensions": {"rows": 21803, "cols": 42},
            "orientation": "genes_rows__samples_cols",
            "representation": {
                "detected": "raw_integer_counts",
                "value_range": [0, 3278723],
                "median": 168.0,
                "negative_fraction": 0.0,
                "zero_fraction": 0.06894,
                "integer_fraction": 1.0,
                "library_size_range_M": [3.95, 81.75],
                "author_processing": "De novo transcriptome assembly read counts; NO FPKM file on GEO"
            },
            "identifiers": {
                "namespace": "custom_assembly_id",
                "total_unique": 21803,
                "format": "G<number> (e.g. G65)",
                "gtf_attributes": "Coordinates present; gene_name and biotype MISSING"
            },
            "samples": {
                "total": 42,
                "unique_donors": 42,
                "groups": {"Uninvolved_skin_PN": 27, "normal_skin_NN": 8, "psoriatic_skin_PP": 7},
                "shared_donors": {"with_GSE54456": "27 uninvolved samples match A3 lesional donors"}
            },
            "decision": "requires_manual_review",
            "visualizations": [
                "data/derived/development/visualizations/GSE63979/gse63979_library_sizes.png"
            ]
        },
        "A6_GSE67785": {
            "accession": "GSE67785",
            "title": "Proteogenomic analysis of psoriasis reveals discordant and concordant changes in mRNA and protein abundance",
            "platform": "GPL10999 (Illumina Genome Analyzer IIx)",
            "technology": "RNA-seq (Poly-A paired biopsy design)",
            "source_file": "data/raw/development/GSE67785/suppl/GSE67785_RAW.tar (28 per-sample files)",
            "dimensions": {"rows": 25272, "cols": 28},
            "orientation": "genes_rows__samples_cols",
            "representation": {
                "detected": "dual_counts_and_fpkm",
                "count_range": [0, 1417849],
                "count_median": 82.0,
                "fpkm_range": [0.0, 304145.0],
                "fpkm_median": 1.453,
                "library_size_range_M": [18.37, 33.54],
                "library_size_cv": 0.136,
                "author_processing": "HTSeq-count (counts) + Cufflinks 2.2.1 (FPKM)"
            },
            "identifiers": {
                "namespace": "ucsc_hgnc_gene_symbol",
                "total_unique": 25272,
                "shared_with_A3": 19448,
                "non_alnum_ids": ["APOBEC3A_B", "GTF2H2C_2", "C4B_2"]
            },
            "samples": {
                "total": 28,
                "unique_donors": 14,
                "groups": {"PP_lesional": 14, "PN_uninvolved": 14, "NN_control": 0},
                "pairing": "14 strictly paired patients (100% complete)"
            },
            "decision": "compatible",
            "visualizations": [
                "data/derived/development/visualizations/GSE67785/gse67785_dual_representation.png"
            ]
        }
    },
    "cross_dataset_visualizations": [
        "data/derived/development/visualizations/cross_dataset/cross_dataset_representation_comparison.png",
        "data/derived/development/visualizations/cross_dataset/cross_dataset_donor_overlap.png",
        "data/derived/development/visualizations/cross_dataset/cross_dataset_pairwise_compatibility_matrix.png"
    ]
}

out_p = "data/derived/development/stage2_evidence_summary.json"
with open(out_p, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)
print("Saved:", out_p)
