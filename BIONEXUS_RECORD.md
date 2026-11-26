# BioNexus V1 — Working Record (decisions, issues, changes, validation)

Maintained by the lead architect. Every entry cites its source. Status words: Decided / Open / Proposed-gated / Done.

**T1.8 status: ACCEPTED AS-IS.** Claude's final independent review disposition is ACCEPT AS-IS. The owner subsequently verified the fixture manifest, integration tests, coverage report and full test suite locally on Windows. T1.8 implementation artifacts remain uncommitted.

## 1. Accepted decisions

| ID | Decision | Source | Date |
|---|---|---|---|
| AD-01 | Consolidated plan and rule cards are the approved working baseline for V1 | Owner message 2026-11-21 02:12 | 2026-11-21 |
| AD-02 | Plan section 8 decisions accepted as written (DR-01..DR-09 decided by architect; DR-10 spec amendments, DR-11 register v1.0 approved in principle by the baseline approval) | Same message ("I agree with the proposed direction and decisions") | 2026-11-21 |
| AD-03 | GATED and CONDITIONAL rules stay proposed and disabled until their validation passes | Same message | 2026-11-21 |
| AD-04 | `PREPROCESSING_DECISION_MAP.md` exists; not relied on, including for Nemotron tasks | Owner clarification | 2026-11-21 |
| AD-05 | Changes only from a documented finding, test result or verified requirement | Owner message | 2026-11-21 |

Note on AD-02: the owner approved "the plan" and "the proposed direction and decisions". I read this as OD-1 and OD-2 answered. The spec text itself (`AGENT_INSTRUCTIONS.md`) is not edited yet; OD-1 amendments are recorded as approved wording and will be applied to the spec only when the owner explicitly confirms the file edit. This remains tracked as I-03.

## 2. Open issues

| ID | Issue | Blocks | Owner/next step |
|---|---|---|---|
| I-01 | Accession in both the Stage 1 plan and the locked U list (OD-3) | M5 | Owner |
| I-02 | Supervisor review of T-* and B-* (OD-4) | M4 freeze | Owner |
| I-03 | Apply OD-1 wording to `AGENT_INSTRUCTIONS.md`; the approved wording has not yet been applied to the file because explicit authorization for that file edit is still required | M1 spec parity only | Obtain explicit owner authorization before editing the file |
| I-04 | Authorize Skills Pack and test-wording revision (OD-5) | M2 | Owner |
| I-05 | Nemotron N2 and N1 have not yet been run (briefs ready: `NEMOTRON_N2_PASTE.md`, `NEMOTRON_N1_PASTE.md`) | M1 exit | Owner pastes; architect reviews |
| I-06 | Set B definition: pre-registered criteria not yet written | M5 | Architect, before any candidate is opened |
| I-07 | A3 read layout conflict (C-12 in master knowledge) | none for M1 | Note only |
| I-09 | Status: Open. Specification gap, not shown to be a conflict: the exact disposition of identical duplicate sample columns in derived outputs, and the stage at which it is handled, are not sufficiently specified. The sources use different wording that may or may not describe the same behavior: "record and keep one with note" (`BIONEXUS_V1_RULE_CARDS.md` L24, M-04); "R (flagged, original kept)" (`BIONEXUS_V1_SCIENTIFIC_TECHNICAL_DESIGN_V4.md` §4.1, L113); "Identical dup collapsed" with output "Duplicate record" (`BIONEXUS_V1_IMPLEMENTATION_ROADMAP.md` L57); "identical duplicates recorded with a note" (`ANTIGRAVITY_M1_PROMPTS.md` T1.7, L121). `BIONEXUS_V1_CONSOLIDATED_PLAN.md` L152 says only "Exact duplicate samples and genes detected" and L338 says M1 has "No transformation, no gene mapping, no compatibility state, no batch." `AGENT_INSTRUCTIONS.md` §20: "Do not silently delete duplicates." Not stated: whether derived outputs keep all identical copies or one, and in which stage. Raw inputs stay unchanged either way (`BIONEXUS_V1_CONSOLIDATED_PLAN.md` L349, AC2: "Originals byte-identical before and after every run"). | Owner to set | Owner clarification |
| I-10 | Status: Open. Specification gap: handling of duplicate gene rows. `BIONEXUS_V1_RULE_CARDS.md` L24 (M-04) names sample IDs/columns only. `BIONEXUS_V1_SCIENTIFIC_TECHNICAL_DESIGN_V4.md` §4.1, L113 covers "Exact duplicate rows or samples". `BIONEXUS_V1_CONSOLIDATED_PLAN.md` L109 (P-13, output "Derived matrix") says "Exact duplicates collapsed with record; many-to-one aggregation by space (N-03)", and L164 lists N-03 as "ACCEPT-GATED (revised)"; L338 says M1 has "No transformation". `BIONEXUS_V1_IMPLEMENTATION_ROADMAP.md` L57 says "Exact duplicate samples/genes". Not stated: whether and when exact duplicate gene rows are removed from a derived matrix, and whether that step belongs to M1 or to the later gated preprocessing stage. | Owner to set | Owner clarification |

## 3. Resolved issues

| ID | Resolution | Evidence | Date |
|---|---|---|---|
| I-08 | Resolved. The roadmap, workflow chart and Antigravity prompts were delivered, and the owner repo handoff took place. M1 implementation subsequently started; the earlier status "awaiting owner repo handoff / M1 start" is no longer current. | Delivered M0 artifacts; owner-provided repository at `D:\BioNexus`; subsequent M1 implementation activity | 2026-11-24 |
| I-11 | Resolved for T1.7. The duplicate comparison policy is implemented against parsed cell values rather than source-file byte identity. The accepted implementation defines the comparison behavior in `src/bionexus/duplicates.py`; source-file integrity remains a separate concern under AC2. | T1.7 duplicate implementation, commit `41d1ca3`; owner-approved I-11 correction and focused tests | 2026-11-24 |
| I-12 | Resolved and implemented under M-01. Metadata duplicate detection is handled by the dedicated `find_metadata_duplicates(metadata, id_column, scope="matrix")` helper, not by extending M-04 `find_duplicates()`. All metadata rows are retained. Repeated metadata IDs produce NEED_FACT records whether the corresponding rows are identical or conflicting; evidence distinguishes the two cases and identifies differing fields and values. The ID-column validation and blank-ID findings are reported separately under `M-01.metadata_id_column`. | Owner-approved I-12 decisions; implementation commit `45dedd8`; 107 focused metadata tests passed locally | 2026-11-24 |

## 4. Changes

| Date | File | Change | Reason |
|---|---|---|---|
| 2026-11-21 | BIONEXUS_V1_IMPLEMENTATION_ROADMAP.md, ANTIGRAVITY_M1_PROMPTS.md, BIONEXUS_V1_WORKFLOW.png, NEMOTRON_N1_PASTE.md, NEMOTRON_N2_PASTE.md | New files per owner request; no existing file modified | Owner message 2026-11-21 04:21 |
| 2026-11-21 | BIONEXUS_V1_CONSOLIDATED_PLAN.md | Source-check statement corrected; status line set to approved baseline | Owner correction, approval |
| 2026-11-22 | src/bionexus/fileio.py, tests/unit/test_fileio.py | T1.3b (commit 2417c68, branch fix/t1-3b-t1-5b): a delimiter candidate that fails on quoting while another candidate is plausible only by reading a quote as literal text now gives not_assessable instead of a silent guess (D-T1.3-1); added `first_column_as_index` (first column as row labels; exact strings, duplicates preserved, input not mutated). +11 tests | Resolves D-T1.3-1. Adds the `first_column_as_index` helper; its integration into the parse-to-orientation data flow remains for T1.8. Owner authorization 2026-11-22 |
| 2026-11-22 | src/bionexus/representation.py, tests/unit/test_representation.py | T1.5b (commit 9e64cad, branch fix/t1-3b-t1-5b): cells (strings and Python ints) whose exact expansion exceeds 4000 digits are not_assessable (resource-safety bound, not a scientific threshold), closing a hang and a serialization failure on extreme exponents or huge integers (D-T1.5-1); R-05 annotation coverage is now reported on the non-numeric and no-values early-return paths (D-T1.5-2). +32 tests | Resolves D-T1.5-1 and D-T1.5-2. Owner authorization 2026-11-22 |
| 2026-11-24 | src/bionexus/duplicates.py, tests/unit/test_duplicates.py | T1.7 duplicate detection implementation and tests committed as `41d1ca3` | T1.7 duplicate detection implementation |
| 2026-11-24 | src/bionexus/metadata.py, tests/unit/test_metadata.py | T1.7 metadata checks (M-01, M-02, M-03), including the F1 positional-matching collision correction, committed as `033feba` | Implement approved metadata checks and prevent positional matching when normalized IDs collide |
| 2026-11-24 | src/bionexus/metadata.py, tests/unit/test_metadata.py | I-12 metadata duplicate detection committed separately as `45dedd8`; adds `find_metadata_duplicates()` and its evidence/tests without changing `find_duplicates()` or `match_samples()` | Implement the approved M-01 metadata duplicate-row behavior |
| 2026-11-26 | src/bionexus/cli.py, tests/integration/test_intake.py, tests/integration/fixtures/, scripts/coverage_report.py | T1.8 implementation and integration-test artifacts supplied in the working tree; independently reviewed by Claude and accepted as-is. Owner subsequently verified the canonical manifest hash, integration suite, coverage report and full suite locally. No T1.8 commit is recorded. | T1.8 implementation, approved decisions D1–D6, Claude final disposition and owner validation |

## 5. Validation results

Historical baseline: no tests or experiments had been recorded at the time of the previous record update.

| Date | Scope | Result |
|---|---|---|
| 2026-11-22 | T1.3b (2417c68) | 11 regression tests added; the focused test suite passed after the patch |
| 2026-11-22 | T1.5b (9e64cad) | 32 regression tests added; the focused test suite passed after the patch |
| 2026-11-22 | Full test suite on Windows (owner-reported) | 286 passed after both patches (focused fileio and representation tests: 135 passed) |
| 2026-11-22 | Post-commit remote verification of fix/t1-3b-t1-5b | All checks passed: two commits on top of 51d1bed (M1 T1.6), each with only its two intended files, content identical to the delivered patches, `git diff --check` clean |
| 2026-11-24 | T1.7 duplicate detection | Focused tests passed after I-11 correction (owner-confirmed); `git apply --reverse --check` confirmed the correction was applied |
| 2026-11-24 | T1.7 metadata checks and F1 correction (`033feba`) | Owner-reported local result: 70 tests passed in `tests/unit/test_metadata.py` |
| 2026-11-24 | T1.7 I-12 metadata duplicate detection (`45dedd8`) | Owner-reported local result: 107 tests passed in `tests/unit/test_metadata.py`; `git diff --check` clean |
| 2026-11-24 | T1.8 implementation report (not independently verified) | NEON/Antigravity reported 65 integration tests, 566 full-suite tests and AC8 PASS. These were agent-reported results only and were superseded by later independent review and owner validation. |
| 2026-11-24 | T1.8 independent source review | Read-only review of user-provided `cli.py`, `test_intake.py`, `provenance.py`, `fileio.py`, relevant specification excerpts and `AGENT_INSTRUCTIONS.md` §§31–32. Findings and open questions were recorded in §7. No local repository commands or tests were run by the architect. |
| 2026-11-25/26 | T1.8 Claude final independent review | Claude's final disposition: **ACCEPT AS-IS**. No confirmed T1.8 code defects remain. Approved decisions D1, D3, D6, D6a and D6b were satisfied; D6c remained declined. Provenance separation, S0 G-04 failure recording, current-run output tracking, G-01 independent checks, AC2 input preservation, AC1 frozen outcomes and AC8 coverage were reviewed. |
| 2026-11-26 | T1.8 manifest verification (owner-reported, Windows) | Canonical JSON SHA-256 matched the pinned sidecar: `24c257f3b3395f5435353057f2e74bae3cc8a712a683fbe7aa1a887155fcba0b`. F01–F31 manifest entries and F28–F31 fixtures were present. |
| 2026-11-26 | T1.8 integration suite (owner-reported, Windows) | `96 passed, 3 skipped` in 15.70s. |
| 2026-11-26 | T1.8 coverage report (owner-reported, Windows) | AC8 overall: PASS. All ACCEPT_M1 rules scheduled in M1 passed the P/N/E coverage requirement. Rules scheduled for M2–M4 remained correctly marked not_scheduled_in_M1. |
| 2026-11-26 | T1.8 full test suite (owner-reported, Windows) | `636 passed, 3 skipped` in 21.71s. |
| 2026-11-26 | T1.8 Claude scratch validation | Claude reported 97 integration passes / 2 skips as root, 111 integration-plus-provenance passes / 0 skips as non-root, and 636 full-suite passes / 2 skips / 1 failure as root. The full-suite failure was `test_make_read_only_keeps_content_and_blocks_write`, reported as root-specific. These are separate Linux scratch results, not the owner's Windows results. |

## 6. Milestone state

M0: roadmap, workflow chart and prompts delivered; owner repo handoff completed. M1 implementation is underway. N1/N2 must finish by M1 exit, not before M1 start.

2026-11-22: T1.3b (2417c68) and T1.5b (9e64cad) were committed and pushed to `fix/t1-3b-t1-5b`, then merged into `implementation/m1-intake` through PR #1.

2026-11-24: T1.7 duplicate detection implementation was committed as `41d1ca3`. The metadata checks and F1 correction were committed separately as `033feba`; I-12 metadata duplicate detection was committed separately as `45dedd8`. The local branch `implementation/m1-intake` is two commits ahead of `origin/implementation/m1-intake` as of this record update; `033feba` and `45dedd8` have not yet been pushed. I-08, I-11 and I-12 are resolved. I-09 and I-10 remain open specification issues.

Latest owner-provided Git evidence:

- Branch: `implementation/m1-intake`.
- Latest commit: `cad8469 docs: update BioNexus working record through T1.8 review`.
- Owner ran `git push origin implementation/m1-intake`; push output advanced remote from `f3e4aac` to `cad8469`.
- Subsequent `git status -sb` showed `## implementation/m1-intake...origin/implementation/m1-intake`, confirming the tracked branch was synchronized at that point.
- Numerous untracked review artifacts and T1.8 files remained in the working tree. They were not staged, committed, deleted, or otherwise modified during this review. Preserve them.

T1.8: Claude completed the independent review and issued **ACCEPT AS-IS**. The implementation and tests satisfy the applicable approved T1.8 decisions. The owner subsequently verified the canonical fixture-manifest hash, F28–F31 fixture presence, integration suite, AC8 coverage report and full test suite locally on Windows.

The latest owner-reported validation is 96 integration tests passed, 3 skipped; AC8 PASS; and 636 full-suite tests passed, 3 skipped. Claude's Linux scratch validation is recorded separately in §5 and must not be conflated with the owner's Windows results.

T1.8 remains uncommitted. Preserve all untracked implementation and review artifacts. The latest previously verified tracked-branch state remains `implementation/m1-intake` at `cad8469`, synchronized with origin at the time of that Git check. A fresh Git status is required before any future staging or commit.

## 7. T1.8 review record — preliminary observations and final dispositions

**Review boundary:** The original preliminary observations in §§7.1–7.10 were based on source code and excerpts supplied by the owner in chat. At that stage, the architect did not execute the repository, run tests, inspect unshared files, or independently reproduce runtime behavior. Those observations were submitted for Claude's review and are retained below as an audit trail. They are not the final technical disposition. Claude's final disposition and the subsequent owner validation are recorded in §§5, 6, 8 and 9.

### 7.1 Output directory containment

**Observed code:** `src/bionexus/cli.py`, `_validate_out_dir()`:

- Resolves the output path and each input path.
- Rejects only when `resolved_out == resolved_inp` or `resolved_out == resolved_inp.parent`.
- Otherwise creates the output directory with `mkdir(parents=True, exist_ok=True)`.

**Preliminary finding:** The current checks do not reject an output directory nested beneath an input-containing directory. For example, if an input is `D:\data\input\matrix.tsv`, an output directory `D:\data\input\derived` is not equal to the input file or its immediate parent and can pass the shown checks. This permits derived artifacts to be written inside an input folder, contrary to the separation principle.

**Disposition:** Claude reviewed the existing literal-equality/direct-parent containment policy. This broader nested-path policy remains deferred and is documented as a limitation, not silently broadened during T1.8. See §8.

### 7.2 Stale artifacts and reused output directories

**Observed code:**

- `_validate_out_dir()` allows an existing directory through `exist_ok=True`.
- After `parse_matrix()`, the CLI uses `parsed_matrix_path.exists()` to decide whether to add the G-02 provenance step.
- The shown code does not establish that an existing `parsed_matrix.tsv` was created by the current run.
- The pipeline writes other derived files conditionally, including `oriented_matrix.tsv`, `sample_matches.json` and `representation_evidence.json`.

**Preliminary finding:** Reusing an output directory can leave files from an earlier run. In particular, a stale `parsed_matrix.tsv` can cause a G-02 provenance step to be recorded even when the current parse did not create that file. Other stale conditional outputs may also remain visible after an early return.

**Disposition:** Resolved in the reviewed T1.8 implementation. Non-empty output directories are refused, existing empty directories are accepted, absent directories are created, and provenance tracks outputs written by the current run rather than relying solely on file existence. Regression tests cover stale-output behavior and output/provenance consistency. See §8.

### 7.3 S0 input hashing and provenance hash consistency

**Observed code:**

- S0 calculates `h = sha256_file(inp)` and stores it in `input_hashes`.
- It then calls `prov.add_input(inp)`.
- The supplied `provenance.py` implementation of `add_input()` independently calls `sha256_file(path)` again.
- During finalization, `verify_unchanged()` uses the hash stored in `input_hashes`.

**Preliminary finding:** S0 and provenance independently hash the same input instead of sharing the same captured hash. Under stable input conditions these values should match, but a file change between the two reads can make the provenance input hash differ from the hash used for the final unchanged check. This is a consistency/race concern; no runtime reproduction had been performed during the preliminary review.

**Disposition:** Deferred, non-blocking. Double hashing remains a known limitation. A clean change would require revisiting the protected provenance implementation and is not part of the accepted T1.8 scope.

### 7.4 S0 hash failure path

**Observed code:**

- On `OSError` from `sha256_file()`, the CLI appends `verify_unchanged(inp, "")`.
- The failed input is not added to `input_hashes`.
- If fewer than two input hashes are available, the pipeline finalizes without proceeding to S1.

**Preliminary finding:** The pipeline stops before parsing when either input hash is unavailable, which is consistent with treating S0 as a gate. However, passing an empty expected hash to `verify_unchanged()` is an indirect way to record the failure. Depending on whether the second read succeeds, the resulting decision basis may describe an unreadable input or a hash mismatch rather than preserving the original S0 failure explicitly.

**Disposition:** Resolved in the final T1.8 implementation. S0 hash failures produce an explicit G-04 BLOCKED record scoped to the input path (`scope=str(inp)`), without an empty expected SHA-256 value. The `s0_failed` state prevents downstream processing, including the case where the same input path is supplied twice. Claude reported regression coverage for the relevant failure cases.

### 7.5 Metadata parsing failure and downstream dependencies

**Observed code:**

- If `_parse_metadata()` returns `df=None`, the CLI continues after recording its parse records.
- It can still run orientation detection with `metadata_sample_ids=None`.
- If orientation succeeds, it can proceed to representation evidence and duplicate checks.
- Metadata-dependent M-01/M-03 work is conditionally skipped or limited.

**Preliminary finding:** This is confirmed control flow, but not yet a confirmed specification violation. Independent matrix-only checks may be intentionally allowed after metadata parsing failure. The exact dependency and continuation policy must be reconciled with the accepted T1.8 decisions, especially U3a/U3b.

**Disposition:** Claude reviewed the independent-stage behavior and the integration assertions. Relevant tests are characterization tests where authoritative U1–U6 wording is unavailable; this does not create a new specification decision. See §8 and the D5 limitation.

### 7.6 G-01 NEED_FACT independent checks

**Observed test coverage:** The initially supplied G-01 NEED_FACT integration case checked G-01, R-01 candidate evidence and final state, but did not fully assert all independent checks and their records.

**Preliminary finding:** The implementation report and limited assertions did not by themselves establish complete compliance with U3a-rep.

**Disposition:** Resolved in the reviewed T1.8 tests. The strengthened G-01 NEED_FACT test asserts the required independent checks, generated artifacts and final state, while not treating candidate representation evidence as proof of valid scope or compatibility.

### 7.7 Single-column metadata fallback and provenance

**Observed code:** `_parse_metadata()` delegates to `parse_matrix()` and uses a narrowly gated single-column fallback for the exact approved G-02 NOT_ASSESSABLE condition and decision basis. The fallback constructs a new `ParseResult`.

**Preliminary finding:** The fallback behavior appears intentionally constrained by the approved decision. However, the returned result may not preserve all change-log information from the initial `parse_matrix()` result. This needed confirmation against the expected provenance/change-log contract and the exact current code.

**Disposition:** Claude classified the remaining metadata BOM/change-log provenance limitation as deferred and non-blocking. No protected provenance implementation change was included in T1.8.

### 7.8 G-04 read-only wording

**Evidence reviewed:**

- Rule Card G-04 says: "SHA-256 on input; all outputs separate files; originals read-only."
- `AGENT_INSTRUCTIONS.md` §31 says derived artifacts must be separate and versioned, with examples separating `original/`, `derived/` and `reports/`, and says never to overwrite an original dataset.
- §32 requires provenance for every transformation, including input and output files and checksums, operation, parameters, timestamp and software/annotation versions.

**Preliminary finding:** The reviewed §31–32 text clearly requires preservation and non-overwriting, but does not explicitly require changing filesystem permissions on the original input files. Therefore, the absence of a `make_read_only()` call in the CLI was not classified as a confirmed defect based on the evidence then available.

**Disposition:** No filesystem-permission change was authorized as part of T1.8. Claude's Linux root full-suite run reported one failure in `test_make_read_only_keeps_content_and_blocks_write`; the owner's separate Windows full-suite run passed. The environment-specific results are recorded separately in §5 and do not alter the T1.8 ACCEPT AS-IS disposition.

### 7.9 AC5 and early-return paths

The absence of an oriented derived matrix on G-01 BLOCKED or G-03 NEED_FACT paths is not, by itself, an AC5 violation. AC5 value equality should be tested for derived matrices that the pipeline is expected to produce. No conclusion should be drawn that an intentionally absent output must be created merely to satisfy AC5.

**Disposition:** No additional output requirement was introduced by the T1.8 review.

### 7.10 CLI exception handling

**Observed code:** `main()` catches `ValueError` and `OSError` from `run_intake()`. Other exceptions may produce a traceback and nonzero process termination.

**Preliminary finding:** This does not automatically violate U4, which requires nonzero exit for CLI/output creation or write errors. Whether malformed metadata parsing exceptions need conversion into structured assessment records or cleaner CLI messages is a separate behavior/UX question.

**Disposition:** No confirmed T1.8 acceptance-blocking defect was identified. Arbitrary programming errors should not be converted into RuleGap records without an explicit requirement.

### 7.11 Metadata duplicate helper wording limitation (D6c)

**Decision:** D6c was explicitly declined. The protected T1.7 files `src/bionexus/metadata.py` and `tests/unit/test_metadata.py` must remain unchanged as part of T1.8.

The existing helper wording for repeated blank metadata IDs is retained. The evidence distinguishes repeated blank values through `blank:true` in the `M-01.duplicate_metadata_rows` record, together with the sibling `M-01.metadata_id_column` record identifying `blank_ids`.

Repeated blank values do not establish that the corresponding rows represent duplicate biological samples. All metadata rows remain retained.

**Disposition:** Documentation limitation only; no helper wording or protected-file amendment is authorized. Record the limitation without silently changing the T1.7 implementation.

## 8. Claude final review and disposition

Claude's independent review is complete.

**Final disposition: ACCEPT AS-IS.**

Claude reviewed the T1.8 implementation, integration tests, approved decisions, provenance behavior, output-directory policy, current-run output tracking, test coverage and scope constraints. No confirmed code or test defect remains that requires a T1.8 correction.

The review dispositions include:

1. **D1 — Required metadata ID column:** satisfied. `--metadata-id-column NAME` is required by the CLI. `run_intake()` requires the keyword-only `metadata_id_column: str` argument with no default. Non-string values raise `TypeError`.
2. **D3 — Output directory policy:** satisfied. Non-empty output directories are refused, existing empty directories are accepted, and absent directories are created. The check occurs before input hashing/parsing. No deletion or overwrite of pre-existing output contents is performed.
3. **D6 — Configured metadata ID column:** satisfied. The configured ID column is the sole ID column used for metadata duplicate validation and sample matching. The implementation does not fall back to a hard-coded `sample_id` column. Invalid ID-column structure prevents matching while independent checks continue as approved.
4. **D6a — Repeated blank IDs:** satisfied. The metadata ID-column finding and duplicate-row finding are both recorded; `blank:true` distinguishes repeated blank values. All metadata rows are retained.
5. **D6b — API argument contract:** satisfied. `metadata_id_column` is required and non-string values are rejected.
6. **D6c — Helper wording:** declined. Protected T1.7 helper and test files remain unchanged. The wording limitation is documented in §7.11.
7. **Provenance:** metadata ID validation and sample matching are represented as separate provenance steps. Validation records the metadata input and no output. Matching is recorded only when matching actually runs and its output is written. The S0 G-04 failure record uses the input path as its scope and does not use an empty expected hash.
8. **S0 duplicate input-path failure:** a defect in which the same input path supplied twice could incorrectly allow processing was identified and corrected in the final reviewed implementation. The final implementation uses explicit S0 failure state and includes regression cases.
9. **G-01 NEED_FACT:** the strengthened integration test checks independent checks, generated artifacts and final state.
10. **Current-run outputs:** provenance tracks outputs written by the current run. Regression tests cover stale output behavior and output/provenance consistency.
11. **AC1:** frozen F01–F27 expected states are preserved. The owner subsequently verified the canonical manifest hash and F28–F31 fixtures.
12. **AC2:** input preservation/hash-lock checks passed in Claude's review.
13. **AC8:** PASS.
14. **AC9:** PASS according to Claude's review; no GSE accession pattern was identified in the reviewed `src` and tests scope.
15. **Scope:** the reviewed implementation changes were limited to the authorized T1.8 implementation and test scope; protected T1.7 files were not modified.

### 8.1 Remaining limitations — non-blocking

The following limitations remain documented and are not T1.8 acceptance blockers:

- **D2:** existing literal-equality/direct-parent containment policy remains. Broader nested-path policy is deferred.
- **D4:** interim Tier A field list remains `condition`, `tissue`, `organism`.
- **D5:** authoritative U1–U6 wording remains unavailable; relevant tests are characterization tests.
- **Double hashing:** S0 and provenance continue to hash inputs independently. A clean API-level correction would require revisiting protected provenance code.
- **Metadata BOM/change-log provenance:** the limitation remains deferred; it reflects existing T1.7 behavior.
- **D6c:** helper wording limitation remains documentation-only.

### 8.2 Independent validation environment distinction

Claude's Linux scratch validation was performed using a reconstructed scratch environment and fixtures based on the handoff specification. These results are not the same run as the owner's local Windows validation.

Claude reported:

- Integration tests as root: 97 passed, 2 skipped.
- Integration plus `test_provenance.py` as non-root: 111 passed, 0 skipped.
- Full suite as root: 636 passed, 2 skipped, 1 failed. The failure was `test_make_read_only_keeps_content_and_blocks_write`, reported as root-specific.

The owner separately ran the actual local Windows working tree. The owner's results are recorded in §5. The Linux root-specific failure is retained as environment-specific validation evidence and is not represented as a Windows test failure.

**Final decision:** T1.8 is accepted as-is. No corrective implementation, test change or specification amendment is required for T1.8 closure. Any future change requires a separately documented finding, approved decision or explicit owner authorization.

## 9. Current acceptance and change-control status

- T1.8: **ACCEPTED AS-IS** — Claude final disposition.
- Owner validation on Windows: integration suite PASS (`96 passed, 3 skipped`); AC8 PASS; full suite PASS (`636 passed, 3 skipped`).
- Canonical fixture-manifest SHA-256: MATCH.
- F01–F31 manifest entries and F28–F31 fixtures: owner-verified present.
- NEON implementation: accepted as-is; no corrective code changes required by the final review.
- D2, D4, D5 and D6c limitations remain documented as described in §§7–8.
- No T1.8 commit is recorded.
- The latest previously verified tracked-branch state is `implementation/m1-intake` at `cad8469`, synchronized with origin at the time of that Git check. This is historical Git evidence, not a claim about the current working-tree status.
- Preserve all untracked implementation files, fixtures, diffs, backups and review artifacts. Do not stage, commit, push, reset, clean, stash or delete them without explicit owner instruction.
- Do not modify protected T1.1–T1.7 files as part of T1.8 closure.
- Any future change must cite its specific accepted decision, confirmed defect, test result or owner-approved requirement.