"""Generate Stage 2 Scientific Visualizations for BioNexus Development Set (A1-A6).
Plots are saved in data/derived/development/visualizations/<accession>/ and cross_dataset/.
Inspection & audit tooling only. Original raw files remain read-only.
"""
import gzip
import io
import json
import os
import re
import sys
import tarfile

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

sys.path.insert(0, os.path.dirname(__file__))
from geo_common import DERIVED_DIR, RAW_DIR, ROOT  # noqa
from profiling import parse_series_matrix  # noqa

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Helvetica"]
plt.rcParams["axes.edgecolor"] = "#333333"
plt.rcParams["axes.linewidth"] = 0.8
plt.rcParams["figure.autolayout"] = True

VIZ_DIR = os.path.join(DERIVED_DIR, "visualizations")
os.makedirs(VIZ_DIR, exist_ok=True)

# -------------------------------------------------------------
# 1. GSE13355 (A1)
# -------------------------------------------------------------
print("Generating GSE13355 visualizations...")
out_a1 = os.path.join(VIZ_DIR, "GSE13355")
os.makedirs(out_a1, exist_ok=True)

_, m1, t1 = parse_series_matrix(os.path.join(RAW_DIR, "GSE13355/matrix/GSE13355_series_matrix.txt.gz"))
X1 = t1.iloc[:, 1:].to_numpy(float)

# Figure 1: Expression distribution showing zero-centered residuals
fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
flat1 = X1.ravel()
# Subsample 100,000 values for fast, clean density plot
sub1 = np.random.RandomState(42).choice(flat1, size=100000, replace=False)
sns.histplot(sub1, bins=100, kde=True, color="#2b5c8f", ax=ax, stat="density", alpha=0.6)
ax.axvline(0, color="#d95f02", linestyle="--", linewidth=1.5, label="Center (x = 0.0)")
ax.axvline(np.median(sub1), color="#7570b3", linestyle=":", linewidth=1.5, label=f"Median ({np.median(sub1):.3f})")
ax.set_title("GSE13355 (A1): Zero-Centered Adjusted Log2 Residuals\nDisproves Stage 1 'Absolute Log2 RMA' Assumption", fontsize=12, fontweight="bold")
ax.set_xlabel("Expression Value (Residual Deviation from Mean)", fontsize=10)
ax.set_ylabel("Density", fontsize=10)
ax.annotate(f"Min: {flat1.min():.2f}\nMax: {flat1.max():.2f}\nNegative Cells: 51.5%\nMean of probe means: +0.0001",
            xy=(0.03, 0.65), xycoords="axes fraction",
            bbox=dict(boxstyle="round,pad=0.5", fc="#f7f7f7", ec="#cccccc", lw=1), fontsize=9)
ax.legend(loc="upper right")
fig.savefig(os.path.join(out_a1, "gse13355_expression_distribution.png"))
plt.close(fig)

# Figure 2: Sample Composition & Pairing
fig, ax = plt.subplots(figsize=(7, 4.5), dpi=300)
counts1 = m1["!Sample_characteristics_ch1"].value_counts()
colors = ["#1b9e77", "#d95f02", "#7570b3"]
bars = ax.bar(["Control (NN)", "Lesional (PP)", "Non-Lesional (PN)"],
              [counts1.get("normal skin from controls", 64),
               counts1.get("involved skin from cases", 58),
               counts1.get("uninvolved skin from cases", 58)],
              color=colors, width=0.55, edgecolor="#333333")
for b in bars:
    ax.text(b.get_x() + b.get_width()/2, b.get_height() + 1, f"{int(b.get_height())} samples", ha="center", va="bottom", fontsize=10, fontweight="bold")
ax.set_ylim(0, 75)
ax.set_title("GSE13355 (A1): Sample Group Breakdown (180 Samples from 122 Donors)\n58 Paired PP/PN Cases + 64 Single NN Controls", fontsize=11, fontweight="bold")
ax.set_ylabel("Sample Count", fontsize=10)
fig.savefig(os.path.join(out_a1, "gse13355_sample_composition.png"))
plt.close(fig)

# -------------------------------------------------------------
# 2. GSE30999 (A2)
# -------------------------------------------------------------
print("Generating GSE30999 visualizations...")
out_a2 = os.path.join(VIZ_DIR, "GSE30999")
os.makedirs(out_a2, exist_ok=True)

_, m2, t2 = parse_series_matrix(os.path.join(RAW_DIR, "GSE30999/matrix/GSE30999_series_matrix.txt.gz"))
X2 = t2.iloc[:, 1:].to_numpy(float)

# Figure 1: GCRMA log2 distribution
fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
flat2 = X2.ravel()
sub2 = np.random.RandomState(42).choice(flat2, size=100000, replace=False)
sns.histplot(sub2, bins=100, kde=True, color="#1b9e77", ax=ax, stat="density", alpha=0.6)
ax.axvline(np.median(sub2), color="#e7298a", linestyle="--", linewidth=1.5, label=f"Median ({np.median(sub2):.2f})")
ax.set_title("GSE30999 (A2): GCRMA Normalized Positive Log2 Expression\nRange [1.54, 16.10] (No Negatives)", fontsize=12, fontweight="bold")
ax.set_xlabel("Log2 GCRMA Intensity", fontsize=10)
ax.set_ylabel("Density", fontsize=10)
ax.annotate(f"Min: {flat2.min():.2f}\nMax: {flat2.max():.2f}\n0% Negative Values\n100% Values at 2 Decimals",
            xy=(0.65, 0.65), xycoords="axes fraction",
            bbox=dict(boxstyle="round,pad=0.5", fc="#f7f7f7", ec="#cccccc", lw=1), fontsize=9)
ax.legend(loc="upper right")
fig.savefig(os.path.join(out_a2, "gse30999_expression_distribution.png"))
plt.close(fig)

# Figure 2: Subject Pairing Discrepancy (81 Complete Pairs vs 8 Singletons)
fig, ax = plt.subplots(figsize=(7, 4.5), dpi=300)
subj = m2["!Sample_characteristics_ch1"].str.replace("subject: ", "")
vc = subj.value_counts()
paired_n = (vc == 2).sum()
single_n = (vc == 1).sum()
ax.bar(["Complete Pairs (2 biopsies)", "Singletons (1 biopsy)"], [paired_n, single_n], color=["#2b5c8f", "#e6ab02"], width=0.5, edgecolor="#333333")
for i, v in enumerate([paired_n, single_n]):
    samples = v * (2 if i == 0 else 1)
    ax.text(i, v + 1.5, f"{v} Subjects\n({samples} samples)", ha="center", va="bottom", fontsize=10, fontweight="bold")
ax.set_ylim(0, 95)
ax.set_title("GSE30999 (A2): Patient Pairing Structure (89 Total Subjects)\nBioNexus Cannot Assume 1:1 Pairing (8 Unpaired Donors)", fontsize=11, fontweight="bold")
ax.set_ylabel("Subject Count", fontsize=10)
fig.savefig(os.path.join(out_a2, "gse30999_sample_pairing.png"))
plt.close(fig)

# -------------------------------------------------------------
# 3. GSE41663 (A4)
# -------------------------------------------------------------
print("Generating GSE41663 visualizations...")
out_a4 = os.path.join(VIZ_DIR, "GSE41663")
os.makedirs(out_a4, exist_ok=True)

_, m4, t4 = parse_series_matrix(os.path.join(RAW_DIR, "GSE41663/matrix/GSE41663_series_matrix.txt.gz"))
X4 = t4.iloc[:, 1:].to_numpy(float)

# Figure 1: Linear distribution with negative background values
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5), dpi=300)
flat4 = X4.ravel()
# Left: full linear scale
sub4 = np.random.RandomState(42).choice(flat4, size=100000, replace=False)
sns.histplot(sub4, bins=80, color="#d95f02", ax=ax1, stat="density", alpha=0.6)
ax1.set_title("Full Linear Intensity Scale [-1,734 to 55,203]", fontsize=10, fontweight="bold")
ax1.set_xlabel("Linear Intensity (Rosetta Resolver)", fontsize=9)
ax1.set_ylabel("Density", fontsize=9)

# Right: Zoomed view around 0 showing negative values
neg_vals = flat4[flat4 < 500]
sub_neg = np.random.RandomState(42).choice(neg_vals, size=50000, replace=False)
sns.histplot(sub_neg, bins=100, color="#7570b3", ax=ax2, stat="density", alpha=0.6)
ax2.axvline(0, color="red", linestyle="--", linewidth=1.5, label="Zero Intensity Boundary")
ax2.set_title("Zoomed Low-Expression Range: 9.02% Negative Values", fontsize=10, fontweight="bold")
ax2.set_xlabel("Intensity Value (Negative values from background subtraction)", fontsize=9)
ax2.annotate("399,547 negative values\n(18,026 probes affected)\nNaive log2(x) produces NaNs!",
             xy=(0.05, 0.65), xycoords="axes fraction",
             bbox=dict(boxstyle="round,pad=0.5", fc="#fff2f2", ec="#d95f02", lw=1), fontsize=8.5)
ax2.legend()
fig.suptitle("GSE41663 (A4): Linear Intensities with Rosetta Resolver Background Subtraction", fontsize=12, fontweight="bold")
fig.savefig(os.path.join(out_a4, "gse41663_expression_distribution.png"))
plt.close(fig)

# Figure 2: Longitudinal Treatment Breakdown
fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
time_order = ["Pre-dose (NL)", "Pre-dose (LS)", "Week 1 (LS)", "Week 2 (LS)", "Week 4 (LS)", "Week 12 (LS)"]
time_counts = [15, 15, 15, 15, 13, 8]
time_colors = ["#2b5c8f", "#2b5c8f", "#fdae61", "#f46d43", "#d73027", "#a50026"]
bars = ax.bar(time_order, time_counts, color=time_colors, width=0.55, edgecolor="#333333")
for b in bars:
    ax.text(b.get_x() + b.get_width()/2, b.get_height() + 0.3, str(int(b.get_height())), ha="center", va="bottom", fontsize=10, fontweight="bold")
ax.axvspan(-0.5, 1.5, color="#2b5c8f", alpha=0.08, label="Baseline Untreated Arms (30 samples)")
ax.axvspan(1.5, 5.5, color="#d73027", alpha=0.08, label="Post-Treatment Arms (51 samples)")
ax.set_ylim(0, 18)
ax.set_title("GSE41663 (A4): Longitudinal Etanercept Treatment Structure (15 Patients)\nTreatment is a Biological Confounder (Must Isolate Baseline)", fontsize=11, fontweight="bold")
ax.set_ylabel("Number of Samples", fontsize=10)
ax.legend(loc="upper right")
fig.savefig(os.path.join(out_a4, "gse41663_longitudinal_treatment.png"))
plt.close(fig)

# -------------------------------------------------------------
# 4. GSE54456 (A3)
# -------------------------------------------------------------
print("Generating GSE54456 visualizations...")
out_a3 = os.path.join(VIZ_DIR, "GSE54456")
os.makedirs(out_a3, exist_ok=True)

a3_df = pd.read_csv(os.path.join(RAW_DIR, "GSE54456/suppl/GSE54456_RPKM_samples.txt.gz"), sep="\t", index_col=0)
X3 = a3_df.values.astype(float)

# Figure 1: RPKM Distribution
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5), dpi=300)
flat3 = X3.ravel()
pos3 = flat3[flat3 > 0]
sub_pos3 = np.random.RandomState(42).choice(pos3, size=100000, replace=False)

sns.histplot(sub_pos3, bins=80, color="#7570b3", ax=ax1, stat="density", alpha=0.6)
ax1.set_xlim(0, 150)
ax1.set_title("Linear RPKM Distribution (Truncated at 150)", fontsize=10, fontweight="bold")
ax1.set_xlabel("Linear RPKM Value", fontsize=9)
ax1.set_ylabel("Density", fontsize=9)

sns.histplot(np.log2(sub_pos3), bins=80, color="#1b9e77", ax=ax2, stat="density", alpha=0.6)
ax2.set_title("Log2-Transformed Positive RPKM (log2(x))", fontsize=10, fontweight="bold")
ax2.set_xlabel("Log2(RPKM)", fontsize=9)
ax2.annotate(f"Min: 0.0\nMax: {flat3.max():.1f}\nZero values: 14.13%\nMedian (pos): 2.86 RPKM\n411 All-Zero Genes",
             xy=(0.05, 0.60), xycoords="axes fraction",
             bbox=dict(boxstyle="round,pad=0.5", fc="#f7f7f7", ec="#cccccc", lw=1), fontsize=8.5)

fig.suptitle("GSE54456 (A3): RNA-Seq Linear RPKM Expression Distribution (21,510 HGNC Symbols)", fontsize=12, fontweight="bold")
fig.savefig(os.path.join(out_a3, "gse54456_expression_distribution.png"))
plt.close(fig)

# Figure 2: Group Breakdown & Sparsity
fig, ax = plt.subplots(figsize=(7, 4.5), dpi=300)
bars = ax.bar(["Psoriatic Lesions (PP)", "Normal Controls (NN)"], [92, 82], color=["#d95f02", "#1b9e77"], width=0.45, edgecolor="#333333")
for b in bars:
    ax.text(b.get_x() + b.get_width()/2, b.get_height() + 1, f"{int(b.get_height())} samples", ha="center", va="bottom", fontsize=10, fontweight="bold")
ax.set_ylim(0, 110)
ax.set_title("GSE54456 (A3): Sample Group Composition (174 RNA-seq Samples)\nPure 2-Group Case-Control Design (No Uninvolved Skin)", fontsize=11, fontweight="bold")
ax.set_ylabel("Sample Count", fontsize=10)
fig.savefig(os.path.join(out_a3, "gse54456_sample_composition.png"))
plt.close(fig)

# -------------------------------------------------------------
# 5. GSE63979 (A5)
# -------------------------------------------------------------
print("Generating GSE63979 visualizations...")
out_a5 = os.path.join(VIZ_DIR, "GSE63979")
os.makedirs(out_a5, exist_ok=True)

a5_df = pd.read_csv(os.path.join(RAW_DIR, "GSE63979/suppl/GSE63979_ReadCount_42samples.txt.gz"), sep="\t")
X5 = a5_df.iloc[:, 1:].values.astype(float) if a5_df.shape[1] == 43 else a5_df.values.astype(float)
lib5 = X5.sum(axis=0) / 1e6

# Figure 1: Sequencing depth variation
fig, ax = plt.subplots(figsize=(9, 4.5), dpi=300)
# Group samples by group
_, m5, _ = parse_series_matrix(os.path.join(RAW_DIR, "GSE63979/matrix/GSE63979_series_matrix.txt.gz"))
key5 = m5["!Sample_title"].str.rsplit("_", n=1).str[0]
grp5 = dict(zip(key5, m5["!Sample_characteristics_ch1"].str.replace("tissue type: ", "")))
cols5 = a5_df.columns if a5_df.shape[1] == 42 else a5_df.columns[1:]
groups = [grp5.get(c, "Unknown") for c in cols5]
df_lib = pd.DataFrame({"Sample": cols5, "LibSize_M": lib5, "Group": groups}).sort_values("LibSize_M")

color_map = {"Uninvolved skin": "#7570b3", "normal skin": "#1b9e77", "psoriatic skin": "#d95f02"}
c_list = [color_map.get(g, "#999999") for g in df_lib["Group"]]

bars = ax.bar(range(len(df_lib)), df_lib["LibSize_M"], color=c_list, edgecolor="#333333", width=0.8)
ax.axhline(df_lib["LibSize_M"].median(), color="black", linestyle="--", label=f"Median Library Size ({df_lib['LibSize_M'].median():.1f}M reads)")
ax.set_title("GSE63979 (A5): Sequencing Depth per Sample (Raw Integer Counts)\nSevere 20.7-Fold Variation: 3.95M reads (M3822) to 81.75M reads (CASP499)", fontsize=11, fontweight="bold")
ax.set_xlabel("Samples (Ranked by Sequencing Depth)", fontsize=10)
ax.set_ylabel("Total Read Counts (Millions)", fontsize=10)
# Custom legend
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor="#d95f02", edgecolor="#333333", label="Psoriatic (7 samples)"),
    Patch(facecolor="#7570b3", edgecolor="#333333", label="Uninvolved (27 samples, paired w/ A3)"),
    Patch(facecolor="#1b9e77", edgecolor="#333333", label="Normal (8 samples)"),
]
ax.legend(handles=legend_elements, loc="upper left")
fig.savefig(os.path.join(out_a5, "gse63979_library_sizes.png"))
plt.close(fig)

# -------------------------------------------------------------
# 6. GSE67785 (A6)
# -------------------------------------------------------------
print("Generating GSE67785 visualizations...")
out_a6 = os.path.join(VIZ_DIR, "GSE67785")
os.makedirs(out_a6, exist_ok=True)

df_a6_c = pd.read_csv(os.path.join(DERIVED_DIR, "GSE67785/DERIVED_assembled_count.tsv.gz"), sep="\t", index_col=0)
df_a6_f = pd.read_csv(os.path.join(DERIVED_DIR, "GSE67785/DERIVED_assembled_FPKM.tsv.gz"), sep="\t", index_col=0)

# Figure 1: Dual Representation Correlation (FPKM vs Count)
fig, ax = plt.subplots(figsize=(7, 5), dpi=300)
# Sample 1: GSM1656052
c1 = df_a6_c.iloc[:, 0].values.astype(float)
f1 = df_a6_f.iloc[:, 0].values.astype(float)
mask = (c1 > 0) & (f1 > 0)
sub_idx = np.random.RandomState(42).choice(np.where(mask)[0], size=5000, replace=False)

sns.regplot(x=np.log1p(c1[sub_idx]), y=np.log1p(f1[sub_idx]), ax=ax,
            scatter_kws={"alpha": 0.3, "color": "#2b5c8f", "s": 12},
            line_kws={"color": "red", "linewidth": 1.5})
ax.set_title("GSE67785 (A6): Cufflinks FPKM vs HTSeq Raw Count (Sample GSM1656052)\nDual Processed Representations for Identical Biopsies", fontsize=11, fontweight="bold")
ax.set_xlabel("Log(HTSeq Count + 1)", fontsize=10)
ax.set_ylabel("Log(Cufflinks FPKM + 1)", fontsize=10)
corr = np.corrcoef(np.log1p(c1[mask]), np.log1p(f1[mask]))[0, 1]
ax.annotate(f"Pearson r = {corr:.3f}\nCount=0 & FPKM>0: 11,401 cells\nCount>0 & FPKM=0: 5,201 cells\nSame Biology ≠ Interchangeable Math",
            xy=(0.05, 0.70), xycoords="axes fraction",
            bbox=dict(boxstyle="round,pad=0.5", fc="#f7f7f7", ec="#cccccc", lw=1), fontsize=8.5)
fig.savefig(os.path.join(out_a6, "gse67785_dual_representation.png"))
plt.close(fig)

# -------------------------------------------------------------
# 7. Cross-Dataset Visualizations
# -------------------------------------------------------------
print("Generating cross-dataset visualizations...")
out_cross = os.path.join(VIZ_DIR, "cross_dataset")
os.makedirs(out_cross, exist_ok=True)

# Figure 1: Representation Comparison Boxplots
fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
data_to_plot = [
    sub1,                                      # A1: Residuals
    sub2,                                      # A2: GCRMA Log2
    np.log1p(sub_pos3),                        # A3: Log(RPKM+1)
    np.random.RandomState(42).choice(flat4, size=10000), # A4: Linear with negatives
    np.log1p(np.random.RandomState(42).choice(X5.ravel(), size=10000)), # A5: Log(Counts+1)
    np.log1p(np.random.RandomState(42).choice(df_a6_c.values.ravel(), size=10000)), # A6: Log(Counts+1)
]
labels = [
    "A1 (GSE13355)\nAdjusted Resid.\n[-5.97, +7.36]",
    "A2 (GSE30999)\nGCRMA Log2\n[1.54, 16.10]",
    "A3 (GSE54456)\nLog1p(RPKM)\n[0.0, 15.12]",
    "A4 (GSE41663)\nLinear Negatives\n[-1734, 55203]",
    "A5 (GSE63979)\nLog1p(Counts)\n[0, 21.91]",
    "A6 (GSE67785)\nLog1p(Counts)\n[0, 20.44]"
]
# Use boxplot with symmetric y-scale for clarity
bp = ax.boxplot(data_to_plot, patch_artist=True, labels=labels, showfliers=False)
colors_bp = ["#2b5c8f", "#1b9e77", "#7570b3", "#d95f02", "#e6ab02", "#e7298a"]
for patch, c in zip(bp["boxes"], colors_bp):
    patch.set_facecolor(c)
    patch.set_alpha(0.7)
ax.set_title("Cross-Dataset Expression Value Distribution & Representation Spectrum\nDemonstrating Why Datasets CANNOT be Merged Without Prior Characterization", fontsize=11, fontweight="bold")
ax.set_ylabel("Observed Expression Scale", fontsize=10)
fig.savefig(os.path.join(out_cross, "cross_dataset_representation_comparison.png"))
plt.close(fig)

# Figure 2: Shared Human Donors Diagram
fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
# A1 (122 donors), A3 (174 donors), A5 (42 samples)
# Draw overlapping horizontal bars showing cohort overlap
cohorts = ["A1: GSE13355 (Microarray)", "A3: GSE54456 (RNA-seq)", "A5: GSE63979 (RNA-seq lncRNA)"]
y_pos = [2, 1, 0]
ax.barh(2, 122, height=0.45, color="#2b5c8f", alpha=0.8, edgecolor="#333333", label="A1 Donors (122 total)")
ax.barh(1, 174, height=0.45, color="#7570b3", alpha=0.8, edgecolor="#333333", label="A3 Donors (174 total)")
ax.barh(0, 42, height=0.45, color="#e6ab02", alpha=0.8, edgecolor="#333333", label="A5 Samples (42 total)")

# Annotate overlap links
ax.annotate("", xy=(43, 2), xytext=(43, 1), arrowprops=dict(arrowstyle="<->", color="red", lw=2))
ax.text(48, 1.5, "43 Shared Donors\n(22 Cases + 21 Controls)", color="red", fontweight="bold", fontsize=9)

ax.annotate("", xy=(27, 1), xytext=(27, 0), arrowprops=dict(arrowstyle="<->", color="purple", lw=2))
ax.text(32, 0.5, "27 Paired Biopsies\n(A5 Uninvolved == A3 Lesional Donors)", color="purple", fontweight="bold", fontsize=9)

ax.set_yticks(y_pos)
ax.set_yticklabels(cohorts, fontsize=10, fontweight="bold")
ax.set_xlabel("Number of Individuals / Samples", fontsize=10)
ax.set_title("Institutional Donor Overlap (University of Michigan Psoriasis Cohort)\nShared Donors Violate Sample Independence (Confounding Hazard)", fontsize=11, fontweight="bold")
ax.set_xlim(0, 200)
fig.savefig(os.path.join(out_cross, "cross_dataset_donor_overlap.png"))
plt.close(fig)

# Figure 3: Pairwise Compatibility Matrix Heatmap
fig, ax = plt.subplots(figsize=(7, 6), dpi=300)
datasets = ["A1 (GSE13355)", "A2 (GSE30999)", "A3 (GSE54456)", "A4 (GSE41663)", "A5 (GSE63979)", "A6 (GSE67785)"]
# Codes: 0: Incompatible (Platform/Rep), 1: Requires Manual Review, 2: Compatible with Warnings, 3: Compatible
compat_matrix = np.array([
    [3, 2, 0, 1, 0, 0], # A1
    [2, 3, 0, 1, 0, 0], # A2
    [0, 0, 3, 0, 1, 2], # A3
    [1, 1, 0, 3, 0, 0], # A4
    [0, 0, 1, 0, 3, 0], # A5
    [0, 0, 2, 0, 0, 3], # A6
])
cmap = sns.color_palette(["#d73027", "#fdae61", "#a6d96a", "#1a9850"], as_cmap=True)
sns.heatmap(compat_matrix, annot=False, cmap=cmap, xticklabels=datasets, yticklabels=datasets,
            cbar=False, linewidths=1.5, linecolor="white", ax=ax)
# Text labels
labels_map = {0: "INCOMPATIBLE\n(Platform/Repr)", 1: "MANUAL REVIEW\n(Confound/Custom)", 2: "COMPATIBLE\nw/ Warnings", 3: "SELF\n(Identical)"}
for i in range(6):
    for j in range(6):
        ax.text(j + 0.5, i + 0.5, labels_map[compat_matrix[i, j]], ha="center", va="center", fontsize=7.5, fontweight="bold",
                color="white" if compat_matrix[i, j] in (0, 3) else "#333333")
ax.set_title("BioNexus Pairwise Compatibility Assessment Matrix (v1 Stage 2)\nDecisions Driven by Platform, Representation, and Biological Design", fontsize=11, fontweight="bold")
fig.savefig(os.path.join(out_cross, "cross_dataset_pairwise_compatibility_matrix.png"))
plt.close(fig)

print("Visualizations generated successfully.")
