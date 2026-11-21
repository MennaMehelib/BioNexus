# Antigravity Prompts — M1 (Intake and Representation Evidence Engine)

How to use: for each task, paste **COMMON PREAMBLE** followed by that task's block. Send the report and `git diff` back to the lead architect (Claude). Do not start the next task before it is accepted. One task at a time per file set. Order: T1.1 → {T1.2, T1.3, T1.5} → T1.4 → T1.6, T1.7 → T1.8 → T1.9.

---
## COMMON PREAMBLE (paste before every task)

You are the coding agent for BioNexus V1, a tool that decides whether bulk RNA-seq gene-expression datasets can be scientifically integrated. The central rule is: never blindly merge heterogeneous gene-expression datasets.

**Before writing any code**
1. Run `git status`, `git log --oneline -10` and list the repository tree. Read every existing file that your task touches or imports. Report what you found.
2. Read `docs/ROADMAP_EXTRACT.md` and `docs/RULE_CARDS_EXTRACT.md` if present (copies of the relevant roadmap and rule-card text). If they are missing, stop and say so. Do not guess requirements.

**Hard rules**
- Create or modify ONLY the files listed under "Allowed files". Do not rewrite or reformat existing files. If another change seems necessary, stop and report it; do not make it.
- Never modify, move or delete anything under the data directory. Original datasets are read-only. Outputs go only to a temporary or output directory you create.
- Do not open, read, list or reference any dataset other than those explicitly named in your task. The locked evaluation datasets must never appear in code, tests, fixtures, comments or config.
- Do not invent thresholds, scientific rules or numeric cut-offs. If a value is needed and the task does not give one, derive it from the data's own properties and document the derivation, or return `need_fact`/`not_assessable`. Never silently choose.
- Do not change any data value except where the task says so. Never round, impute, zero-fill, log-transform or normalize anything in M1.
- Gated rules (listed in the task) must stay disabled by default.
- Write the tests FIRST from the expected behaviour in the task, run them to see them fail, then implement.
- Never claim a test passed unless you ran it. Paste real command output.

**Language and tooling:** Python 3.10+, pandas, numpy, pytest. No other runtime dependencies unless the task allows.

**Required report (at the end)**
1. Files created/modified (list).
2. `git diff --stat` and the full `git diff`.
3. Exact commands run and their real output (pytest summary with counts).
4. For each acceptance criterion: PASS/FAIL with evidence.
5. Limitations, assumptions, anything you could not do, anything you noticed but did not change.

---
## T1.1 — Skeleton, assessment records, rule registry

**Inspect first:** the repository tree; if a `pyproject.toml` or `src/` already exists, report it and stop for instructions.

**Allowed files (create only):**
`pyproject.toml`, `README.md` (5 lines max), `src/bionexus/__init__.py`, `src/bionexus/records.py`, `src/bionexus/rules.py`, `src/bionexus/rules_register.json`, `tests/__init__.py`, `tests/unit/__init__.py`, `tests/unit/test_records.py`, `tests/unit/test_rules.py`, `.gitignore` (include `.u_denylist`, `__pycache__`, `*.egg-info`, `out/`).

**Functionality**

`records.py`
- `class Outcome(str, Enum)` with exactly: `pass`, `resolved`, `note`, `limitation`, `need_fact`, `need_decision`, `not_assessable`, `blocked` (use `PASS`, `RESOLVED`, `NOTE`, `LIMITATION`, `NEED_FACT`, `NEED_DECISION`, `NOT_ASSESSABLE`, `BLOCKED` as member names).
- `class State(str, Enum)`: `compatible`, `compatible_with_warnings`, `requires_manual_review`, `incompatible`.
- `@dataclass(frozen=True) class AssessmentRecord` with fields: `check_id: str`, `rule_id: str`, `rule_version: str`, `scope: str` (e.g. a study or pair identifier), `outcome: Outcome`, `evidence: dict`, `confidence: str | None`, `limitations: tuple[str, ...]`, `decision_basis: str`. Validate in `__post_init__`: non-empty `check_id`, `rule_id`, `scope`; `outcome` must be an `Outcome`; raise `ValueError` otherwise. Provide `to_dict()` returning JSON-serializable data (enum as string).
- `def combine_outcomes(records) -> State` — fixed order: any `blocked` → `incompatible`; else any of `need_fact`, `need_decision`, `not_assessable` → `requires_manual_review`; else any `limitation` → `compatible_with_warnings`; else `compatible`. `pass`, `resolved`, `note` never change the result. Empty input → `compatible`.
- `@dataclass(frozen=True) class RuleGap` with `scope: str`, `description: str`, `missing: str`; function `rule_gap_record(gap) -> AssessmentRecord` producing outcome `not_assessable`, `rule_id="J-05"`, and `decision_basis="rule gap: BioNexus cannot assess this case yet"`.

`rules.py`
- `class RuleStatus(str, Enum)`: `ACCEPT_M1`, `ACCEPT_GATED`, `CONDITIONAL`, `REJECTED`, `DEFERRED`.
- `class RuleDisabled(Exception)`.
- `class RuleRegistry`: loads `rules_register.json` (list of `{id, status, version}`); `status(rule_id)`; `is_enabled(rule_id)` is True for `ACCEPT_M1`; for `ACCEPT_GATED`/`CONDITIONAL` only if the id is in an `enabled_for_test` set passed to the constructor; never for `REJECTED`/`DEFERRED` (passing such an id in the set raises `ValueError`); `require_enabled(rule_id)` raises `RuleDisabled` when not enabled; unknown id raises `KeyError`.

`rules_register.json` — exactly these 45 rules, `version` `"0.1"` each:
- ACCEPT_M1 (25): G-01, G-02, G-03, G-04, M-01, M-02, M-03, M-04, M-05, M-06, M-07, R-01, R-02, R-05, R-06, N-05, T-07, B-05, J-01, J-02, J-03, J-04, J-05, V-01, V-02
- ACCEPT_GATED (12): R-04, N-01, N-02, N-03, T-01, T-02, T-03, T-04, B-01, B-02, B-03, B-04
- CONDITIONAL (2): R-03, T-05
- REJECTED (3): T-06, B-06, X-02
- DEFERRED (3): N-04, X-01, X-03

**Tests to write and run** (`pytest -q`)
- `combine_outcomes`: one test per branch of the fixed order; precedence (blocked beats need_fact beats limitation); empty list; `pass/resolved/note` only → `compatible`.
- Record validation: empty `check_id` raises; wrong outcome type raises; `to_dict()` is JSON-serializable via `json.dumps`.
- `rule_gap_record` gives `not_assessable`, `J-05`.
- Registry: 45 rules loaded with the counts above; an M1 rule is enabled; a gated rule is disabled by default and enabled when listed in `enabled_for_test`; `require_enabled` on `T-01` raises `RuleDisabled`; `REJECTED` id in the enabled set raises `ValueError`; unknown id raises `KeyError`.

**Expected results:** all tests pass; `pip install -e .` works; `python -c "import bionexus"` works.

**Acceptance criteria**
1. All listed tests exist and pass (paste pytest output).
2. The JSON has exactly 45 ids with the stated statuses.
3. No file outside "Allowed files" was created or changed.
4. No numeric threshold or scientific rule appears in the code.

---
## T1.2 — Provenance and hashing (G-04, V-02)

**Inspect first:** `records.py`, `rules.py` from T1.1.
**Allowed files:** `src/bionexus/provenance.py`, `tests/unit/test_provenance.py`.
**Functionality:** `sha256_file(path) -> str` (stream in chunks); `make_read_only(path)` (chmod, no content change); `class ProvenanceLog` with `add_input(path)`, `add_step(rule_id, rule_version, parameters: dict, inputs: list[str], outputs: list[str])`, `to_json()`, `write(path)`; each output entry stores its SHA-256 and the software versions (`bionexus`, Python, pandas, numpy); `verify_unchanged(path, expected_hash) -> AssessmentRecord` (rule `G-04`, `pass` or `blocked`).
**Tests:** hash of a known small file equals a precomputed constant written in the test; same file twice → same hash; changing one byte changes it; a derived file written next to an input leaves the input hash identical; log round-trips through JSON; `verify_unchanged` returns `blocked` after tampering.
**Expected:** all pass. **Acceptance:** AC2 mechanism demonstrated; no mutation of inputs; only allowed files touched.

## T1.3 — Parse and structural validation (G-02)

**Inspect first:** `records.py`, `provenance.py`.
**Allowed files:** `src/bionexus/fileio.py`, `tests/unit/test_fileio.py`, `tests/fixtures/parse/` (small synthetic files).
**Functionality:** `parse_matrix(path) -> ParseResult(df, change_log, records)`. Detect delimiter (tab/comma/semicolon) from the file's own content; handle UTF-8 BOM; strip surrounding quotes; handle a header with one fewer label than data columns (ragged header), recording the fix in `change_log`; never change a numeric value. Anything ambiguous (two delimiters equally plausible, rows of unequal length not explained by the ragged-header case) → `not_assessable` record, no guess. Unreadable or empty file → `blocked`. Write the normalized derived copy only if asked via an `out_path` argument; the input file is untouched.
**Tests (synthetic fixtures you create):** tab, comma, semicolon; BOM; quoted fields; ragged header; empty file → blocked; binary junk → blocked; ambiguous delimiter → not_assessable; numeric values identical before and after parse (compare as strings from source).
**Acceptance:** each case yields the stated outcome; value equality test passes.

## T1.4 — Orientation (G-03)

**Inspect first:** `fileio.py`, `records.py`.
**Allowed files:** `src/bionexus/orientation.py`, `tests/unit/test_orientation.py`, `tests/fixtures/orientation/`.
**Functionality:** `detect_orientation(df, metadata_sample_ids=None) -> OrientationResult(df_oriented, records)`. Output convention: rows = genes, columns = samples. Use only independent structural signals: (a) which axis labels look like gene identifiers vs sample identifiers (Ensembl-style `ENSG`, symbols, probe-like vs `GSM`/sample-like) using patterns passed in as data, not hard-coded accession rules; (b) which axis labels match the metadata sample IDs; (c) which axis is longer (genes are normally more numerous than samples). Transpose only if every available signal agrees. If signals disagree or only one exists and it is ambiguous, or the matrix is square → `need_fact` record, no transpose. No numeric thresholds: signals are boolean comparisons.
**Tests:** already-correct; clearly transposed; square matrix → need_fact; signals disagree → need_fact; values identical after transpose (`df.T` equality).
**Acceptance:** AC5 (no value change other than axis); outcomes as stated.

## T1.5 — Representation evidence (R-01, R-02, R-05, R-06)

**Inspect first:** `records.py`, `rules.py`.
**Allowed files:** `src/bionexus/representation.py`, `tests/unit/test_representation.py`, `tests/fixtures/representation/`.
**Functionality:** `evidence_record(df, declared=None) -> RepresentationEvidence`. Compute and return as plain facts: all-values-integer-valued (bool), any negative, any NA, count of NA genes, minimum, zero fraction, per-column sums (list), per-column sum min/max. Candidate labels: `R1` only if all non-NA values are non-negative integers. If values are non-integer and no `declared` representation is supplied → `need_fact` (R-02: documentation needed). If `declared` is supplied, record it as the declared representation and check consistency with the facts (e.g. declared R1 but non-integer values → `blocked` with reason; declared linear but negatives present → `need_fact`). **Do not infer CPM/TPM/RPKM from constant column sums: rule R-03 is CONDITIONAL and must stay disabled** (check with `RuleRegistry.require_enabled("R-03")` semantics; just do not implement it). NA handling (R-06): return the list of genes with any NA (complete-case set), never impute. R-05: if an annotation gene list is passed, record the fraction of annotation genes present as a fact and a `limitation` record if any are absent; no threshold.
**Tests:** integer counts → R1 candidate; counts with one negative → not R1; non-integer undeclared → need_fact; declared R1 with non-integers → blocked; NA genes listed, matrix unchanged; column sums reported; universe subset → limitation.
**Acceptance:** no value is changed; no CPM/TPM inference exists; outcomes as stated.

## T1.6 — Scope gate (G-01)

**Inspect first:** `representation.py`, `records.py`.
**Allowed files:** `src/bionexus/scope.py`, `tests/unit/test_scope.py`, `tests/fixtures/scope/`.
**Functionality:** `scope_gate(declared: dict, evidence: RepresentationEvidence, id_type: str|None) -> records`. `declared` keys: `organism`, `technology`, `level` (all optional strings). Accept only human, RNA-seq, gene-level. Technology declared as microarray, organism not human, or level not gene → `blocked` ("out of V1 scope") with a one-line reason. If a required declaration is missing → `need_fact`. If declared RNA-seq but evidence shows negative values together with probe-like IDs → `need_fact` (declaration and evidence disagree). Never refuse on accession.
**Tests:** human RNA-seq counts passes; declared microarray refused; mouse refused; missing organism → need_fact; RNA-seq declared with negatives + probe IDs → need_fact; no accession string appears in the source (grep test).
**Acceptance:** boundary refusals work on fixtures.

## T1.7 — Sample matching and duplicates (M-01..M-04)

**Inspect first:** `records.py`.
**Allowed files:** `src/bionexus/metadata.py`, `src/bionexus/duplicates.py`, tests, fixtures.
**Functionality:** `match_samples(matrix_ids, metadata_ids, study)`: tier 1 exact; tier 2 normalized (case-fold, strip whitespace, collapse `-`/`_`/`.`, optional documented mapping dict argument); tier 3 positional only if counts are equal AND a `documented_order=True` flag is passed. Fuzzy/near matches are returned as candidates only with a `need_fact` record listing candidates, evidence and consequence. Identity key is `(study, sample_id)`; the same stem in two studies is never merged. `tier_a_check(metadata, required_fields)` → `need_fact` per missing field. `find_duplicates(df)`: exact duplicate sample columns and duplicate gene rows; identical duplicates recorded with a note; same ID with different values → `need_fact`.
**Tests:** per rule card P/N/E: exact, normalized, ambiguous, same stem different studies not merged, missing field, duplicates identical vs conflicting.
**Acceptance:** no silent mapping; outcomes as stated.

## T1.8 — Intake runner and rule-gap handling (J-05)

**Inspect first:** all modules from T1.2–T1.7.
**Allowed files:** `src/bionexus/cli.py`, `src/bionexus/__init__.py` (add imports only if needed), `tests/integration/test_intake.py`, `tests/integration/fixtures/`, `scripts/coverage_report.py`.
**Functionality:** `bionexus intake --matrix X --metadata Y --declared k=v ... --out DIR` runs S0 hash → S1 parse → scope gate → orientation → sample matching → representation evidence → duplicates, writing derived files, `records.json`, `provenance.json` into `DIR` (never into the input directory). Any situation no implemented rule covers produces a `RuleGap` record, not an exception. `coverage_report.py` lists every M1 rule with the number of positive, negative and edge tests found (by test-name convention `test_<RULE>_<P|N|E>_...`).
**Tests:** end-to-end over ~25 synthetic fixtures with expected outcomes written in the test file BEFORE implementation; an undefined-case fixture yields `not_assessable` plus RuleGap; originals byte-identical.
**Acceptance:** AC1 (100% fixtures at expected outcome), AC2, AC6 (records validate), AC7, AC8 (coverage report shows ≥1 P, N, E per M1 rule).

## T1.9 — Development-data checks (owner supplies read-only paths)

**Precondition:** the owner supplies (a) the read-only directory of the A3, A5, A6 expression files, (b) the project's code-generated profile JSON files for them, (c) a local git-ignored `.u_denylist` file. If any is missing, stop.
**Allowed files:** `scripts/profile_diff.py`, `scripts/scan_denylist.py`, `tests/integration/test_dev_data.py` (skipped automatically when the data path is not set via an environment variable).
**Functionality:** `profile_diff.py` runs intake on A3, A5, A6 (read-only) and compares dimensions, orientation, ID type, integer-ness, zero fraction with the project profile JSON; prints every difference. A1, A2, A4 must be refused by the scope gate with a one-line reason. `scan_denylist.py` reads `.u_denylist` and fails if any listed string occurs anywhere in tracked files.
**Do not** open any dataset other than A1–A6 named above, and never anything from the denylist.
**Acceptance:** AC3 (0 unexplained differences; each difference listed with a cause or flagged for the architect), AC4, AC9 scan clean, input hashes unchanged.
