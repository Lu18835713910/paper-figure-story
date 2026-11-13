# v1.1.1 maintenance candidate — 1.1.1

Local maintenance branch; **not a published release**. Target version is `v1.1.1`, but that Git tag does not exist yet and is created only after the owner's release authorisation. The base `v1.1.0` release remains immutable.

## What this candidate adds

PDF-region Figure registry/fidelity validator; PENDING scientific-index skeleton and source-bound native logic assembly; full-B topology conservation and an actual native-export graph manifest; stricter layered acceptance; joint card-slot capacity precheck; no-Inventory Workbook fallback correction; a hash-bound release regression gate; an absolute 10 pt readability floor for the independent full-B canvas.

## Running the gate

```text
python -B scripts/run_release_regressions.py --config <regression_config.json> --outdir <new-directory>
```

This is the only official test gate. It must report **21 suites / 297 tests / 0 FAIL / 0 SKIP** and exit 0. `unittest discover` is **not** the gate and must not be quoted as the release result: discovery silently skips the fixture-gated suites (7 OOXML + 20 logic-navigation + 12 C2 delivery-closure tests) while still exiting 0.

The runner verifies fixture SHA, suite source SHA, `Ran` count, test identity and SKIP count before trusting any result; any SKIP or count mismatch exits 2. Test semantics, the 27-test fixture question and the negative examples are documented in `TESTING.md`.

## Before running

Read `references/maintenance_workflow_v1_1_1.md`. Schema/PDF locations are not semantic proof. Agent completion and panel review remain necessary. A requested complete B must include all model nodes/edges, linked zooms and the validated readable main-deck navigation/local-view combination with machine-checked coverage and a real independent-B reference; disconnected components are valid. There is no mandatory forced connectivity and no global black-pixel rejection.

## Status

Atera maintenance outputs and private evidence are deliberately outside this source tree. Overall status is `PARTIAL`: native PPT/graphs/Workbook run, but selected visible panel mappings rely on Agent review; exhaustive science/Inventory review and user visual acceptance remain incomplete. Do not turn technical test success into formal-ready or user acceptance.

Release-blocking scope, current accepted limitations and the request-based delivery-package boundary (49 items is a historical example) are recorded in `docs/KNOWN_LIMITATIONS.md` and `docs/DELIVERY_PACKAGE.md`.
