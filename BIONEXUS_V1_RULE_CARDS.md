# BioNexus V1 — Rule Cards (companion to BIONEXUS_V1_CONSOLIDATED_PLAN.md)

All cards are **Proposed**. Only the owner can mark a rule Approved. "Tests" lists the minimum: P = positive, N = negative, E = edge. Evidence labels as in the plan. No threshold below is invented: where a value is needed it is derived from the data (tolerance from precision) or is an experiment output.

Card fields: Definition/purpose · Eligibility · Action/parameters · Evidence/assumptions · Outputs (originals preserved) · Tests · Validation · Limitations.

---
## Group G — Gate and file handling (all ACCEPT-M1)

**G-01 Scope gate.** Purpose: V1 only processes human bulk RNA-seq gene-level matrices (OC-1). Eligibility: every upload. Action: read declared technology/organism/level; compare with value-based representation evidence (R-01). Declared and evidence disagree, or out of scope → refuse with a one-line reason; nothing else runs. Evidence: spec §3, §5; OC-1. Output: scope record. Tests: P human RNA-seq counts accepted · N microarray-like (negatives, probe IDs) refused · E declared "RNA-seq" but values look like log-intensity → need_fact. Validation: synthetic; boundary refusals on A1, A2, A4. Limits: cannot detect a false declaration with no value evidence.

**G-02 Parse normalization.** Purpose: read delimiter, quoting, BOM, ragged header safely. Action: normalize into a derived file; log each change. Tests: P tab/comma/BOM · N unreadable binary → blocked · E ragged header (extra/missing label column). Limits: ambiguous header → not_assessable, not a guess.

**G-03 Orientation.** Purpose: genes×samples vs samples×genes. Action: fix only when independent signals agree (ID patterns in rows vs columns, dimension contrast, metadata sample IDs matching one axis); otherwise need_fact. Tests: P clearly transposed · N already correct · E square matrix → need_fact. Limits: signals are structural, no thresholds.

**G-04 Originals preserved.** Action: SHA-256 on input; all outputs separate files; originals read-only. Tests: hash identical after run (AC2). Limits: none.

---
## Group M — Samples and metadata (ACCEPT-M1)

**M-01 Sample matching.** Tier 1 exact ID; tier 2 normalized ID (case, whitespace, punctuation, documented GEO/GSM mapping); tier 3 positional match only when counts equal and the owner-visible file order is documented. Identity key is always (study, sample). Tests: P exact · N same stem different studies not merged · E duplicates in metadata.
**M-02 Fuzzy match.** Candidates only; never auto-accept → fact request with candidates, evidence, consequence. Tests: P ambiguous pair listed · N no silent mapping.
**M-03 Tier A metadata.** Fields required for compatibility (condition, tissue, organism, study design…) per spec §17; missing → F naming the field. Tests: P complete · N missing condition → F · E condition present but unmapped label.
**M-04 Exact duplicates.** Duplicate sample IDs/columns identical → record and keep one with note; same ID different values → F. Tests: P/N/E as stated.
**M-05 Donor overlap.** Exact study-qualified donor IDs only; overlap keeps all samples, annotates donor, J = limited. Tests: P shared donor annotated · N similar-looking IDs not linked · E donor ID absent → no claim. Validation: A3/A5 natural overlap (documented). Limits: undetectable overlap stays unknown (stated).
**M-06 Condition/subgroup.** Explicit metadata and label map only; no subtype inference. Tests: P mapped labels · N "lesional skin" not turned into a subtype · E conflicting labels → F.
**M-07 Study–condition structure.** none = every condition level in ≥2 studies; partial = some in one study only; complete = each in one study only. Structural, no thresholds. Tests: three fixtures + E single study → not applicable.

---
## Group R — Representation (R-01, R-02, R-05, R-06 ACCEPT-M1; R-03 CONDITIONAL; R-04 ACCEPT-GATED)

**R-01 Representation evidence record.** Records structural facts: integer-ness, non-negativity, presence of negatives, column sums, minimum value, ratio of zeros. Produces candidate labels R1–R7 with evidence; changes no value. Tests: P integer counts → R1 candidate · N negative values → not R1 · E non-integers with constant column sums → CPM/TPM candidate. Limits: values alone never prove a representation.
**R-02 Linear vs log.** Documentation first; value patterns only supporting; undocumented → F. Tests: P documented log2 · N undocumented → F · E log values that look like linear.
**R-03 Constant-sum evidence (CONDITIONAL).** Column sums equal to a constant within a tolerance derived from the file's printed precision support CPM/TPM. Experiment: simulated rounding at several precisions. Deadline M2, else DEFERRED.
**R-04 Log offset/base (GATED).** From documentation; minimum-value ties as supporting evidence only. Validation: synthetic.
**R-05 Universe completeness.** Compare uploaded feature universe with the declared annotation; incompleteness lowers the Q grade as a limitation, never blocks. Tests: P complete · N subset → limitation.
**R-06 NA handling.** Genes with any NA excluded from the joint matrix and listed; no imputation; whole-sample NA → F.

---
## Group N — Gene identifiers (N-01..N-03 GATED, N-05 M1, N-04 DEFERRED)

**N-01 Versionless Ensembl mapping.** Strip version; pin annotation release; record release. Tests: P ENSG with version · N non-Ensembl id not guessed · E retired IDs → listed unmapped.
**N-02 Symbol/Entrez → Ensembl.** One-to-one only; one-to-many excluded and listed; never merged automatically. Validation: A3/A6 symbols (19,448 shared) vs synthetic ambiguity cases.
**N-03 Many-to-one aggregation.** Counts and TPM: sum. RPKM/FPKM: only documented isoforms of one gene from one quantifier, else convert to TPM first. Tests: P sum preserves total · N non-additive RPKM refused · E one source ID mapped to two genes.
**N-05 Intersection.** Joint matrix over shared genes only; presence table kept; no zero-fill. Library-size/proportion totals computed over the full uploaded universe first.
**N-04** custom-assembly coordinate mapping: DEFERRED (Option 2A).

---
## Group T — Transformations (GATED unless noted)

**T-01 Count proportions (R1/R2/R3 → log-CPM).** Action: x/Σx over the study's full universe ×1e6, then log2(·+c). R2 never rounded. Evidence: identity 2 [M]; Law 2014 [E]. Tests: P any per-sample scaling gives identical result · N R4/R5 input refused · E zero-sum sample → F. Validation: exactness on synthetic; E-UNIV.
**T-02 RPKM/FPKM → TPM.** TPM_g = 1e6·x_g/Σx. Eligible when the feature universe is complete for the quantification (R-05) and one quantifier family. Evidence: Zhao 2020 [E]. Tests: P exact on synthetic · N partial universe → Q limitation · E mixed RPKM/FPKM labelled.
**T-03 log2(x + c).** c matched to a log-scale partner's offset; otherwise default 1 (convention) with sensitivity report; never log of negatives. Validation: E-OFFSET.
**T-04 Invert log.** Only with documented base and c; else F.
**T-05 Length bridge (CONDITIONAL).** Needs the gene lengths used by the quantifier. Proceeds only if E-A6 shows stable gene-wise agreement. Deadline M3, else DEFERRED. Without lengths: separate tracks with the unlocking evidence named.
**T-06 REJECTED:** pooling R1+R2 as counts (needs rounding).
**T-07 Forbidden operations (ACCEPT-M1 as refusal tests):** normalized → counts, rounding, zero-fill, imputation, log of negatives, ComBat-seq on non-counts, rescale without lengths. Each has a refusal test.

---
## Group B — Batch (see plan section 5)

**B-01 Batch assessment (GATED).** Reports numbers: PCA, RLE, variance share by study and by condition. No "strong/weak" cut-offs. Validation: synthetic with known effects.
**B-02 Eligibility (GATED).** Conditions 1–6 of plan section 5.3. ≥2 samples per batch is a conservative design constraint [P], not a tool requirement. Tests: P eligible fixture · N each condition failing separately · E single-sample batch.
**B-03 ComBat-seq on all-R1 groups; B-04 ComBat on matched log space (GATED).** Condition of interest passed as covariate. Validation: E-BATCH + set B. Both ship disabled until both pass.
**B-05 Always keep uncorrected; structural post-checks (M1).** Dimensions, labels, NaN/Inf, non-negative integers for ComBat-seq; failure discards the corrected matrix.
**B-06 REJECTED:** numeric "strong batch effect" threshold.

---
## Group J/V — Compatibility, validation (ACCEPT-M1)

**J-01 T/Q/J grading. J-02 Q checklist** (annotation, quantifier, library prep, layout, strandedness; each differing factor adds a limitation, no score). **J-03 Limitation catalogue L1–L6** (material test: no approved rule removes it AND it can change interpretation/use AND the user can act or must know; supervisor review OD-4). **J-04 Fixed combination order** (blocked → incompatible; need_fact/need_decision/not_assessable → requires_manual_review; limitation → compatible_with_warnings; else compatible). **J-05 Rule-gap record** for uncovered cases (not_assessable, shown as "BioNexus cannot assess this case yet"). **V-01 Deterministic output checks. V-02 Provenance per derived file** (input hash, rule id+version, parameters, software versions).
Tests for each: one fixture per branch of J-04; one undefined-case fixture for J-05; trace test for V-02.

---
## Deferred / rejected summary
X-01 sex-label check (DEFERRED) · X-02 auto filtering of mixed feature types (REJECTED, spec §13) · X-03 biotype restriction (DEFERRED) · N-04 (DEFERRED) · T-06, B-06 (REJECTED).
