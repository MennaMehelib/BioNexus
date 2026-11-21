# BioNexus V1 — Consolidated Preprocessing, Rule-Validation and Execution Plan

| | |
|---|---|
| Date | 2026-11-20 |
| Replaces | The design-review cycle (V1–V4). This is the working baseline. New rules enter only through a failing test (section 3.4) |
| Boundaries | Design only. No project file, Skills Pack file, test or script was modified. No test was run. U1–U3 data were not accessed (see 4.1 for what a project document itself lists) |
| Status | **Approved by the owner as the working baseline on 2026-11-21.** Rules marked GATED or CONDITIONAL remain proposed and disabled until their validation passes. (Original status line: everything was proposed until you approve the two items in section 8. "Approved" means approved by you; the AI never marks a rule approved.) |

**Evidence labels.** [M] mathematical identity, checkable by a unit test. [E] published, read in this or an earlier session (named). [O] observation in a development dataset, from project files. [H] hypothesis, with a named experiment. [P] my design decision.

**Source check (corrected 2026-11-21).** `PREPROCESSING_DECISION_MAP.md` exists (it is in the Project knowledge documents, created 2026-11-17, and the owner confirms it exists). The earlier wording that the owner said it was not in the repository was wrong. It is **not relied on** for this plan or for Nemotron's tasks, by the owner's instruction, because its authority status is not established. Every authority cited below is `AGENT_INSTRUCTIONS.md` (read in full this session), `dataset_sources.md`, `rule_coverage_update.md`, `unresolved_scientific_questions.md` (all read this session as Project documents) or `docs/VALIDATION_PLAN.md` (Skills Pack).

---

## 1. Independent assessment of V4

I read V4 in full and compared it with the real V3 (58,718 bytes on my disk).

**What V4 corrected well**

| Item | Verdict |
|---|---|
| CPM is not TPM (no gene-length division) | Correct and useful. The valid route is count *proportions*, not "TPM-like" (section 2) |
| R4 + R5 and R3 + R4/R5 "conditional, not automatic" | Correct direction. Conditions are right: feature universe, same length definition, same annotation |
| A6 evidence gaps flagged `[NV]` (read layout, gene lengths, feature universe) | Correct, and they match `BIO_NEXUS_MASTER_KNOWLEDGE.md` (A6 read layout `[NV]`) |
| Honest account of its own earlier draft | Good practice |

**What remains wrong or questionable**

| # | Problem in V4 | Evidence |
|---|---|---|
| 1 | Its own sections disagree. The matrix (5.3) says RPKM/FPKM → TPM is "never automatic", but the route table (7.3) says "yes, class R under the policy" and the stage table (S7) says "rescale to proportions before gene intersection" | V4 lines 167 (matrix text), 338 and 326 (route and stage tables) |
| 2 | The material-limitations table (6.2) is garbled. The "Always internal" column was merged into the "Content" column, so L1 is shown with "Orientation fixed, headers normalized" as its content | V4 section 6.2 |
| 3 | The change log claims corrections that are not in the body. Items 5 and 6 of section 12 ("three-cause split", "pre-approval vs post-approval assessments") do not appear in the V4 text, and section 16 says the same items were "already correct in V3, no change needed" | grep of V4 |
| 4 | Items 8–10 of section 12 list "corrections" that are non-changes (V3 already had four states, approval, no Stage B) | V3 §5.2, §5.6 |
| 5 | "No contradictions remain" (section 17) is false, given points 1 and 2 | — |
| 6 | MR-17 says CPM → TPM is "mathematically invalid, prohibited". Overstated. With the gene lengths a conversion exists (TPM ∝ CPM / L) [M]. What is invalid is a rescale *without* lengths | Rule T-05 below |
| 7 | V4 says it read V3 at 54,882 bytes. My V3 is 58,718 bytes. I cannot tell whether it read the same file | — |
| 8 | It cites `PREPROCESSING_DECISION_MAP.md` as authority; the file exists but is not an approved source, and the owner's instruction is not to rely on it | See source check |
| 9 | It keeps a runtime "policy sheet" and per-run correction approval, which your new requirement removes | Sections 5, 8 |

**Net:** V4's scientific tightening of the matrix is mostly right, but it is a more cautious version of the same design, and its self-checks are not reliable. This plan replaces it rather than patching it.

---

## 2. Final preprocessing strategy

### 2.1 Principle

Every incompatibility is first tested for a valid preprocessing route. A dataset is declared non-integrable only when no valid route exists *even with evidence the user could supply*, or when integrating would misrepresent biology.

### 2.2 Five outcome categories

| Code | Category | Example |
|---|---|---|
| C1 | **Directly compatible** | Two raw-count studies, same gene model |
| C2 | **Compatible through preprocessing** (automatic) | RPKM study + TPM study: convert RPKM to TPM, log both |
| C3 | **Needs specific evidence first** (a fact request, class F) | Raw counts + FPKM: the gene lengths used by the FPKM quantifier are needed |
| C4 | **Integrable, limited for joint inference** | Study and condition fully overlap: matrix is built, cross-study comparison is flagged |
| C5 | **Cannot be combined without misrepresenting biology** | Different tissue; different organism; normalized values to "counts" |

### 2.3 Three target spaces

| Space | Content | Accepts directly | Accepts with evidence |
|---|---|---|---|
| **SP-C** counts | Raw integer counts | R1 | — |
| **SP-P** log2 count-proportion (log-CPM) | `log2(CPM + c)`. Established representation for linear-model analysis of counts [E: Law 2014 (voom), read: "we work with log-counts per million"] | R1, R2, R3 (per-sample-scaled counts without length normalization) | R4, R5 with gene lengths (T-05) |
| **SP-T** log2 TPM | `log2(TPM + c)` | R4, R5 | R1, R2, R3 with gene lengths (T-05) |

R6 (log-scale) is first inverted if base and offset are documented (T-04) and then follows its native route.

### 2.4 Mathematical identities the routes rest on [M]

1. `RPKM_g = 1e9·c_g / (L_g·N)`; `TPM_g = 1e6·(c_g/L_g) / Σ_h(c_h/L_h) = 1e6·RPKM_g / Σ_h RPKM_h`. Zhao 2020 (read) states the TPM–RPKM proportionality and the formula; FPKM is RPKM with fragments for reads (Zhao 2020, read).
2. `CPM_g = 1e6·c_g / N`. If `n_gj = c_gj / s_j` for any per-sample factor `s_j` (library-size scaling, TMM, size factors), then `n_gj / Σ_h n_hj = c_gj / Σ_h c_hj`. So *any* per-sample-scaled count matrix returns exact count proportions once rescaled to a constant sum.
3. Given the lengths used by the quantifier, `c_g ∝ x_g·L_g` for RPKM/FPKM/TPM `x`, so count proportions are `x_g L_g / Σ x_h L_h`. This needs the *same* lengths. Cufflinks-type FPKM uses effective lengths, which may differ from merged-exon lengths, so this route stays conditional (T-05, `[H]`).
4. `y = log2(x + c)` is invertible: `x = 2^y − c`, if base and `c` are known.
5. Counts and TPM are additive across disjoint features of one gene. RPKM/FPKM are not additive unless first converted to TPM.

### 2.5 Selection ladder (deterministic, per integration group)

1. All R1 → SP-C. This is the only space where ComBat-seq can apply.
2. Else all in {R1, R2, R3, or R6 derived from them} → SP-P.
3. Else all in {R4, R5, or R6 derived from them} → SP-T.
4. Else mixed count-derived and length-normalized → needs gene lengths (C3). With lengths and a passed T-05 validation → SP-P. Otherwise separate tracks, with the reason and exactly what evidence would unlock the merge.
5. Overlapping alternative groups (A+B and A+C valid, B+C not) → one matrix per valid group, no choice demanded. Using them is a downstream decision.

### 2.6 Execution order inside the preprocessing stage

(1) invert log if R6 → (2) convert to the target space **on the study's own full uploaded universe** → (3) apply gene ID mapping and many-to-one aggregation → (4) `log2(x + c)` → (5) intersect genes (never zero-fill). Conversion happens *before* mapping because mapping can remove genes, and removing genes changes the totals the conversion depends on.

### 2.7 Scenario routes

| ID | Scenario | Cat. | Route | Conditions and evidence | Output | Failure → fallback |
|---|---|---|---|---|---|---|
| P-01 | R1 + R1, same annotation | C1 | SP-C | Same gene model | Counts matrix | — |
| P-02 | R1 + R1, different ID type or annotation release | C2 | Map to versionless Ensembl gene ID (N-01, N-02) | ID type detected; pinned annotation | Mapping artifact + matrix | No shared genes → no joint matrix (C5, technical). Ambiguous genes excluded and listed |
| P-03 | Custom assembly IDs (A5-type) | out of V1 | None | Option 2A of `unresolved_scientific_questions.md` (coordinate lift-over is beyond V1) | Study kept standalone | Unmapped; reported once |
| P-04 | R1 + R2 (expected counts) | C2 | SP-P (T-01). R2 is not rounded | Library size = sum over the study's universe | log-CPM both | If R2 units undocumented → F |
| P-05 | R1/R2 + R3 (CPM or scaled counts) | C2 | SP-P (T-01, identity 2) | R3 is a length-free scaling (documented or F) | log-CPM | Unknown normalization → F |
| P-06 | R4 + R5 | C2 | SP-T: R5 → TPM (T-02), then log | Same quantification universe (uploaded universe) | log-TPM | Universe incompleteness lowers Q grade (limitation), not a block |
| P-07 | R5 + R5 (RPKM and FPKM mixed) | C2 | SP-T via T-02 | As P-06 | log-TPM | Pipeline differences → Q = conditional (limitation L4) |
| P-08 | Count-derived + length-normalized | C3 | T-05 bridge to SP-P | Gene lengths used by the quantifier; validation E-A6 passed | log-CPM | No lengths → separate tracks, reason stated |
| P-09 | Log-scale + linear partner | C2 | Invert (T-04) or transform partner with the **same offset** `c` | Base and `c` documented | One space | Undocumented → F |
| P-10 | Different library prep, strandedness, read layout | C4 | No preprocessing removes it | Metadata checklist (J-02) | Matrix + limitation L4 | — |
| P-11 | Study–condition structure partial / complete | C4 | None. Correction not eligible | M-07 | Matrix, J limited / not_suitable | — |
| P-12 | Shared donors across studies | C4 | Keep all samples, annotate donor ID | Exact study-qualified IDs | Matrix, J limited | Identity uncertain → F |
| P-13 | Duplicate gene rows | C2 | Exact duplicates collapsed with record; many-to-one aggregation by space (N-03) | Distinct source IDs for one gene | Derived matrix | Identical ID with different values → F |
| P-14 | NA values | C2 | Genes with any NA excluded from the joint matrix, listed. No imputation | — | Complete-case gene set | A whole sample NA → F |
| P-15 | Missing Tier A metadata | C3 | F request naming the field | — | — | — |
| P-16 | Different organism or tissue, not gene-level, not bulk RNA-seq | C5 | None | Established evidence | Reason and nothing else | — |

**User interaction at runtime has only two kinds of request: a missing fact (F), or nothing.** Owner policy is decided at design time (section 5), not at runtime.

### 2.8 Experiments that settle the open scientific points (all on A or synthetic data)

| Exp. | Question | Data | Done when |
|---|---|---|---|
| E-UNIV | Should proportions be computed over the study's own universe or over the intersection universe? | Synthetic with known true abundance and different universes | One default chosen by recovery error; recorded in T-01/T-02 |
| E-OFFSET | Sensitivity to the log offset `c` | Synthetic + A3, A6 (A6 FPKM has 1,325 values below 1e-10, so log without an offset is unsafe: `BIO_NEXUS_MASTER_KNOWLEDGE.md`, `[VF]` citing `GSE67785_report.md`) | Default `c` confirmed or revised before freeze |
| E-A6 | Do count-derived and FPKM-derived proportions agree for the same A6 samples, up to a constant gene factor (the implied length)? | A6 counts and FPKM (same 28 samples) | Gene-wise ratio is stable across samples → T-05 enabled for same-quantifier cases; otherwise T-05 deferred |
| E-BATCH | Do ComBat-seq and ComBat recover a known effect and keep a known condition signal? | Synthetic with injected batch and condition effects, with and without confounding | Pre-registered criteria met → B-03/B-04 may enable |

---

## 3. Consolidated rule register (finite)

### 3.1 Status vocabulary

| Status | Meaning |
|---|---|
| **ACCEPT-M1** | Deterministic or structural. Implement in the first milestone; needs synthetic tests only |
| **ACCEPT-GATED** | Scientifically sound; implement, but **disabled** until its validation (listed) passes on synthetic data and set B |
| **CONDITIONAL** | Needs a named experiment or evidence. Has a deadline; if not met it is deferred, not kept open |
| **REJECTED** | Invalid or unnecessary. Reason given |
| **DEFERRED** | Outside V1 |

### 3.2 Register

Full cards (definition, eligibility, action, evidence, output, tests, validation, limits) are in `BIONEXUS_V1_RULE_CARDS.md`.

| ID | Rule | From | Status | Validation required |
|---|---|---|---|---|
| G-01 | Scope gate: human, bulk RNA-seq, gene-level, declared | spec §3, §5; OC-1 | ACCEPT-M1 | Synthetic + boundary refusal tests |
| G-02 | Parse normalization (delimiter, quotes, BOM, ragged header) | spec §7 | ACCEPT-M1 | Synthetic |
| G-03 | Orientation auto-fix on agreeing signals | spec §8 | ACCEPT-M1 | Synthetic transposed/ambiguous |
| G-04 | Originals preserved, checksums, derived files separate | spec §31–32 | ACCEPT-M1 | Hash tests |
| M-01 | Sample matching tiers 1–3 | spec §16 | ACCEPT-M1 | Synthetic + A |
| M-02 | Fuzzy match = candidates only → F | spec §16 | ACCEPT-M1 | Synthetic |
| M-03 | Tier A metadata completeness → F | spec §17 | ACCEPT-M1 | Synthetic |
| M-04 | Exact duplicate samples and genes detected | spec §20 | ACCEPT-M1 | Synthetic |
| M-05 | Donor overlap by exact study-qualified IDs | spec §14, §25 | ACCEPT-M1 | Synthetic + A3/A5 natural overlap |
| M-06 | Condition and subgroup from explicit metadata and label map | spec §14–15 | ACCEPT-M1 | Synthetic |
| M-07 | Study–condition structure: none / partial / complete | spec §25 | ACCEPT-M1 | Synthetic |
| R-01 | Representation evidence record, structural facts only | MR-1 | ACCEPT-M1 (revised) | Synthetic + A |
| R-02 | Linear vs log: documentation first; values are supporting evidence only; undocumented → F | MR-2 | ACCEPT-M1 (revised) | Synthetic |
| R-03 | Constant-sum column evidence for CPM/TPM (tolerance from data precision) | MR-1 | CONDITIONAL → deadline M2, test by simulation | Synthetic |
| R-04 | Log base/offset from documentation; minimum-value ties as supporting evidence | MR-2 | ACCEPT-GATED | Synthetic |
| R-05 | Universe-completeness evidence (feeds Q grade, not a block) | V4 | ACCEPT-M1 | Synthetic |
| R-06 | NA handling: complete-case genes, no imputation | MR-14 | ACCEPT-M1 | Synthetic |
| N-01 | Versionless Ensembl gene mapping, pinned release | spec §11–12 | ACCEPT-GATED | Synthetic + A |
| N-02 | Symbol/Entrez → Ensembl; one-to-many excluded and listed | spec §12 | ACCEPT-GATED | Synthetic + A3/A6 symbols |
| N-03 | Many-to-one aggregation by space | MR-4 | ACCEPT-GATED (revised) | Synthetic sum-preservation |
| N-04 | Custom-ID coordinate mapping | gap | **DEFERRED** (Option 2A) | — |
| N-05 | Gene intersection and presence table; no zero-fill | spec §18 | ACCEPT-M1 | Synthetic |
| T-01 | R1/R2/R3 → count proportions (log-CPM space) | new | ACCEPT-GATED | Synthetic exactness; E-UNIV |
| T-02 | R5 → TPM (RPKM/FPKM per-sample rescale) | MR-5 | ACCEPT-GATED | Synthetic exactness; E-UNIV |
| T-03 | `log2(x + c)`; `c` matched to a log partner, else default 1 | MR-6 | ACCEPT-GATED | E-OFFSET |
| T-04 | Invert log when base and `c` are documented | new | ACCEPT-GATED | Synthetic |
| T-05 | Length bridge between count-derived and length-normalized | MR-5, MR-17 (revised) | **CONDITIONAL** → E-A6, deadline M3 | E-A6 + synthetic |
| T-06 | R1 + R2 pooled in count space | MR-3 | **REJECTED** (rounding forbidden; replaced by T-01) | — |
| T-07 | Forbidden set: normalized → counts, rounding, zero-fill, imputation, log of negatives, ComBat-seq on non-counts, rescale without lengths | spec §2, §22 | ACCEPT-M1 as refusal tests | Synthetic refusal tests |
| B-01 | Batch assessment: numbers, PCA, RLE, variance by study (report only) | MR-10 | ACCEPT-GATED | Synthetic with known effects |
| B-02 | Correction eligibility (structural, section 5.3) | MR-16 | ACCEPT-GATED | Synthetic; E-BATCH |
| B-03 | ComBat-seq on all-R1 groups | spec §28 | ACCEPT-GATED | E-BATCH + set B |
| B-04 | ComBat on a matched log space | spec §28 | ACCEPT-GATED | E-BATCH + set B |
| B-05 | Uncorrected matrix always kept; structural post-checks | MR-11 | ACCEPT-M1 | Synthetic |
| B-06 | Numeric thresholds for "strong" effect | MR-10 | **REJECTED** (numbers reported, none invented) | — |
| J-01 | T / Q / J grading | V3 | ACCEPT-M1 | Synthetic |
| J-02 | Q grade by metadata checklist (annotation, quantifier, library prep, layout, strandedness) | MR-7 | ACCEPT-M1 | Fixtures differing in one factor |
| J-03 | Material-limitation catalogue L1–L6 | MR-12 | ACCEPT-M1 | Supervisor review (OD-4) |
| J-04 | Fixed state-combination order | V3 | ACCEPT-M1 | Synthetic |
| J-05 | Rule-gap record for uncovered cases | V3 | ACCEPT-M1 | Synthetic undefined case |
| V-01 | Deterministic output checks | V3 | ACCEPT-M1 | Synthetic |
| V-02 | Provenance record per derived file | spec §32 | ACCEPT-M1 | Trace test |
| X-01 | Sex-label sanity check | MR-15 | **DEFERRED** | — |
| X-02 | Automatic filtering of mixed feature types | MR-13 | **REJECTED** (spec §13: filtering needs an approved rule; V1 reports) | — |
| X-03 | Biotype restriction for library-prep mismatch | new idea | **DEFERRED** (no validated trigger) | — |

### 3.3 MR-1 to MR-17 mapping

MR-1 → R-01, R-03 · MR-2 → R-02, R-04 · MR-3 → T-06 (rejected), T-01 · MR-4 → N-03 · MR-5 → T-02, T-05 · MR-6 → T-03 · MR-7 → J-02 · MR-8 → M-01 to M-05 · MR-9 → M-07 · MR-10 → B-06 (rejected), B-01 · MR-11 → B-05 · MR-12 → J-03 · MR-13 → X-02 · MR-14 → R-06 · MR-15 → X-01 · MR-16 → B-02 · MR-17 → T-07, T-05.

**MR-16 resolved.** I read the `sva` manual (bioc.r-universe.dev). It is silent on single-sample batches and on a minimum batch size, and it describes the ComBat-seq input only as "raw count matrix". So there is no tool rule to cite. B-02 therefore uses a conservative design constraint of mine: at least two samples per batch, because a batch-specific variance cannot be estimated from one sample. It is tested synthetically.

### 3.4 Stopping rule

- **The register above is closed.** No new rule is added except in response to a failing test or a defect, and each addition must carry a rule card.
- **Deadlines.** R-03 by the end of M2, T-05 by the end of M3. A CONDITIONAL rule that misses its deadline becomes DEFERRED automatically.
- **Freeze** at the end of M4. A rule that has not passed its validation is shipped disabled and documented as such.

---

## 4. Dataset lifecycle: A → B → U

### 4.1 What the project files show

| Set | Status in the files | Source |
|---|---|---|
| **A** (A1–A6) | Downloaded. 18 of 18 raw files and the platform file match recorded sizes and SHA-256, read-only | `dataset_sources.md` §1–2 |
| A, in V1 scope | **A3** (RNA-seq RPKM, 21,510 × 174; library layout is a documented conflict between files, item C-12, so not relied on), **A5** (raw counts, custom IDs, cannot be mapped), **A6** (counts plus FPKM, same 28 samples, read layout `[NV]`) | `BIO_NEXUS_MASTER_KNOWLEDGE.md`, `rule_coverage_update.md` |
| A, out of V1 scope | A1, A2, A4: historical evidence and boundary-refusal tests only | OC-1 |
| **B** | **Not defined.** No accession list and no download. Only role hints: B1 (GTEx, TPM, Ensembl IDs), B2 (atopic dermatitis, different disease), B3 (blood, different tissue) | `rule_coverage_update.md`; `BIO_NEXUS_MASTER_KNOWLEDGE.md` notes the B definition as missing |
| **U** | Not downloaded; the project document records "0 paths found". The same document lists the accessions as locked | `dataset_sources.md` §2 |

**Consequences.** The only in-scope natural data are three RNA-seq datasets. A5 and A6 are the only count datasets, and A5 cannot be mapped, so **no natural development pair can exercise the count and ComBat-seq path**. Synthetic fixtures and set B carry that weight.

**One conflict only you can resolve.** The Stage 1 notes name one accession as an integration candidate, and `dataset_sources.md` lists the same accession in the locked Unseen set. I treat it as **locked U** and will not use it until you say otherwise (OD-3). I did not look at any dataset, only at what the project document says.

### 4.2 Lifecycle

| # | Stage | Data | What it prevents | Gate to pass |
|---|---|---|---|---|
| 1 | **Extract** candidate rules and tag them IN-SCOPE / GENERALIZABLE-DESIGN / OUT-OF-SCOPE-BOUNDARY / HISTORICAL | A | — (A is the development set) | Every rule has a rule card and a source |
| 2 | **Pre-register**: write fixtures, expected outcomes and set-B acceptance criteria *before* any validation data is chosen or opened. Hash and store them | Documents only | Hindsight: criteria cannot be fitted to results | Hash recorded |
| 3 | **Synthetic testing** | Fixtures | Overfitting to A | All positive, negative and edge tests pass |
| 4 | **Calibration** (only for rules with a parameter: T-03, R-03; experiments E-UNIV, E-OFFSET, E-A6, E-BATCH) | A + synthetic | Parameters chosen on B or U | Value and sensitivity recorded |
| 5 | **Freeze** rule set v1.0: git tag, rule-card hash, fixture hash, B criteria hash | — | Silent edits after validation | Your approval; supervisor review of T-* and B-* (OD-4) |
| 6 | **Independent validation on B**, evaluate-only, once per frozen version | B | Tuning on validation data | Pre-registered criteria met. A failure disables the rule; a repair is a new version and needs a **fresh reserve** B′ |
| 7 | **Final evaluation on U**, once, after the last freeze | U (in-scope members only) | Leakage; repeated looks | Report as is, whatever the result |

**Defining B (pre-registered, by me, from public metadata only).** B-pool is split into B-main and B-reserve. It must cover, within bulk RNA-seq: (a) two raw-count studies with a common condition and Ensembl or symbol IDs, for ComBat-seq and the batch design; (b) one TPM study with Ensembl IDs; (c) one different-tissue study and one different-disease study for the negative cases (the roles of the B1–B3 hints). Selection rules are written before any candidate is opened. Accessions are checked against the U list by string comparison only, and shared-donor risk is stated as unverified (`[NV]` in the audit).

**How a rule earns approval.** (1) Rule card complete. (2) Synthetic tests pass. (3) You approve the register (OD-2), with a supervisor review for T-* and B-*. (4) ACCEPT-M1 rules go straight into M1. ACCEPT-GATED rules are built but stay disabled until their validation passes on B. No rule is "validated" by A alone.

---

## 5. Batch-correction policy (automatic when eligible)

### 5.1 The exact conflict with `AGENT_INSTRUCTIONS.md`

| Location | Current text | Conflict |
|---|---|---|
| §28 | "Batch correction must NEVER be automatic. The user must explicitly approve correction." | Direct contradiction of automatic execution |
| §3 workflow | "Optional user-approved batch correction" | Names an approval step |
| §4 V1 MUST INCLUDE | "optional batch correction with explicit user approval" | Same |
| §61 item 12 | "Request optional batch correction" | Makes it a user request |
| §22 | Count transformation or alternative harmonization "only … with explicit user approval" | Blocks automatic preprocessing routes T-01, T-02 and T-03 |
| §63 | "ask for approval when necessary" | No conflict. Approvals move to rule approval (OD-2) |

§28's list of forbidden uses (never ComBat-seq on RPKM, FPKM, TPM or arbitrary normalized values; never overwrite the uncorrected matrix) stays exactly as it is.

### 5.2 Smallest necessary specification change (needs your approval, OD-1)

| Clause | Replace with |
|---|---|
| §28, first two sentences | "Batch correction must never be applied outside a validated, frozen eligibility rule. When every eligibility condition of an approved rule is met, BioNexus applies it automatically and records it. When any condition fails, BioNexus does not apply it. The uncorrected matrix is always preserved." |
| §3, §4, §61.12 | "Eligibility-gated batch correction" · "Receive the corrected matrix when eligible" |
| §22, approval clause | "…only through a rule-defined route that has passed the rule lifecycle. Count reconstruction, rounding, imputation and zero-filling remain forbidden." |

I am not reinterpreting these. They are edits to locked text and take effect only if you approve them.

### 5.3 Policy

| Layer | Who | What |
|---|---|---|
| Project policy: which methods and conditions are permitted | **You** (owner), with supervisor review, at rule approval and freeze | B-02, B-03 and B-04 |
| Dataset assessment | **BioNexus**, deterministically | Check eligibility |
| Execution | **BioNexus**, automatically, only for a frozen rule that passed validation | Run the method, keep both matrices |
| End user | Asked nothing | Told in one line, when a corrected matrix is provided |

**Eligibility (all must hold) [P]:**

1. The group is in a single space: SP-C (all R1 integer counts) → **ComBat-seq**; SP-P or SP-T (same log base and offset) → **ComBat**. Never ComBat-seq on anything else.
2. At least two batches (studies), each with at least two samples.
3. Study–condition structure is `none`: every condition level occurs in at least two studies. `partial` and `complete` are ineligible.
4. A defined condition variable, with no NA, and no unresolved fact request.
5. No shared donors across studies (conservative).
6. The rule is frozen and passed E-BATCH and set B.

The condition of interest is passed to the method so that its signal is retained (`covar_mod`/`group` in ComBat-seq, `mod` in ComBat; sva manual, read).

**Outputs.** `integrated_uncorrected_matrix` (primary, always) and `batch_corrected_matrix` (separate, labelled secondary). Deterministic checks (dimensions, labels, NaN/Inf, non-negative integers for ComBat-seq) discard the corrected matrix automatically if they fail. Statistical diagnostics are reported, not graded, so no cut-off is invented.

**What the user sees.** Nothing when it was not eligible, except where the reason is already a material limitation (L2, confounding). One line when it ran: "A batch-corrected version is also provided (method X). Your uncorrected matrix is the primary result."

**Honest caveat.** The ComBat-seq paper (read) reports mixed results against batch-as-covariate, and the Nygaard 2016 title warns of exaggerated confidence after correction (title only). Automatic correction is therefore defensible only because of the narrow eligibility, the always-kept uncorrected matrix, and the rule that **B-02 to B-04 ship disabled until E-BATCH and set B pass**. Until then BioNexus assesses batch structure and does not correct.

---

## 6. Division of work

### 6.1 What I keep

| Task | Why |
|---|---|
| Scientific decisions: spaces, routes, eligibility, accept/reject of every rule | Requires judgment on biological meaning |
| Rule-card finalization and the pre-registered B criteria | Leakage control depends on it |
| Experiments E-UNIV, E-OFFSET, E-A6, E-BATCH: design and interpretation | Scientific reasoning |
| Architecture, record schema, final integration of all deliverables | Consistency |
| Spec amendment text, decision register ownership | Authority boundary |
| Final quality control of every Nemotron deliverable | Final authority |

### 6.2 What Nemotron does

Detailed, paste-ready briefs are in `NEMOTRON_TASK_BRIEFS.md`.

| ID | Task | Output |
|---|---|---|
| N1 | Spec-to-design traceability matrix (every `AGENT_INSTRUCTIONS.md` clause → this plan) | Table: clause, location, status |
| N2 | Decision and issue register extracted from all documents | Register with source lines |
| N3 | Reference verification report | One row per attributed claim with quote or "could not verify" |
| N4 | Fixture specifications from my rule cards | One spec per fixture, with pre-written expected outcome |
| N5 | 53-test re-mapping check against `VALIDATION_PLAN.md` | Diff report |
| N6 | Rule-card completeness checker | Report of missing fields and untested rules |
| N7 | Cross-section consistency candidates | List of contradiction candidates for me to adjudicate |

**Why this division.** V4 shows what Nemotron does well (reading the spec, reconstructing tables) and where it fails (judging its own consistency, asserting "no contradictions", change-log accuracy). So it gets extraction and checking tasks with verifiable outputs. It never decides science, never edits a design document or the spec, and never reports "consistent"; it reports candidates.

### 6.3 How I will review it without repeating a review cycle

1. **Mechanical checks first:** schema, completeness, and every quote verified against the source by script.
2. **Sample audit:** at least 10 randomly chosen rows per deliverable, and 100% of rows tagged high-risk (anything touching transformation, batch or A/B/U).
3. **Adversarial probe:** one planted error in an input to see whether it is caught.
4. **Accept, reject or fix** logged in the register. Nothing enters the baseline unreviewed. Rejected output is not re-reviewed line by line, only re-run.

---

## 7. First implementation milestone

### 7.1 M0: baseline (documents, no product code)

Approved register and amendments (section 8), rule cards, fixture specifications (N4), pre-registered B criteria, the decision register, and M1 test list. **M0 exit:** OD-1 and OD-2 answered; N1 shows no unaddressed spec clause.

### 7.2 M1: Intake and Representation Evidence Engine 

**Scope.** Rules ACCEPT-M1 for intake only: G-01 to G-04, M-01 to M-04, R-01, R-02, R-05, R-06, V-02, J-05. **No transformation, no gene mapping, no compatibility state, no batch.**

**Input.** Expression files plus metadata. **Output.** Scope decision; validated, oriented *derived* artifact (original untouched); sample-matching table; representation evidence record; fact requests (F) for what is missing; internal assessment records; provenance JSON.

**Deliverables.** (1) Python intake library with unit tests. (2) The assessment-record schema (`check_id, rule_id, rule_version, scope, outcome, evidence, confidence, limitations, decision_basis`). (3) About 25 synthetic fixtures with hash-locked expected outcomes (transposed, ambiguous square, ragged header, raw counts, non-integer counts, CPM-like, TPM-like, RPKM-like, log-scale, negatives, NA, duplicate samples and genes, missing metadata, ambiguous names, wrong technology declared, undefined case). (4) A rule-to-test coverage report.

**Measurable acceptance criteria**

| # | Criterion | How measured |
|---|---|---|
| AC1 | 100% of fixtures give the pre-registered outcome | Automated comparison with the hash-locked expectation file |
| AC2 | Originals byte-identical before and after every run | SHA-256 comparison |
| AC3 | A3, A5 and A6 intake results match the project's code-generated profiles (dimensions, orientation, ID type, integer-ness, zero fraction); every difference is explained | Diff against `profile_*.json` and `stage2_evidence_summary.json`; 0 unexplained |
| AC4 | A1, A2 and A4 are refused by the scope gate with a one-line reason (boundary tests) | Test |
| AC5 | No value changes other than orientation | Value-equality test on derived files |
| AC6 | Every record validates against the schema | Schema validation |
| AC7 | The undefined-case fixture yields `not_assessable` and a rule-gap record, not a crash and not a guess | Test |
| AC8 | Every M1 rule has at least one positive, one negative and one edge test | Coverage report generated from rule cards |
| AC9 | The code contains no unseen-set accession or path | Static scan |

**Not in M1.** Anything touching the U data, gene mapping, compatibility, transformation, batch, UI, export.

### 7.3 After M1 (for orientation only)

M2 metadata, gene mapping and compatibility  → M3 transformations, integration, batch assessment, experiments  → M4 batch correction, validation, **freeze**  → M5 validation on B → M6 evaluation on U. Out of scope for now: UI, Excel export polish, T-05 unless E-A6 passes, N-04, X-01, X-03, anything FASTQ, anything microarray except boundary tests.

---

## 8. Decisions

### 8.1 Decision register

| ID | Decision | Decided by | Status | Why that authority |
|---|---|---|---|---|
| DR-01 | V1 = human, bulk RNA-seq, gene-level | You (OC-1, in your message) | Decided | Your statement; recorded |
| DR-02 | Four states kept; out-of-scope uploads refused at the gate; complete confounding → `compatible_with_warnings` with correction not offered | Me | Decided (architectural; §25 allows WARNING) | Inside spec discretion |
| DR-03 | Three target spaces; selection ladder; execution order | Me | Decided | Technical, math-backed |
| DR-04 | Rule register closed (section 3.4) | Me | Decided | Process |
| DR-05 | R1 + R2 count-space pooling rejected, replaced by T-01 | Me | Decided | Rounding forbidden by spec |
| DR-06 | Shared donors: keep, annotate, J limited (no user exclusion question) | Me | Decided. Replaces the exclusion question in `unresolved_scientific_questions.md` Issue 4 | Your "no specialist choices" principle |
| DR-07 | A5 remains an unmapped-ID fixture (Option 2A) | Me | Decided. `unresolved_scientific_questions.md` recommends 2A, and I found no recorded approval | Keeps scope |
| DR-08 | Set B definition and selection | Me | Decided, pre-registered | Needs no owner input |
| DR-09 | MR-16 resolved as a design constraint | Me | Decided | Not in the sva manual |
| DR-10 | Spec amendments to §28, §3, §4, §61.12, §22 | **You** | OD-1 | Locked text |
| DR-11 | Approve rule register v1.0 | **You** | OD-2 | Approval authority |
| DR-12 | Resolve the accession that appears in both a Stage 1 plan and the locked list; confirm U1–U3 composition | **You** | OD-3 | Only you hold that record, and I must not look |
| DR-13 | Supervisor review of T-* and B-* before freeze | **You** | OD-4 | Governance |
| DR-14 | Authorize revising the Skills Pack and the wording of 8 conflicting tests | **You** | OD-5 | You asked that these not be changed without authorization |

### 8.2 Test conflicts added by this plan

Beyond TC-1 to TC-8 of V3 (all still apply): **S5** and **T15** ("never auto") conflict with section 5 if OD-1 is approved. **T14** and **W4** (approval for transformations) are resolved the same way. They are reported here and not changed.

### 8.3 Why each owner decision cannot be made technically

OD-1 and OD-2 change or approve locked project authority. OD-3 depends on a record only you control. OD-4 is your governance choice. OD-5 is your own constraint. Only OD-1 and OD-2 block M0; OD-3 is needed before M5, OD-4 before M4, OD-5 before M2.

---

## 9. Your immediate next action

1. Reply **"approved"** (or send edits) for **OD-1** (the amendment wording in 5.2) and **OD-2** (rule register v1.0 in section 3).
2. Give Nemotron the briefs in `NEMOTRON_TASK_BRIEFS.md`, not my chat message, starting with N2 and N1.
3. Tell me which accession role stands (OD-3) whenever convenient; it is not blocking.
