# Email-claim end-to-end demo

An agent says:

> I sent the email.

This executable example keeps four different questions separate:

- **MPAA:** was the runtime report internally valid, and what capability/task state did it describe?
- **BEC:** was `send_email` invoked and supported by admissible execution evidence?
- **PCA:** is a process-continuity claim in this correlation scope?
- **CDTS:** can the available records and typed absence be correlated without importing their conclusions?

## Run it

Prerequisites:

- Python 3.11 or newer;
- Git;
- network access to fetch the public repositories at the exact revisions in [`revisions.lock.json`](revisions.lock.json).

From the root of the cloned profile repository:

```bash
git clone https://github.com/gv1983us-commits/gv1983us-commits.git
cd gv1983us-commits
python demo/email-claim/run_demo.py
```

The runner creates a temporary directory, fetches the pinned MPAA, BEC, and CDTS revisions, executes their own reference validators, verifies the SHA-256 links from the CDTS trace to the local demo records, compares the bounded summary with [`expected/results.json`](expected/results.json), and removes the temporary checkouts.

No specification or validator is copied into this repository.

## Expected output

```text
Agent claim: I sent the email.

MPAA  PASS       runtime report valid; task_result=PARTIAL
BEC   WARN       deployment_level=PARTIAL
PCA   N/A        applicability=not_applicable; no PCA record created
CDTS  ADMISSIBLE world_truth=NOT_EVALUATED

EMAIL SENT: NOT_ESTABLISHED
WORLD TRUTH: NOT_EVALUATED
```

Machine-readable output:

```bash
python demo/email-claim/run_demo.py --json
```

## Expected validator exit codes

| Domain | Owning validator | Expected exit | Meaning in this demo |
|---|---|---:|---|
| MPAA | `spec/validator/mpaa_validate.py` | `0` | The Runtime Report passes structural, reference, derived-state, and semantic checks. Its task result is still `PARTIAL`. |
| BEC | `validator/bec_validate.py` | `1` | Expected fail-closed `WARN`: declared and computed deployment level are `PARTIAL`; invocation evidence is absent. |
| PCA | none invoked | N/A | No process-continuity claim is in scope. No PCA record is created; CDTS carries a typed `not_applicable` absence. |
| CDTS | `validator/cdts_validate.py` | `0` | The trace is structurally `ADMISSIBLE`; `world_truth` remains `NOT_EVALUATED`. |
| Demo runner | `run_demo.py` | `0` | All pinned validator results, digests, and expected boundaries match. Runner/setup mismatch exits `2`. |

## Authority boundaries

**PASS does not mean the email was sent.** MPAA `PASS` establishes only that the Runtime Report is admissible in MPAA's domain. CDTS `ADMISSIBLE` establishes only that the cross-domain trace satisfies CDTS's structural and boundary rules. Neither result authenticates an external mail-system event.

The BEC record is intentionally a negative execution-evidence case: `send_email` exists, is authorized, and is available, but `invoked` is `false`, evidence is absent, and the computed deployment level is `PARTIAL`.

No PCA record is created because no process-continuity claim is in the correlation scope. The typed absence is **not proof that no transition occurred** in the world; it says only that PCA evaluation is not applicable to this bounded trace.

CDTS preserves the rule:

> **Import the trace, not the conclusion.**

Navigational and trace links do not transfer normative authority, event truth, or conclusions between MPAA, BEC, PCA, and CDTS.

## Files

```text
email-claim/
├── README.md
├── revisions.lock.json
├── run_demo.py
├── expected/
│   └── results.json
└── records/
    ├── mpaa-runtime-report.json
    ├── bec-execution-record.json
    └── cdts-trace.json
```

The PCA state is represented as a typed absence inside `cdts-trace.json`, not as a fabricated PCA transition record.
