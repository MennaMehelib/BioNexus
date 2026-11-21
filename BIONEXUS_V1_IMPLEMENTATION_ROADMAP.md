# BioNexus V1 — Implementation Roadmap

Baseline: `BIONEXUS_V1_CONSOLIDATED_PLAN.md` + `BIONEXUS_V1_RULE_CARDS.md` (approved 2026-11-21). This document adds no rules. It maps the approved rules onto code, tests and milestones. Changes to it need a finding, a failed test or a verified requirement, logged in `BIONEXUS_RECORD.md`.

Status words: **Proposed** (not yet built), **Gated** (built but disabled until validation passes). Nothing here is Implemented yet.

---
## 0. Immediate answers

### 0.1 Minimum M0 exit checklist (only what blocks M1)

| # | Item | Status |
|---|---|---|
| 1 | Baseline approved by owner | Done (2026-11-21) |
| 2 | PREPROCESSING_DECISION_MAP.md statement corrected in the plan | Done |
| 3 | Decision/issue record exists (`BIONEXUS_RECORD.md`) | Done |
| 4 | This roadmap exists | Done with this file |
| 5 | Owner provides an empty Git repository (or confirms a path) for Antigravity, and the development-data path (read-only) | **Open, owner action** |
| 6 | Owner creates a local, git-ignored deny-list file with the locked accessions (so code can be scanned for them without me seeing them in docs) | **Open, owner action** |
| 7 | I-03: owner confirms whether to edit `AGENT_INSTRUCTIONS.md` with the OD-1 wording (not needed to start M1 code; needed by M1 exit for spec parity) | Open, non-blocking for start |

**Not required to start M1:** Nemotron N1 and N2 results, N3–N7, any experiment, set B, OD-3, OD-4, OD-5. N1/N2 should finish before M1 exit (they check that M1 did not miss a spec clause), not before M1 starts.

### 0.2 First M1 coding task: **T1.1 repository skeleton, rule registry, assessment-record schema**

It has no scientific content, so nothing scientific can block it. Everything later imports it. Its prompt is in `ANTIGRAVITY_M1_PROMPTS.md`.

### 0.3 Nemotron tasks that run in parallel without blocking M1

| Task | When | Blocks? |
|---|---|---|
| N2 decision/issue register | Now | No (feeds record) |
| N1 spec traceability | Now | No (must finish by M1 exit) |
| N4 fixture specs for M1 rules | Now; **useful for T1.3+** | Soft: I define T1.x test expectations in the prompts anyway; N4 adds extra cases |
| N6 rule-card completeness | After N1/N2 | No |
| N5, N7 | Any time | No |
| N3 references | Before M3 (transform rules) | No |

---
## A. End-to-end workflow

![workflow](BIONEXUS_V1_WORKFLOW.png)

The fact-request loop (needs fact → user supplies a fact → back to S2) is the only runtime user interaction. Everything gated (S4 gene mapping to S7 transforms, S9–S10 batch) is built early but stays disabled behind its rule flag until validated. Disabled steps are skipped and reported as `not_assessable` ("BioNexus cannot assess this case yet"), never guessed.

### A.1 Component table

Columns: Input → Processing → Output; Rules; Depends on; Tests; Failure handling; Milestone.

| Stage | Input | Processing | Output | Rules | Depends on | Validation tests | Failure / error handling | MS |
|---|---|---|---|---|---|---|---|---|
| S0 Intake | Files, metadata, declarations | Register inputs, SHA-256, set read-only copies | Intake record, hash manifest | G-04 | — | Hash identical before/after (AC2) | Unreadable file → `blocked`, named reason | M1 |
| S1 Parse | Raw file | Detect delimiter, quoting, BOM, header shape; write normalized derived file; log each change | Derived matrix file + change log | G-02 | S0 | Fixtures: tab, comma, BOM, ragged header | Ambiguous header → `not_assessable`, no guess | M1 |
| Scope gate | Declarations + value evidence | Compare declared tech/organism/level with R-01 evidence | Scope record | G-01 | S1, R-01 | Human counts accepted; microarray-like refused; declared/evidence mismatch → need_fact | Refuse with one line | M1 |
| Orientation | Parsed matrix + metadata IDs | Fix only when independent structural signals agree | Oriented derived matrix | G-03 | S1 | Transposed, correct, square (→ need_fact) | Signals disagree → need_fact | M1 |
| S2 Matching | Matrix sample IDs + metadata | Tiers 1–3; fuzzy = candidates only; Tier A completeness; condition label map | Match table, fact requests | M-01..M-03, M-06 | Orientation | Exact, normalized, ambiguous, missing field | Ambiguity → need_fact with candidates | M1 (M-01..M-03), M2 (M-06) |
| Duplicates | Matrix + metadata | Exact duplicate samples/genes | Duplicate record | M-04 | S1 | Identical dup collapsed; same ID different values → need_fact | — | M1 |
| Donor / structure | Match table + metadata | Exact study-qualified donor IDs; none/partial/complete structure | Donor and structure records | M-05, M-07 | S2 (multi-study) | Shared donor, similar IDs not linked, three structures | Missing donor ID → no claim | M2 |
| S3 Representation | Oriented matrix + declarations | Structural facts and candidate labels; no value change | Representation evidence record | R-01, R-02, R-05, R-06 (R-03, R-04 gated) | Orientation | Integer counts, negatives, non-integer, NA | Undeclared non-integer → need_fact | M1 |
| S4 Gene mapping | Gene ID column + pinned annotation | Versionless Ensembl; one-to-many excluded | Mapping artifact | N-01..N-03 (gated) | S3 | Synthetic + A3/A6 symbols | Unmapped listed, never guessed | M2 |
| S6 Compatibility | All per-study records | Pairs → groups; T/Q/J; fixed state combination | Compatibility record, state | J-01..J-05 | S2–S5 | One fixture per branch | Rule gap → `not_assessable` | M2 |
| S7 Preprocessing | Matrix + route | Convert to target space on full universe, then map, then log | Derived matrices + parameters | T-01..T-05 (gated), T-07 | S3, S4, S6 | Exactness on synthetic; refusals | Forbidden op → refuse | M3 |
| S8 Integration | Derived matrices | Gene intersection, presence table | Uncorrected integrated matrix | N-05 | S7 | Intersection, no zero fill | No shared genes → no joint matrix | M3 |
| S9 Batch assessment | Integrated matrix + design | Report numbers only | Batch report | B-01 (gated) | S8 | Synthetic known effects | — | M3 |
| S10 Correction | Eligible groups | ComBat-seq / ComBat per rule | Separate corrected matrix | B-02..B-04 (gated), B-05 | S9 | E-BATCH + set B | Failed structural check → discard corrected | M4 |
| S11 Validation | Outputs | Deterministic checks | Validation record | V-01, B-05 | S8/S10 | Dimensions, labels, NaN/Inf | Failure → output withheld, reason | M3–M4 |
| S12 Export | All | Write CSV matrices, JSON provenance, markdown report | Export bundle | V-02 | all | Trace test | — | M4 |

**Export format note [to check against spec]:** `AGENT_INSTRUCTIONS.md`/Stage 1 notes mention an Excel export. I have not confirmed the spec's required export formats in this session. M4 starts with N1's traceability row for export; Excel (`.xlsx` via openpyxl) is added if the spec requires it.

---
## B. Dependency map

**Sequential chain (each needs the previous):** S0 → S1 → Orientation → S2 → S3 → S4 → S5 → S6 → S7 → S8 → S9 → S10 → S11 → S12.

**Independent components (no dependency on pipeline stages):** record schema and rule registry (T1.1), provenance/hash utilities (T1.2), static analysis scans, report templates.

**Safe to develop in parallel (different files, no shared state):**
- After T1.1: T1.2 (provenance), T1.3 (parse), T1.5 (representation evidence) can run in parallel. T1.4 (orientation) needs T1.3's output type only.
- M2: sample matching helpers, gene mapping, donor/structure logic.
- Any time: Nemotron audit tasks.

Rule: two agents never edit the same file; each task lists its allowed files.

**Must wait for scientific validation (built behind flags, disabled):**

| Component | Waits for |
|---|---|
| R-03 constant-sum evidence | Precision-tolerance simulation (deadline end of M2) |
| R-04 offset/base detection | Synthetic validation |
| N-01..N-03 | Synthetic + A3/A6 symbol tests, pinned annotation file |
| T-01..T-04 | Exactness tests; E-UNIV; E-OFFSET |
| T-05 | E-A6 (deadline end of M3) |
| B-01..B-04 | E-BATCH, then set B |

---
## C. Python package architecture (V1, deliberately small)

```
bionexus/
  pyproject.toml            # Python >=3.10, pandas, numpy; pytest (dev)
  src/bionexus/
    records.py              # Outcome enum, AssessmentRecord, combine_outcomes (J-04), RuleGap
    rules.py                # RuleRegistry: id, version, status (proposed/gated/enabled), enabled flag
    provenance.py           # sha256, manifest, ProvenanceLog, read-only helpers      (G-04, V-02)
    fileio.py               # parse_matrix(): delimiter/quote/BOM/header              (G-02)
    orientation.py          # detect_orientation()                                    (G-03)
    scope.py                # scope_gate()                                            (G-01)
    metadata.py             # match_samples(), tier_a_check(), label_map()            (M-01..M-03, M-06)
    duplicates.py           # find_duplicates()                                       (M-04)
    donors.py               # donor_overlap(), study_condition_structure()            (M-05, M-07)
    representation.py       # evidence_record(), declared_representation()            (R-01, R-02, R-05, R-06)
    genes.py                # map_ids(), aggregate(), intersect()                     (N-01..N-03, N-05)
    compatibility.py        # grade_pair(), group_studies(), state_from_records()     (J-01..J-05)
    transforms.py           # to_log_cpm(), rpkm_to_tpm(), log_offset(), invert_log() (T-01..T-04, T-07) GATED
    batch.py                # assess(), eligibility(), combat_seq(), combat()          (B-01..B-05) GATED
    validation.py           # check_matrix()                                          (V-01)
    export.py               # write_bundle()                                          (V-02)
    cli.py                  # `bionexus intake|assess|integrate`
  tests/
    unit/ integration/ fixtures/ (synthetic only, hash-locked) conftest.py
  scripts/                  # scan_denylist.py (AC9), profile_diff.py (AC3)
```

### C.1 Module contract table

| Module | Responsibility | Input → Output | Public API | Depends on | Rules | Tests |
|---|---|---|---|---|---|---|
| records | Common vocabulary for every check | outcomes → combined state | `Outcome`, `AssessmentRecord`, `combine_outcomes()` | — | J-04, J-05 | `test_records.py` |
| rules | One place that knows each rule's status/flag | rule id → enabled? | `RuleRegistry.is_enabled(id)` | — | all | `test_rules.py` |
| provenance | Hash, manifest, trace | path → hash/record | `sha256_file`, `ProvenanceLog.add` | — | G-04, V-02 | `test_provenance.py` |
| fileio | Safe parse and derived write | path → DataFrame + change log | `parse_matrix` | provenance, records | G-02 | `test_fileio.py` |
| orientation | Axis detection | DataFrame, sample IDs → oriented + record | `detect_orientation` | records | G-03 | `test_orientation.py` |
| scope | Gate | declarations + evidence → record | `scope_gate` | representation, records | G-01 | `test_scope.py` |
| metadata | Matching and completeness | IDs, metadata → table + records | `match_samples` | records | M-01..M-03 | `test_metadata.py` |
| duplicates | Exact duplicates | DataFrame → record | `find_duplicates` | records | M-04 | `test_duplicates.py` |
| representation | Evidence only | DataFrame + declaration → record | `evidence_record` | records, rules | R-01, R-02, R-05, R-06 | `test_representation.py` |
| donors | Overlap, structure | metadata → records | `donor_overlap`, `study_condition_structure` | records | M-05, M-07 | M2 |
| genes | IDs and intersection | tables → mapped | `map_ids`, `intersect` | records, rules | N-* | M2–M3 |
| compatibility | Grades, state | records → state | `grade_pair` | records | J-* | M2 |
| transforms / batch | Gated science | matrices → matrices | listed above | rules (flag) | T-*, B-* | M3–M4 |

Every public function returns data plus one or more `AssessmentRecord`s (fields: `check_id, rule_id, rule_version, scope, outcome, evidence, confidence, limitations, decision_basis`). Functions never mutate their inputs. A gated rule's function raises `RuleDisabled` unless the registry flag is on.

---
## D. Milestone coding plan

AC numbers refer to plan section 7.2 (AC1–AC9).

### M0 — baseline (documents only)
Tasks: record, roadmap, prompts, repo handoff (owner), N1/N2 launched. Deliverable: this folder. Exit: section E.

### M1 — Intake and Representation Evidence Engine
Rules: G-01..G-04, M-01..M-04, R-01, R-02, R-05, R-06, V-02, J-05. No transformation, gene mapping, compatibility states or batch.

| Task | Functionality | Files (create) | Rules | Tests | Acceptance | Deliverable |
|---|---|---|---|---|---|---|
| **T1.1** | Skeleton, `Outcome`, `AssessmentRecord`, `combine_outcomes`, `RuleRegistry`, `RuleGap` | `pyproject.toml`, `src/bionexus/{__init__,records,rules}.py`, `tests/unit/test_records.py`, `test_rules.py` | J-04, J-05, AC6 | Every J-04 branch; unknown outcome rejected; gated rule disabled by default | Tests pass; package installs | Code + diff + report |
| T1.2 | SHA-256 manifest, read-only handling, provenance log, JSON serialization | `provenance.py`, `test_provenance.py` | G-04, V-02 | Hash stable; original unchanged after write of derived file | AC2 | same |
| T1.3 | `parse_matrix`: delimiter, quoting, BOM, ragged header; change log | `fileio.py`, `tests/fixtures/parse/*`, `test_fileio.py` | G-02 | Tab, comma, BOM, ragged → record; unreadable → blocked | Fixtures hit expected outcomes | same |
| T1.4 | `detect_orientation` from independent structural signals | `orientation.py`, test, fixtures | G-03 | Transposed, correct, square → need_fact | AC1 subset; AC5 (no value change besides axis) | same |
| T1.5 | `evidence_record` (integer-ness, non-negativity, negatives, NA, column-sum stats, minimum, zero fraction), `declared_representation`, universe-completeness note | `representation.py`, test, fixtures | R-01, R-02, R-05, R-06 | Integer counts → R1 candidate; negatives → not R1; non-integer undeclared → need_fact; NA → complete-case list | AC1 subset; no inference from constant sums (R-03 disabled) | same |
| T1.6 | `scope_gate` | `scope.py`, test | G-01 | Human counts pass; microarray-like fixture (negatives + probe IDs) refused; declared vs evidence mismatch → need_fact | AC4 on fixtures | same |
| T1.7 | `match_samples` tiers 1–3, fuzzy candidates, Tier A completeness, `find_duplicates` | `metadata.py`, `duplicates.py`, tests, fixtures | M-01..M-04 | Per rule card P/N/E | AC1 subset | same |
| T1.8 | Rule-gap record, `bionexus intake` CLI chaining S0–S3; integration test over all fixtures | `cli.py`, `tests/integration/test_intake.py` | J-05, AC1, AC7 | Undefined case → `not_assessable` + RuleGap | AC1, AC7, AC8 report | CLI + coverage report |
| T1.9 | Development-data checks (needs owner paths): `scripts/profile_diff.py`, `scripts/scan_denylist.py` | scripts, tests | AC3, AC4, AC9 | A3/A5/A6 results vs project profiles; A1/A2/A4 refused; deny-list scan | 0 unexplained differences; scan clean | Diff report |

Order: T1.1 → {T1.2, T1.3, T1.5} → T1.4 → T1.6, T1.7 → T1.8 → T1.9.

### M2 — Metadata, gene mapping, compatibility
Tasks: T2.1 M-06 label map; T2.2 M-05 donors + M-07 structure; T2.3 N-01..N-03 mapping (gated, flag on in tests only), annotation file pinned by owner; T2.4 J-01..J-05 compatibility; T2.5 R-03 precision simulation (decide enable/defer); T2.6 multi-study integration tests. Tests: one fixture per J-04 branch, similar-ID non-link, one-to-many exclusion. Acceptance: all fixtures at expected outcome; A3/A6 symbol mapping report with unmapped list; compatibility on A3 + A6 pair gives a state with per-dimension reasons.

### M3 — Transformations, integration, batch assessment, experiments
T3.1 T-01 log-CPM; T3.2 T-02 RPKM→TPM; T3.3 T-03/T-04 log offset and inversion; T3.4 N-05 intersection; T3.5 B-01 batch report; T3.6 T-07 refusal tests; T3.7 experiments E-UNIV, E-OFFSET, E-A6 (scripts + results recorded); T3.8 V-01 checks. Acceptance: exactness on synthetic (identity tests to numeric tolerance derived from float precision); T-05 decided (enable or defer) by E-A6; each experiment has a written result in the record.

### M4 — Correction, validation, export, freeze
T4.1 B-02 eligibility; T4.2 E-BATCH simulation; T4.3 B-03 / B-04 wrappers (R `sva` via `rpy2`, or documented alternative; choice made with evidence in T4.2); T4.4 B-05 structural post-checks; T4.5 export bundle; T4.6 freeze procedure (tag, hashes). Acceptance: pre-registered E-BATCH criteria met or rules stay disabled; freeze requires OD-4.

### M5 — Validation on B
Pre-registered B criteria (plan 4.2) executed once on the frozen version; report as is.

### M6 — Final evaluation on U
Once, after the last freeze, in-scope U members only, reported as is. Needs OD-3.

---
## E. Gates

| MS | Entry | Tasks | Tests | Exit | Working deliverable |
|---|---|---|---|---|---|
| M0 | Baseline approved | Section 0.1 items | — | 0.1 items 1–6 done | Record, roadmap, prompts |
| M1 | M0 items 1–6; repo + data paths from owner | T1.1–T1.9 | Unit, fixture integration, AC1–AC9 | AC1–AC9 all pass with real execution output; N1 shows no unaddressed spec clause; I-03 resolved | Installable package; `bionexus intake` works on fixtures and A3/A5/A6 |
| M2 | M1 exit | T2.x | See D | Fixtures pass; R-03 decided; A3+A6 report | Compatibility engine |
| M3 | M2 exit; annotation pinned | T3.x | See D | Experiments recorded; T-05 decided | Preprocessing + uncorrected integration |
| M4 | M3 exit | T4.x | See D | E-BATCH met or rules disabled; OD-4 done | Frozen v1.0, export |
| M5 | M4 + B criteria hash | Run B | Pre-registered | Report | Validation report |
| M6 | M5 + OD-3 | Run U once | Pre-registered | Report | Final evaluation |

A milestone is complete only with working code and real test output. Documentation alone never closes a milestone.

---
## F. Antigravity workflow

1. Owner creates the repository, copies in the contents of `ANTIGRAVITY_M1_PROMPTS.md` as needed, and sets the development data path outside the repo (read-only).
2. For each task: paste the **common preamble** then the **task block**. The agent works only in the allowed files, writes tests first, runs them, and returns the report.
3. Owner pastes the report and `git diff` back to me. I review (scientific and technical), then accept or request a targeted fix. **No dependent task starts before acceptance.**
4. One task at a time per file set. Parallel tasks only where section B allows.
5. Portable: prompts name behaviours, files and tests, not IDE features. Any coding agent can take them.
6. Reports must contain only commands actually run and their real output.

## G. Record keeping
`BIONEXUS_RECORD.md` holds decisions, open issues, changes, validation results. I update it after each accepted task.
