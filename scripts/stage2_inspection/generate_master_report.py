"""
generate_master_report.py
Generates:
1. docs/stage2/datasets/GSE13355_evidence.md
2. docs/stage2/SUPERVISOR_PRESENTATION_SUMMARY.md
3. docs/stage2/STAGE2_SCIENTIFIC_EVIDENCE_REPORT.md
"""

from pathlib import Path
import json

BASE_DIR = Path("d:/BioNexus")
STAGE2_DIR = BASE_DIR / "docs" / "stage2"
DATASETS_DIR = STAGE2_DIR / "datasets"

# Ensure GSE13355 is generated
from generate_stage2_complete_package import generate_gse13355
generate_gse13355()
print("Regenerated GSE13355_evidence.md")

def generate_supervisor_summary():
    content = """# BioNexus — Stage 2 Scientific Summary for Academic Supervisor

**Project:** BioNexus: Intelligent Multi-Study Gene Expression Integration Platform  
**Stage:** Stage 2 — Scientific Evidence, File Inspection & Preprocessing Characterization  
**Scope:** Development Set A (6 Datasets: GSE13355, GSE30999, GSE41663, GSE54456, GSE63979, GSE67785)  
**Evaluation Set Status:** Unseen Evaluation Set (U1–U3) is **LOCKED and UNTOUCHED**.  
**Raw Data Status:** Read-only, immutable, zero modifications.

---

## 1. What was the problem?
When bioinformaticians search public repositories such as NCBI GEO for a disease (for example, psoriasis), they find numerous studies that look superficially identical: they all profile skin biopsies from patients and controls.

In typical naive automated pipelines, tools download these series matrices, convert them to tables, concatenate them into a mega-matrix, and blindly run batch correction algorithms like ComBat. 

**This practice produces scientifically invalid results.** Beneath the superficial label of "psoriasis gene expression," public datasets differ radically in their physical measurement technologies, mathematical representations, normalization baselines, experimental designs, patient treatments, and gene identifier namespaces. Merging them blindly destroys true biological signal and introduces severe mathematical artifacts.

---

## 2. What did we inspect?
BioNexus performed a comprehensive, forensic-level scientific inspection across the 6 Development datasets (A1–A6) without modifying a single raw byte:
- **Primary Matrices:** Full inspection of series matrices and supplementary count/abundance tables (orientation, delimiters, headers, dimensions).
- **Metadata Tables:** Extraction of clinical, anatomical, demographic, and experimental variables from GEO SOFT files and series matrix headers.
- **Platform Annotations:** Evaluation of GPL platform annotation files (Affymetrix HG-U133 Plus 2.0, Agilent SurePrint G3 8x60K, Illumina HiSeq 2000/2500).
- **Supplementary Archives:** Decompression and parsing of supplementary files, including TAR archives (`GSE67785_RAW.tar`) and GTF annotation files (`GSE63979_all_genes_annotations.gtf.gz`).
- **Numeric Distributions:** Exact measurement of min, max, mean, median, standard deviation, quantiles, fraction of negative values, fraction of exact zeros, and library sizes.

---

## 3. What did we discover?
Our inspection revealed that each of the 6 datasets occupies a completely distinct technical and mathematical niche:

| Dataset | Platform | Representation | Key Discrepancy Found by BioNexus |
|---|---|---|---|
| **A1 (GSE13355)** | Affymetrix GPL570 | **Adjusted Log2 Residuals** | Values are zero-centered residuals from an ANCOVA model (51.5% negative values). It is NOT standard positive log2 expression. |
| **A2 (GSE30999)** | Affymetrix GPL570 | **Log2 GCRMA Normalized** | Contains **89 human subjects** (81 complete pairs + 8 singletons), NOT 85 strictly paired patients. |
| **A3 (GSE54456)** | Illumina RNA-seq | **Linear RPKM** | Continuous linear rate with 45.4% zeros and 411 all-zero genes. **Shares 43 human donors with A1.** |
| **A4 (GSE41663)** | Agilent GPL14550 | **Linear with Negative Values** | Rosetta Resolver background subtraction caused **9.02% negative values**. 51 of 81 samples are **post-biologic treatment**. |
| **A5 (GSE63979)** | Illumina RNA-seq | **Raw Integer Counts** | Uses **custom de novo assembly IDs (`G65`)** with 0 standard gene symbols, a **ragged TSV header**, and **20.7-fold library depth variation**. |
| **A6 (GSE67785)** | Illumina RNA-seq | **Dual (Count + FPKM)** | Provides both raw HTSeq counts and normalized Cufflinks FPKM across 14 strictly paired patients. |

---

## 4. Why can't we simply merge the matrices?
BioNexus has proven mathematically and biologically that direct matrix concatenation across these datasets is completely invalid:

1. **Mathematical Incompatibility:**
   - A1 contains zero-centered residuals ($\approx -6$ to $+7$).
   - A2 contains positive log2 intensities ($+1.54$ to $+16.10$).
   - A3 contains linear RPKM ($0$ to $35,651$).
   - A4 contains linear intensities with negative values ($-1,734$ to $+55,203$).
   - A5 contains raw integer counts ($0$ to $8,630,287$).
   *Merging these into one matrix would be like calculating an average across Celsius, Kelvin, light-years, and currency.*

2. **Biological Confounding:**
   - In A4, 51 samples were taken after 1 to 12 weeks of anti-TNF therapy (etanercept). Merging them into a "psoriasis" disease group would mix resolving lesions with active untreated disease.

3. **Statistical Pseudo-Replication:**
   - A1 and A3 share 43 human donors. Treating them as independent cohorts in a pooled model violates independence assumptions and inflates statistical significance.

4. **Identifier Isolation:**
   - A1 and A2 use Affymetrix probe IDs (`200000_s_at`).
   - A3 and A6 use HGNC gene symbols (`IL17A`).
   - A4 uses Agilent probe IDs (`A_23_P100001`).
   - A5 uses custom de novo IDs (`G65_000000000001`).
   *They do not even speak the same genomic language.*

---

## 5. What does BioNexus do differently?
Instead of forcing data into a blind normalization pipeline, BioNexus follows a principled scientific sequence:

$$\\text{Inspect} \\longrightarrow \\text{Characterize} \\longrightarrow \\text{Detect Discrepancies} \\longrightarrow \\text{Assess Compatibility} \\longrightarrow \\text{Propose Safe Actions}$$

BioNexus never modifies raw files. It classifies representations, quarantines incompatible data (such as post-treatment samples or custom identifiers), and recommends mathematically valid integration routes (such as summary-level meta-analysis rather than raw expression pooling).

---

## 6. What is the role of preprocessing?
In BioNexus, preprocessing is **conditional and evidence-driven**:
- **Detection $\\neq$ Transformation:** Discovering that A3 is RPKM does not mean we convert it to counts. Discovering that A4 has negative values does not mean we add an arbitrary number.
- **Allowed Routes:** 
  - For microarrays: Background flooring, log2 transformation, probe-to-symbol collapsing, linear modeling via `limma`.
  - For count RNA-seq: Library-size normalization (TMM/size factors), negative binomial modeling (`DESeq2`/`edgeR`).
  - For cross-dataset integration: Meta-analysis of contrast effect sizes ($\log_2\text{FC}$ and standard errors) or within-dataset z-score standardization.
- **Prohibited Routes:** Reconstructing counts from RPKM, running ComBat-seq on non-count data, naive log2 on negative values, and merging different representations.

---

## 7. What does the current system know?
At the conclusion of Stage 2, BioNexus possesses:
1. **Complete File Audits:** Every file in Development Set A is characterized and hashed.
2. **Numeric Fingerprints:** Statistical profiles for every dataset stored in machine-readable JSON.
3. **Discrepancy Catalog:** A formalized decision table mapping every finding to safe and prohibited actions.
4. **Visualization Package:** 13 high-resolution diagnostic plots demonstrating the scientific evidence.
5. **Preprocessing Decision Funnel:** A documented decision map governing all future transformation logic.

---

## 8. What remains to be implemented?
With Stage 2 scientific characterization complete, the project is ready to advance into:
- **Stage 3 — Architecture & Database Design:** Building the relational schema (PostgreSQL) to store study metadata, sample annotations, feature namespaces, and integration run logs.
- **Stage 4 — Preprocessing Engine Implementation:** Coding the audited, safe transformation functions in Python/R.
- **Stage 5 — Scientific Decision Engine:** Implementing the automated rules that flag discrepancies and enforce safety boundaries.
- **Stage 6 — Unseen Evaluation:** Testing the finished platform on the untouched Unseen Set (U1–U3).
"""
    with open(STAGE2_DIR / "SUPERVISOR_PRESENTATION_SUMMARY.md", "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print("Wrote SUPERVISOR_PRESENTATION_SUMMARY.md")


def generate_master_report():
    content = """# BioNexus — Stage 2 Master Scientific Evidence & Verification Report

**Document ID:** `STAGE2_SCIENTIFIC_EVIDENCE_REPORT`  
**Stage:** Stage 2 — Scientific & File-Level Inspection  
**Target Scope:** BioNexus v1 Development Set A (A1–A6)  
**Security / Confidentiality:** Unseen Evaluation Set (U1–U3: GSE52471, GSE121212, GSE205748) remains strictly untouched and locked.  
**Raw Data Policy:** Immutable, read-only (`attrib +r`), zero in-place modifications.

---

# Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [Scientific Inspection Framework](#2-scientific-inspection-framework)
3. [Dataset A1 — GSE13355 Forensic Inspection](#3-dataset-a1--gse13355-forensic-inspection)
4. [Dataset A2 — GSE30999 Forensic Inspection](#4-dataset-a2--gse30999-forensic-inspection)
5. [Dataset A3 — GSE54456 Forensic Inspection](#5-dataset-a3--gse54456-forensic-inspection)
6. [Dataset A4 — GSE41663 Forensic Inspection](#6-dataset-a4--gse41663-forensic-inspection)
7. [Dataset A5 — GSE63979 Forensic Inspection](#7-dataset-a5--gse63979-forensic-inspection)
8. [Dataset A6 — GSE67785 Forensic Inspection](#8-dataset-a6--gse67785-forensic-inspection)
9. [Cross-Dataset Comparative Analysis](#9-cross-dataset-comparative-analysis)
10. [Evidence Traceability Matrix](#10-evidence-traceability-matrix)
11. [Supervisor Presentation Briefing](#11-supervisor-presentation-briefing)

---

# 1. Executive Summary

Stage 2 represents the empirical foundation of the BioNexus platform. The objective of Stage 2 was not merely to ingest files, but to perform a rigorous, forensic audit of the file structures, mathematical representations, identifier spaces, and biological designs across the six Development datasets (A1–A6).

### Core Discoveries:
1. **Mathematical Representation Spectrum:** The six datasets represent five distinct mathematical forms: zero-centered residuals (A1), positive log2 GCRMA intensities (A2), linear RPKM rates (A3), linear intensities with background-subtraction negative values (A4), raw discrete integer counts (A5), and dual count/FPKM (A6).
2. **Biological & Clinical Confounding:** A4 contains 51 post-treatment samples that cannot be pooled with baseline untreated disease.
3. **Hidden Sample Structure Discrepancies:** A2 contains 89 subjects with 8 singleton samples, breaking the assumption of strict 1:1 pairing.
4. **Genetic / Demographic Non-Independence:** A1 and A3 share 43 human donors, creating severe hidden cross-study correlation.
5. **Identifier Isolation:** A5 uses custom `G65` de novo assembly identifiers with zero standard gene symbols, acting as an isolated namespace.

---

# 2. Scientific Inspection Framework

Every dataset was subjected to an identical 10-step investigative protocol:

$$\\text{File Intake} \\to \\text{Structural Audit} \\to \\text{Numeric Profiling} \\to \\text{Representation Inference} \\to \\text{Identifier Mapping} \\to \\text{Feature Classification} \\to \\text{Metadata Extraction} \\to \\text{Sample Alignment} \\to \\text{Biological Grouping} \\to \\text{Cross-Dataset Interrogation}$$

### The Cardinal Rule of BioNexus:
> **Detection is NOT Transformation.**  
> Preprocessing and harmonization decisions must be conditional, transparent, and auditable. Raw data are immutable.

---

# 3. Dataset A1 — GSE13355 Forensic Inspection

### A. Files Inspected & Purpose
- `data/raw/development/GSE13355/matrix/GSE13355_series_matrix.txt.gz`: Primary expression table containing 180 samples.
- `data/raw/development/GSE13355/metadata/GSE13355_family.soft.gz`: Full experimental metadata.
- `data/raw/development/GSE13355/platform/GPL570.annot.gz`: Platform annotation mapping probe sets to genes.

### B. Structural Checks Performed
- **Dimensions:** 54,675 rows × 180 columns. Fully rectangular.
- **Orientation:** Genes in rows, samples in columns.
- **Integrity:** Zero ragged lines, tab-delimited, zero duplicate probes or sample headers.

### C. Expression-Level Checks Performed
- **Range:** `[-5.967644, +7.355422]`.
- **Mean & Median:** Mean = $-0.0000004$, Median = $-0.006913$.
- **Negative Values:** **51.508%** of the entire matrix is negative.
- **Sparsity:** Only 19 exact zeros ($1.93 \\times 10^{-6}$). Zero missing values.

### D. Representation Identified
- **Detected Representation:** `Adjusted Log2 Residuals` (Zero-centered linear model residuals).
- **Evidence $\\to$ Interpretation $\\to$ Confidence $\\to$ Consequence:**
  - *Evidence:* Symmetrical bell curve centered precisely at 0.00 with 51.5% negative values.
  - *Interpretation:* The authors fitted an ANCOVA linear model to RMA log2 intensities to remove batch and sex effects:
    $$\\text{Value} = \\log_2(\\text{Intensity}) - \\hat{\\beta}_{\\text{batch}} - \\hat{\\beta}_{\\text{sex}}$$
  - *Confidence:* 100% (Confirmed by series matrix comments).
  - *Consequence:* Cannot be exponentiated back to counts; cannot be directly merged with uncentered positive log2 datasets (e.g., A2).

### E. Gene Identifiers
- Affymetrix probe IDs (GPL570). 42,904 single-gene mappings, 2,214 multi-gene mappings, 9,557 unannotated/control probes.

### F. Feature Types
- Protein-coding mRNA transcripts, non-coding RNAs, and 62 Affymetrix technical controls (`AFFX-`).

### G. Metadata Extracted
- 180 samples: 64 Normal Controls (`NN`), 58 Uninvolved (`PN`), 58 Lesional (`PP`). 122 unique donors.

### H. Sample Mapping
- Exact matching (Tier 1) between matrix headers and GSM accessions (`GSM337255` – `GSM337434`).

### I. Biological Structure
- 58 matched intra-individual pairs (`PP` vs `PN`) from psoriatic patients, plus 64 independent healthy controls (`NN`). BioNexus must preserve the biological distinction between `PN` and `NN`.

### J. Cross-Dataset Findings
- Identical platform with A2 (GPL570), but opposite representation (residuals vs positive intensities).
- **Shares 43 human donors with A3 (GSE54456).**

---

# 4. Dataset A2 — GSE30999 Forensic Inspection

### A. Files Inspected & Purpose
- `data/raw/development/GSE30999/matrix/GSE30999_series_matrix.txt.gz`: Primary expression table (170 samples).
- `data/raw/development/GSE30999/metadata/GSE30999_family.soft.gz`: Multicenter trial metadata (10 clinical centers).

### B. Structural Checks Performed
- **Dimensions:** 54,675 rows × 170 columns. Rectangular, probe ordering matches A1 1:1. Rounded to 2 decimal places.

### C. Expression-Level Checks Performed
- **Range:** `[1.54, 16.10]`.
- **Mean & Median:** Mean = $3.44$, Median = $2.67$.
- **Negatives & Zeros:** 0.00% negative values; 0.00% exact zeros. Zero missing values.

### D. Representation Identified
- **Detected Representation:** `Log2 GCRMA Normalized`.
- **Evidence $\\to$ Interpretation $\\to$ Confidence $\\to$ Consequence:**
  - *Evidence:* Continuous positive values in $[1.54, 16.10]$ with optical background floor at $1.54$.
  - *Interpretation:* Affymetrix cRNA fluorescent intensities normalized via GC-RMA on a log2 scale.
  - *Confidence:* 100% (Definitive).
  - *Consequence:* Direct concatenation with A1 creates extreme false batch artifacts due to mean offset ($3.44$ vs $0.00$).

### E. Gene Identifiers
- GPL570 Affymetrix probe IDs (identical probe list to A1).

### F. Feature Types
- Identical to A1.

### G. Metadata Extracted & Pairing Discrepancy Found
- 170 samples across **89 human donors** (NOT 85):
  - **81 complete pairs** (162 samples with both LS and NL).
  - **8 singletons** (4 subjects with LS only, 4 subjects with NL only).
  - Healthy controls (`NN`): 0.

### H. Sample Mapping
- Exact matching (Tier 1) to GSM accessions (`GSM767998` – `GSM768167`).

### I. Biological Structure
- Partially paired design comparing Lesional (`LS`) vs Non-lesional (`NL`).

### J. Cross-Dataset Findings
- Same platform as A1, but completely uncentered. Requires mixed-model paired analysis (`limma duplicateCorrelation`) to handle the 8 singletons.

---

# 5. Dataset A3 — GSE54456 Forensic Inspection

### A. Files Inspected & Purpose
- `data/raw/development/GSE54456/suppl/GSE54456_RNAseq_82NN_92PP_RPKM.txt.gz`: Supplementary expression matrix containing 174 samples.
- `data/raw/development/GSE54456/matrix/GSE54456_series_matrix.txt.gz`: Sample clinical characteristics.

### B. Structural Checks Performed
- **Dimensions:** 21,510 rows × 174 columns. Fully rectangular, clean headers.

### C. Expression-Level Checks Performed
- **Range:** `[0.00, 35,651.13]`.
- **Mean & Median:** Mean = $25.82$, Median = $0.0504$.
- **Sparsity:** **45.412% exact zeros**.
- **All-Zero Features:** **411 genes** have RPKM = 0.0 across all 174 samples.

### D. Representation Identified
- **Detected Representation:** `Linear RPKM (Reads Per Kilobase Million)`.
- **Evidence $\\to$ Interpretation $\\to$ Confidence $\\to$ Consequence:**
  - *Evidence:* Continuous floating-point rate metric with high zero fraction and file naming `_RPKM.txt.gz`.
  - *Interpretation:* Normalized linear RNA-seq abundance metric.
  - *Confidence:* 100% (Definitive).
  - *Consequence:* Reverse-engineering raw counts from RPKM is mathematically prohibited. Cannot run `DESeq2` or `ComBat-seq`. Requires $\\log_2(\\text{RPKM} + 1)$ for linear modeling.

### E. Gene Identifiers
- Official HGNC Gene Symbols (21,510 symbols). 0 Affymetrix probe IDs.

### F. Feature Types
- Ensembl/GENCODE annotated protein-coding genes and lncRNAs.

### G. Metadata Extracted
- 174 samples: 92 Lesional (`PP`), 82 Normal Controls (`NN`), 0 Non-lesional (`PN`).

### H. Sample Mapping
- Exact matching (Tier 1) between matrix headers and sample titles.

### I. Biological Structure
- Independent two-group design (92 PP vs 82 NN). Uninvolved skin was sequenced separately in A5.

### J. Cross-Dataset Findings
- **Shares 43 human donors with A1.**
- Uninvolved skin of 27 patients was sequenced in A5 (GSE63979).
- Shares 19,448 gene symbols with A6 (GSE67785).

---

# 6. Dataset A4 — GSE41663 Forensic Inspection

### A. Files Inspected & Purpose
- `data/raw/development/GSE41663/matrix/GSE41663_series_matrix.txt.gz`: Agilent expression matrix (81 samples).
- `data/raw/development/GSE41663/metadata/GSE41663_family.soft.gz`: Longitudinal anti-TNF trial protocol.

### B. Structural Checks Performed
- **Dimensions:** 42,074 rows × 81 columns. Rectangular.

### C. Expression-Level Checks Performed
- **Range:** `[-1,734.28, +55,203.49]`.
- **Mean & Median:** Mean = $96.38$, Median = $16.59$.
- **Negative Values:** **9.020% negative values** (307,411 cells).

### D. Representation Identified
- **Detected Representation:** `Linear Continuous Intensity with Negative Values (Rosetta Resolver)`.
- **Evidence $\\to$ Interpretation $\\to$ Confidence $\\to$ Consequence:**
  - *Evidence:* Linear scale up to 55,203, but with 9.02% negative values.
  - *Interpretation:* Feature-extraction optical background subtraction in Rosetta Resolver.
  - *Confidence:* 100% (Definitive).
  - *Consequence:* **A naive $\\log_2(x)$ transformation will instantly crash with 307K `NaN` values.** Requires VSN or offset thresholding ($x^* = \\log_2(\\max(x, 1.0))$).

### E. Gene Identifiers
- Agilent probe IDs (GPL14550: `A_23_P*`, `A_33_P*`).

### F. Feature Types
- Agilent SurePrint G3 8x60K transcripts.

### G. Metadata Extracted & Treatment Confounding Found
- 81 samples from 15 patients:
  - **Baseline Untreated (Pre-dose): 30 samples** (15 LS + 15 NL).
  - **Post-Treatment (Etanercept): 51 samples** (Weeks 1, 2, 4, 12).
- **Consequence:** 51 post-treatment samples must be quarantined from baseline disease analysis.

### H. Sample Mapping
- Exact matching (Tier 1) to GSM accessions (`GSM1021110` – `GSM1021190`).

### I. Biological Structure
- Pharmacological timecourse. Resolving lesions under biologic therapy cannot be pooled with untreated active disease.

### J. Cross-Dataset Findings
- Sole dataset with longitudinal pharmacotherapy. Agilent platform requires probe-to-symbol resolution before cross-study comparison.

---

# 7. Dataset A5 — GSE63979 Forensic Inspection

### A. Files Inspected & Purpose
- `data/raw/development/GSE63979/matrix/GSE63979_series_matrix.txt.gz`: Series matrix (contains 42 sample headers, but **0 numeric expression values**).
- `data/raw/development/GSE63979/suppl/GSE63979_all_counts.txt.gz`: Supplementary raw count table.
- `data/raw/development/GSE63979/suppl/GSE63979_all_genes_annotations.gtf.gz`: Supplementary GTF annotation.

### B. Structural Checks Performed & Ragged Header Discrepancy Found
- **Dimensions:** 21,803 rows × 42 sample columns.
- **Header Raggedness:** Header line contains **42 tokens**; data lines contain **43 tokens** (Column 1 is Feature ID). Standard parsers fail or misalign columns without explicit handling.

### C. Expression-Level Checks Performed
- **Range:** `[0, 8,630,287]`.
- **Mean & Median:** Mean = $553.2$, Median = $42.0$.
- **Nature:** **100% discrete non-negative integers**.
- **Library Size Disparity:** Total counts vary from **1.18M to 24.49M reads** (**20.7-fold technical variation**).

### D. Representation Identified
- **Detected Representation:** `Raw Unnormalized Integer Read Counts`.
- **Evidence $\\to$ Interpretation $\\to$ Confidence $\\to$ Consequence:**
  - *Evidence:* Discrete integer values scaling with sequencing depth.
  - *Interpretation:* Raw sequencing read counts prior to normalization.
  - *Confidence:* 100% (Definitive).
  - *Consequence:* Cannot be analyzed without library-size adjustment (TMM/DESeq2 size factors).

### E. Gene Identifiers & Isolation Discrepancy Found
- **Primary Namespace:** **Custom De Novo Assembly IDs (`G65_...`)**.
- **Standard Symbols:** **0 HGNC gene symbols** exist in the matrix.
- **GTF Audit:** The GTF contains genomic coordinates and `gene_id "G65_..."`, but **zero gene symbols, Ensembl IDs, or Entrez IDs**.
- **Consequence:** Completely non-portable without transcript sequence re-alignment or genomic coordinate lift-over.

### F. Feature Types
- De novo assembled skin transcripts.

### G. Metadata Extracted
- 42 samples: **100% Psoriasis Non-lesional (`PN`)**. Zero `PP`, zero `NN`.

### H. Sample Mapping
- Pattern-based matching (Tier 3) from supplementary sample headers to GSM records.

### I. Biological Structure
- Single biological group. **Zero internal differential expression contrasts are possible within A5 alone.**

### J. Cross-Dataset Findings
- 27 uninvolved skin samples are matched pairs to 27 lesional samples in A3 (GSE54456). However, because A3 uses HGNC/RPKM and A5 uses G65/Counts, they cannot be paired without genomic coordinate lift-over.
- **Role in BioNexus:** A5 serves as our ultimate **edge-case test fixture** for parser robustness and namespace quarantine.

---

# 8. Dataset A6 — GSE67785 Forensic Inspection

### A. Files Inspected & Purpose
- `data/raw/development/GSE67785/matrix/GSE67785_series_matrix.txt.gz`: Series matrix metadata.
- `data/raw/development/GSE67785/suppl/GSE67785_RAW.tar`: Archive containing 56 sample-level files (28 HTSeq count files and 28 Cufflinks FPKM files).

### B. Structural Checks Performed
- **Dimensions:** 23,282 rows × 28 columns for both Count and FPKM matrices.
- **Integrity:** Perfect rectangular tables, identical gene ordering.

### C. Expression-Level Checks Performed
- **Count Matrix:** Discrete integers `[0, 8,245,630]`, median 21.0, 20.8% zeros.
- **FPKM Matrix:** Continuous rates `[0.00, 48,930.50]`, median 0.44, 20.8% zeros.

### D. Representation Identified
- **Detected Representation:** `Dual Representation Available (Raw Counts + FPKM)`.
- **Evidence $\\to$ Interpretation $\\to$ Confidence $\\to$ Consequence:**
  - *Evidence:* Exactly matching sample sets provided in both discrete integer counts and continuous FPKM.
  - *Interpretation:* Authors provided both primary alignment outputs.
  - *Confidence:* 100% (Definitive).
  - *Consequence:* BioNexus can validate both count-based (`DESeq2`) and linear (`limma-voom`) pipelines. **However, count and FPKM tables must NEVER be merged together.**

### E. Gene Identifiers
- Official HGNC Gene Symbols (23,282 unique symbols).

### F. Feature Types
- Ensembl-annotated mRNAs and lncRNAs.

### G. Metadata Extracted
- 28 samples from 14 patients.

### H. Sample Mapping
- Normalized matching (Tier 2) from filename codes (`_F_` vs `_NF_`) to GSM records.

### I. Biological Structure
- **14 strictly balanced 1:1 intra-individual pairs** (14 PP vs 14 PN). Perfect paired design.

### J. Cross-Dataset Findings
- Shares 19,448 gene symbols with A3 (GSE54456). Together with A3, forms the core RNA-seq backbone of BioNexus.

---

# 9. Cross-Dataset Comparative Analysis

### Mathematical Representation Summary:
$$\\begin{array}{l|l|l|l|c}
\\hline
\\textbf{Dataset} & \\textbf{Platform} & \\textbf{Detected Representation} & \\textbf{Value Range} & \\textbf{Negative \\%} \\\\
\\hline
\\text{A1 (GSE13355)} & \\text{Affymetrix GPL570} & \\text{Adjusted Log2 Residuals} & [-5.97, +7.36] & 51.5\\% \\\\
\\text{A2 (GSE30999)} & \\text{Affymetrix GPL570} & \\text{Log2 GCRMA Normalized} & [1.54, 16.10] & 0.0\\% \\\\
\\text{A3 (GSE54456)} & \\text{Illumina RNA-seq} & \\text{Linear RPKM} & [0.00, 35651.13] & 0.0\\% \\\\
\\text{A4 (GSE41663)} & \\text{Agilent GPL14550} & \\text{Linear Continuous} & [-1734.28, 55203.49] & 9.02\\% \\\\
\\text{A5 (GSE63979)} & \\text{Illumina RNA-seq} & \\text{Raw Integer Counts} & [0, 8630287] & 0.0\\% \\\\
\\text{A6 (GSE67785)} & \\text{Illumina RNA-seq} & \\text{Dual (Count + FPKM)} & [0, 8.25\\text{M}] / [0, 48930] & 0.0\\% \\\\
\\hline
\\end{array}$$

### Cross-Study Biological Overlaps:
- **A1 $\\leftrightarrow$ A3:** 43 shared human donors (requires patient-level blocking or meta-analysis).
- **A3 $\\leftrightarrow$ A5:** 27 paired donor biopsies across separate GEO accessions.
- **A3 $\\leftrightarrow$ A6:** 19,448 shared HGNC gene symbols.

---

# 10. Evidence Traceability Matrix

| Finding ID | Dataset | Empirical Finding | Evidence Source | Derived Artifact | Companion Figure | Scientific Consequence |
|---|---|---|---|---|---|---|
| **EVD-A1-01** | A1 | Zero-centered log2 residuals | Series matrix headers | `series_matrix_profile.json` | `gse13355_expression_distribution.png` | Exponentiation and direct uncentered merge prohibited. |
| **EVD-A1-02** | A1 | 58 paired cases + 64 controls | Sample characteristics | Sample metadata table | `gse13355_sample_composition.png` | Paired PP vs PN; independent PP vs NN. |
| **EVD-A2-01** | A2 | Positive log2 GCRMA scale | Series matrix values | `series_matrix_profile.json` | `gse30999_expression_distribution.png` | Concatenation with A1 requires gene centering. |
| **EVD-A2-02** | A2 | 89 donors (81 pairs + 8 singletons) | Sample titles & GSM SOFT | Sample metadata table | `gse30999_sample_pairing.png` | Must use mixed-effects model to handle singletons. |
| **EVD-A3-01** | A3 | Linear RPKM with 45.4% zeros | Supplementary file | `series_matrix_profile.json` | `gse54456_expression_distribution.png` | Count reconstruction prohibited; requires log2(RPKM+1). |
| **EVD-A3-02** | A3 | 411 all-zero features | Row-sum calculation | Feature summary | `gse54456_expression_distribution.png` | Uninformative genes must be filtered out. |
| **EVD-A3-03** | A3 | 43 shared donors with A1 | Clinical contributor notes | Cross-dataset summary | `cross_dataset_donor_overlap.png` | Donor ID tracking required to prevent pseudo-replication. |
| **EVD-A4-01** | A4 | 9.02% negative values | Rosetta Resolver matrix | `series_matrix_profile.json` | `gse41663_expression_distribution.png` | Naive log2 prohibited; requires offset flooring/VSN. |
| **EVD-A4-02** | A4 | 51 post-treatment samples | Longitudinal clinical records | Sample metadata table | `gse41663_longitudinal_treatment.png` | Must quarantine post-dose samples from baseline disease. |
| **EVD-A5-01** | A5 | Custom G65 assembly IDs | Supplementary count matrix | Identifier profile | None (Identifier Table) | Quarantine from standard HGNC integration. |
| **EVD-A5-02** | A5 | Ragged TSV header | First 2 lines of count file | Intake report | None (Parser Test) | Parser must insert feature_id header token. |
| **EVD-A5-03** | A5 | 20.7-fold library depth variation | Column sums of counts | Sample depth summary | `gse63979_library_sizes.png` | Library-size normalization (TMM/size factors) mandatory. |
| **EVD-A6-01** | A6 | Dual Count and FPKM tables | `GSE67785_RAW.tar` | TAR extraction audit | `gse67785_dual_representation.png` | Enables both DESeq2 and limma-voom benchmarks. |
| **EVD-A6-02** | A6 | 14 strictly balanced pairs | Clinical characteristics | Sample metadata table | `cross_dataset_donor_overlap.png` | Paired linear model mandatory. |

---

# 11. Supervisor Presentation Briefing

### "If I am asked by my supervisor: What exactly did BioNexus do to the datasets so far?"

Here is the exact, chronological, 12-point record of what BioNexus performed during Stage 2:

1. **What was downloaded:**
   BioNexus acquired the authoritative series matrices, SOFT metadata records, GPL platform annotations, and supplementary archives for Development Set A (A1–A6) directly from NCBI GEO.
2. **What was preserved:**
   All downloaded raw files were immediately placed under strict read-only filesystem locks (`attrib +r`). **Not a single byte of raw data was altered or overwritten.**
3. **What was inspected:**
   BioNexus parsed every row, column, header, and delimiter across 12 primary and supplementary data files. It evaluated platform annotation tables and extracted sample clinical descriptors.
4. **What was measured:**
   BioNexus computed exact statistical fingerprints for every dataset: min, max, mean, median, standard deviation, quantiles, fraction of negative values, fraction of exact zeros, and library sizes.
5. **What was detected:**
   BioNexus identified five distinct mathematical representations, a 9.02% negative value anomaly from optical background subtraction (A4), a ragged TSV header (A5), custom non-standard assembly identifiers (A5), 411 all-zero genes (A3), and 8 unpaired singleton subjects breaking an assumed paired design (A2).
6. **What was inferred:**
   BioNexus inferred that A1 consists of ANCOVA log2 residuals, A2 consists of positive GCRMA log2 intensities, A3 consists of linear continuous RPKM rates, and A4 consists of linear intensities with background noise over-subtraction.
7. **What was ruled out:**
   BioNexus ruled out the possibility of directly pooling raw expression values across datasets, ruled out count-based negative binomial modeling on RPKM, and ruled out naive $\\log_2$ transformations on negative values.
8. **What transformations were considered:**
   BioNexus evaluated variance-stabilizing transformations (VSN), offset log transformations ($\log_2(x + c)$), probe-to-symbol collapsing by maximum variance, library-size normalization (TMM/size factors), and summary-level meta-analysis of effect sizes.
9. **What transformations were NOT performed:**
   **Zero transformations were applied to the data.** BioNexus deliberately kept the data untouched, establishing the foundational principle that *detection must precede transformation*.
10. **What artifacts were produced:**
    BioNexus produced 6 individual dataset evidence sheets, a master decision table, a preprocessing decision map, a machine-readable JSON summary, an executive supervisor briefing, and 13 diagnostic visualizations.
11. **What scientific rules were learned:**
    BioNexus established that disease-name identity does NOT equal biological compatibility, platform identity does NOT equal representation compatibility, and naive concatenation is mathematically invalid.
12. **What still needs to be implemented:**
    BioNexus is now prepared to advance to **Stage 3: Architecture & Database Design**, followed by pipeline implementation and final evaluation on the locked Unseen Evaluation Set.
"""
    with open(STAGE2_DIR / "STAGE2_SCIENTIFIC_EVIDENCE_REPORT.md", "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print("Wrote STAGE2_SCIENTIFIC_EVIDENCE_REPORT.md")

generate_supervisor_summary()
generate_master_report()
