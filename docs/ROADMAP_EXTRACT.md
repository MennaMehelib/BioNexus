# ROADMAP_EXTRACT (M1-relevant excerpts of BIONEXUS_V1_IMPLEMENTATION_ROADMAP.md)

Verbatim excerpts copied without editing. No new decisions or rules. The full document is the authority; if anything here seems incomplete, stop and report it rather than guessing. Excerpt headings below are added only to label each piece.

Notes carried from the source: nothing is implemented yet; gated rules stay disabled; AC1-AC9 are acceptance criteria numbers from the consolidated plan section 7.2 (listed below).


<!-- excerpt: 0.2 First M1 task -->
### 0.2 First M1 coding task: **T1.1 repository skeleton, rule registry, assessment-record schema**

It has no scientific content, so nothing scientific can block it. Everything later imports it. Its prompt is in `ANTIGRAVITY_M1_PROMPTS.md`.

<!-- excerpt: A.1 component table (M1 rows only, rows verbatim) -->
|---|---|---|
|---|---|---|
| Stage | Input | Processing | Output | Rules | Depends on | Validation tests | Failure / error handling | MS |
|---|---|---|---|---|---|---|---|---|
| S0 Intake | Files, metadata, declarations | Register inputs, SHA-256, set read-only copies | Intake record, hash manifest | G-04 | — | Hash identical before/after (AC2) | Unreadable file → `blocked`, named reason | M1 |
| S1 Parse | Raw file | Detect delimiter, quoting, BOM, header shape; write normalized derived file; log each change | Derived matrix file + change log | G-02 | S0 | Fixtures: tab, comma, BOM, ragged header | Ambiguous header → `not_assessable`, no guess | M1 |
| Scope gate | Declarations + value evidence | Compare declared tech/organism/level with R-01 evidence | Scope record | G-01 | S1, R-01 | Human counts accepted; microarray-like refused; declared/evidence mismatch → need_fact | Refuse with one line | M1 |
| Orientation | Parsed matrix + metadata IDs | Fix only when independent structural signals agree | Oriented derived matrix | G-03 | S1 | Transposed, correct, square (→ need_fact) | Signals disagree → need_fact | M1 |
| S2 Matching | Matrix sample IDs + metadata | Tiers 1–3; fuzzy = candidates only; Tier A completeness; condition label map | Match table, fact requests | M-01..M-03, M-06 | Orientation | Exact, normalized, ambiguous, missing field | Ambiguity → need_fact with candidates | M1 (M-01..M-03), M2 (M-06) |
| Duplicates | Matrix + metadata | Exact duplicate samples/genes | Duplicate record | M-04 | S1 | Identical dup collapsed; same ID different values → need_fact | — | M1 |
| S3 Representation | Oriented matrix + declarations | Structural facts and candidate labels; no value change | Representation evidence record | R-01, R-02, R-05, R-06 (R-03, R-04 gated) | Orientation | Integer counts, negatives, non-integer, NA | Undeclared non-integer → need_fact | M1 |
|---|---|---|---|---|---|---|
|---|---|---|---|---|---|---|
|---|---|---|---|---|---|

<!-- excerpt: B Dependency map -->
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

<!-- excerpt: C Package architecture -->
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

<!-- excerpt: D M1 coding plan -->
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

<!-- excerpt: E Gate (M1 row) -->
| MS | Entry | Tasks | Tests | Exit | Working deliverable |
| M1 | M0 items 1–6; repo + data paths from owner | T1.1–T1.9 | Unit, fixture integration, AC1–AC9 | AC1–AC9 all pass with real execution output; N1 shows no unaddressed spec clause; I-03 resolved | Installable package; `bionexus intake` works on fixtures and A3/A5/A6 |

<!-- excerpt: F Antigravity workflow -->
## F. Antigravity workflow

1. Owner creates the repository, copies in the contents of `ANTIGRAVITY_M1_PROMPTS.md` as needed, and sets the development data path outside the repo (read-only).
2. For each task: paste the **common preamble** then the **task block**. The agent works only in the allowed files, writes tests first, runs them, and returns the report.
3. Owner pastes the report and `git diff` back to me. I review (scientific and technical), then accept or request a targeted fix. **No dependent task starts before acceptance.**
4. One task at a time per file set. Parallel tasks only where section B allows.
5. Portable: prompts name behaviours, files and tests, not IDE features. Any coding agent can take them.
6. Reports must contain only commands actually run and their real output.

<!-- excerpt: AC1-AC9 from BIONEXUS_V1_CONSOLIDATED_PLAN.md section 7.2 -->
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
