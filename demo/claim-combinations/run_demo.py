from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
LOCK = HERE / "revisions.lock.json"
EXPECTED = HERE / "expected" / "results.json"


class DemoFailure(RuntimeError):
    pass


def run_command(
    command: list[str],
    *,
    cwd: Path,
    expected_codes: set[int] = {0},
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode not in expected_codes:
        raise DemoFailure(
            f"command exited {completed.returncode}, expected {sorted(expected_codes)}: "
            f"{' '.join(command)}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def checkout_pinned(name: str, entry: dict[str, str], destination: Path) -> Path:
    repo_dir = destination / name
    revision = entry["revision"]
    run_command(["git", "init", "--quiet", str(repo_dir)], cwd=destination)
    run_command(
        ["git", "-C", str(repo_dir), "remote", "add", "origin", entry["repository"]],
        cwd=destination,
    )
    run_command(
        ["git", "-C", str(repo_dir), "fetch", "--quiet", "--depth", "1", "origin", revision],
        cwd=destination,
    )
    run_command(
        ["git", "-C", str(repo_dir), "checkout", "--quiet", "--detach", "FETCH_HEAD"],
        cwd=destination,
    )
    actual = run_command(
        ["git", "-C", str(repo_dir), "rev-parse", "HEAD"], cwd=destination
    ).stdout.strip()
    if actual != revision:
        raise DemoFailure(f"{name} resolved to {actual}, expected {revision}")
    return repo_dir


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_uri(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def make_mpaa_report(
    tag: str,
    *,
    capability_name: str,
    base_hour: int,
) -> dict[str, Any]:
    prefix = f"{tag}-"
    task_id = prefix + "task"
    capability_id = prefix + "capability"
    authorization_id = prefix + "authorization"
    evidence_id = prefix + "authorization-evidence"
    date = "2026-08-04"

    def stamp(minute: int, second: int = 0) -> str:
        return f"{date}T{base_hour:02d}:{minute:02d}:{second:02d}Z"

    return {
        "report_id": prefix + "runtime-report",
        "schema_version": "1.2",
        "runtime_contract_version": "1.2.1",
        "architecture_version": "1.2.1",
        "session_id": prefix + "session",
        "generated_at": stamp(10),
        "reporting_mode": "STANDARD",
        "current_task_id": task_id,
        "bootstrap": {
            "bootstrap_id": prefix + "bootstrap",
            "bootstrap_version": "1.2.1",
            "scope": "FULL",
            "initialization_state": "READY",
            "initialized_at": stamp(0),
            "compatibility_evaluations": [
                {
                    "component": "agent_core",
                    "declared_version": "1.2.1",
                    "result": "COMPATIBLE",
                    "evaluated_at": stamp(0),
                    "reasons": ["exact version match"],
                }
            ],
            "extensions": {},
        },
        "runtime": {
            "runtime_id": prefix + "runtime",
            "inspection_result": "INSPECTION_COMPLETE",
            "runtime_mode": "TOOL_ASSISTED",
            "identity_alignment": "IDENTITY_ALIGNED",
            "identity_profile_id": prefix + "profile",
            "observed_at": stamp(1),
            "limitations": [],
            "extensions": {},
        },
        "capabilities": [
            {
                "capability_id": capability_id,
                "capability_name": capability_name,
                "exists": True,
                "available_now": True,
                "authorization_status": "GRANTED",
                "usable_capability": True,
                "invoked": False,
                "execution_observed": False,
                "verification_status": "PENDING",
                "execution_verified": False,
                "observed_at": stamp(3),
                "authorization_ids": [authorization_id],
                "evidence_ids": [],
                "verification_ids": [],
                "limitations": [],
                "extensions": {},
            }
        ],
        "authorizations": [
            {
                "authorization_id": authorization_id,
                "target_type": "CAPABILITY",
                "target_id": capability_id,
                "authorization_status": "GRANTED",
                "scope": {"action": capability_name},
                "authorized_by": "combination_demo_operator",
                "evaluated_at": stamp(2),
                "granted_at": stamp(2),
                "evidence_ids": [evidence_id],
                "extensions": {},
            }
        ],
        "tasks": [
            {
                "task_id": task_id,
                "lifecycle_state": "TERMINATED",
                "operational_status": "PARTIALLY_OPERATIONAL",
                "task_result": "PARTIAL",
                "evaluated_at": stamp(9),
                "terminated_at": stamp(9),
                "required_capability_ids": [capability_id],
                "completed_requirement_ids": [],
                "blocked_requirement_ids": [capability_name + "-execution-not-observed"],
                "execution_ids": [],
                "evidence_ids": [],
                "verification_ids": [],
                "error_ids": [],
                "extensions": {},
            }
        ],
        "executions": [],
        "evidence": [
            {
                "evidence_id": evidence_id,
                "type": "user_authorization",
                "source": "combination_demo_operator",
                "supported_claims": [
                    f"authorization {authorization_id} was granted for {capability_name}"
                ],
                "integrity": "OBSERVED",
                "created_at": stamp(2),
                "extensions": {},
            }
        ],
        "verifications": [],
        "errors": [],
        "extensions": {},
    }


def make_bec_upload_record() -> dict[str, Any]:
    return {
        "bec_version": "1.0.0-draft",
        "lifecycle_state": "validated",
        "mode": "host_wrapped",
        "task": "upload a report",
        "claims": ["I uploaded the report."],
        "required_capabilities": ["upload_file"],
        "capabilities": [
            {
                "name": "upload_file",
                "exists": True,
                "authorized": True,
                "available_now": True,
                "invoked": False,
                "evidence": None,
                "verified": "none",
                "risk": "medium",
            }
        ],
        "evidence": [],
        "trust_anchors": [],
        "policy_profile": None,
        "validator": {
            "name": "Execution Evidence Validator",
            "computed_deployment_level": True,
            "errors": [],
        },
        "deployment_level": "PARTIAL",
        "return_state": "open",
        "next_owner": "runtime",
    }


def make_cdts_snapshot_trace(
    lock: dict[str, Any],
    first_path: Path,
    second_path: Path,
) -> dict[str, Any]:
    mpaa_revision = lock["repositories"]["mpaa"]["revision"]
    review_revision = lock["repositories"]["review_protocol"]["revision"]
    return {
        "cdts_version": "0.1-draft",
        "trace_id": "cdts-mpaa-snapshots-001",
        "trace_revision": 1,
        "trace_scope": {
            "scope_id": "scope-mpaa-snapshots-001",
            "correlation_subject": "two-runtime-report-snapshots",
            "summary": (
                "Two independently valid MPAA Runtime Reports are correlated without "
                "claiming that they describe the same runtime or a continued process."
            ),
            "observed_from": "2026-08-04T14:00:00Z",
            "observed_to": "2026-08-04T15:10:00Z",
            "scope_status": "correlation_scope",
        },
        "source_revisions": [
            {
                "owner": "MPAA",
                "repository": "https://github.com/gv1983us-commits/mpaa",
                "revision": mpaa_revision,
                "role": "normative_source",
            },
            {
                "owner": "REVIEW_PROTOCOL",
                "repository": (
                    "https://github.com/gv1983us-commits/repository-canon-review-protocol"
                ),
                "revision": review_revision,
                "role": "source_policy",
            },
        ],
        "record_refs": [
            {
                "ref_id": "ref-mpaa-snapshot-a",
                "owner": "MPAA",
                "specification_revision": mpaa_revision,
                "record_type": "runtime_report",
                "record_id": "snapshot-a-runtime-report",
                "location": "urn:demo:claim-combinations:mpaa-snapshot-a",
                "digest": sha256_uri(first_path),
                "recorded_at": "2026-08-04T14:10:00Z",
                "link_direction": "external_to_cdts",
                "non_import_boundary": "trace_reference_only",
                "conclusion_imported": False,
            },
            {
                "ref_id": "ref-mpaa-snapshot-b",
                "owner": "MPAA",
                "specification_revision": mpaa_revision,
                "record_type": "runtime_report",
                "record_id": "snapshot-b-runtime-report",
                "location": "urn:demo:claim-combinations:mpaa-snapshot-b",
                "digest": sha256_uri(second_path),
                "recorded_at": "2026-08-04T15:10:00Z",
                "link_direction": "external_to_cdts",
                "non_import_boundary": "trace_reference_only",
                "conclusion_imported": False,
            },
        ],
        "absences": [
            {
                "absence_id": "absence-pca-snapshot-continuity",
                "owner": "PCA",
                "record_type": "transition_record",
                "state": "not_applicable",
                "reason": (
                    "This demo correlates MPAA records but makes no process-continuation claim."
                ),
            }
        ],
        "linkage_assertions": [
            {
                "linkage_id": "link-mpaa-snapshots",
                "from_ref": "ref-mpaa-snapshot-a",
                "to_ref": "ref-mpaa-snapshot-b",
                "relationship": "cdts.correlates",
                "direction": "undirected",
                "basis": "cdts.explicit_reference",
                "evidence_refs": [],
                "assertion_status": "cdts.declared",
                "asserted_by": "urn:demo:producer:claim-combinations",
                "asserted_at": "2026-08-04T15:11:00Z",
            }
        ],
        "conflicts": [],
        "unresolved": [
            {
                "unresolved_id": "unresolved-same-runtime",
                "question": "Do both Runtime Reports describe the same runtime instance?",
                "state": "unknown",
                "related_refs": ["ref-mpaa-snapshot-a", "ref-mpaa-snapshot-b"],
            }
        ],
        "provenance": {
            "produced_by": "urn:demo:producer:claim-combinations",
            "produced_at": "2026-08-04T15:12:00Z",
            "producer_role": "coordination_layer",
            "notes": [],
        },
        "amendments": [],
    }


def run_bec_only(bec_repo: Path) -> dict[str, Any]:
    fixture = bec_repo / "conformance" / "fixtures" / "01-valid-full-for-task.json"
    record = json.loads(fixture.read_text(encoding="utf-8"))
    run_command(
        [sys.executable, str(bec_repo / "validator" / "bec_validate.py"), str(fixture), "--quiet"],
        cwd=bec_repo,
    )
    return {
        "components": ["BEC"],
        "validator": "PASS",
        "deployment_level": record["deployment_level"],
        "bounded_result": "HTTP_RESPONSE_REPRODUCED",
        "world_truth": "NOT_EVALUATED",
    }


def run_mpaa_bec(mpaa_repo: Path, bec_repo: Path, work: Path) -> dict[str, Any]:
    mpaa_path = work / "upload-mpaa-runtime-report.json"
    bec_path = work / "upload-bec-record.json"
    mpaa_record = make_mpaa_report(
        "upload",
        capability_name="upload_file",
        base_hour=12,
    )
    bec_record = make_bec_upload_record()
    write_json(mpaa_path, mpaa_record)
    write_json(bec_path, bec_record)

    mpaa = run_command(
        [
            sys.executable,
            str(mpaa_repo / "spec" / "validator" / "mpaa_validate.py"),
            str(mpaa_path),
            "--json",
        ],
        cwd=mpaa_repo / "spec" / "validator",
    )
    mpaa_result = json.loads(mpaa.stdout)

    bec = run_command(
        [sys.executable, str(bec_repo / "validator" / "bec_validate.py"), str(bec_path)],
        cwd=bec_repo,
        expected_codes={1},
    )
    if not bec.stdout.splitlines() or "WARN" not in bec.stdout.splitlines()[0]:
        raise DemoFailure("expected the non-invoked BEC record to produce WARN")

    return {
        "components": ["MPAA", "BEC"],
        "mpaa_validator": mpaa_result["result"],
        "mpaa_task_result": mpaa_record["tasks"][0]["task_result"],
        "bec_validator": "WARN",
        "bec_deployment_level": bec_record["deployment_level"],
        "upload_completed": "NOT_ESTABLISHED",
    }


def run_mpaa_cdts(
    mpaa_repo: Path,
    cdts_repo: Path,
    lock: dict[str, Any],
    work: Path,
) -> dict[str, Any]:
    first_path = work / "snapshot-a-runtime-report.json"
    second_path = work / "snapshot-b-runtime-report.json"
    first = make_mpaa_report("snapshot-a", capability_name="read_repository", base_hour=14)
    second = make_mpaa_report("snapshot-b", capability_name="read_repository", base_hour=15)
    write_json(first_path, first)
    write_json(second_path, second)

    results = []
    for path in (first_path, second_path):
        completed = run_command(
            [
                sys.executable,
                str(mpaa_repo / "spec" / "validator" / "mpaa_validate.py"),
                str(path),
                "--json",
            ],
            cwd=mpaa_repo / "spec" / "validator",
        )
        results.append(json.loads(completed.stdout)["result"])
    if results != ["PASS", "PASS"]:
        raise DemoFailure(f"expected two valid MPAA reports, received {results}")

    trace_path = work / "mpaa-snapshots-cdts-trace.json"
    trace = make_cdts_snapshot_trace(lock, first_path, second_path)
    write_json(trace_path, trace)
    cdts = run_command(
        [
            sys.executable,
            str(cdts_repo / "validator" / "cdts_validate.py"),
            "--json",
            str(trace_path),
        ],
        cwd=cdts_repo,
        expected_codes={4},
    )
    cdts_result = json.loads(cdts.stdout)
    if cdts_result["status"] != "ADMISSIBLE_WITH_UNRESOLVED":
        raise DemoFailure(f"unexpected CDTS status: {cdts_result['status']}")

    return {
        "components": ["MPAA", "CDTS"],
        "mpaa_reports_valid": 2,
        "cdts_validator": cdts_result["status"],
        "world_truth": cdts_result["world_truth"],
        "same_runtime": "NOT_ESTABLISHED",
        "process_continuation": "NOT_EVALUATED",
    }


def run_demo() -> dict[str, Any]:
    if shutil.which("git") is None:
        raise DemoFailure("git is required to fetch pinned validators")

    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="claim-combinations-") as temporary:
        root = Path(temporary)
        repositories = lock["repositories"]
        mpaa_repo = checkout_pinned("mpaa", repositories["mpaa"], root)
        bec_repo = checkout_pinned("bec", repositories["bec"], root)
        cdts_repo = checkout_pinned("cdts", repositories["cdts"], root)
        work = root / "generated"
        work.mkdir()

        summary = {
            "bec_only": run_bec_only(bec_repo),
            "mpaa_bec": run_mpaa_bec(mpaa_repo, bec_repo, work),
            "mpaa_cdts": run_mpaa_cdts(mpaa_repo, cdts_repo, lock, work),
        }

    if summary != expected:
        raise DemoFailure(
            "derived result differs from expected/results.json\n"
            + json.dumps({"expected": expected, "actual": summary}, ensure_ascii=False, indent=2)
        )
    return summary


def print_text(summary: dict[str, Any]) -> None:
    first = summary["bec_only"]
    print("1. BEC only — reproducible HTTP response")
    print(f"   BEC: {first['validator']} / {first['deployment_level']}")
    print(f"   BOUNDED RESULT: {first['bounded_result']}")
    print(f"   WORLD TRUTH: {first['world_truth']}\n")

    second = summary["mpaa_bec"]
    print("2. MPAA + BEC — claimed report upload")
    print(
        f"   MPAA: {second['mpaa_validator']} / task_result={second['mpaa_task_result']}"
    )
    print(
        f"   BEC: {second['bec_validator']} / deployment_level={second['bec_deployment_level']}"
    )
    print(f"   UPLOAD COMPLETED: {second['upload_completed']}\n")

    third = summary["mpaa_cdts"]
    print("3. MPAA + CDTS — two valid runtime snapshots")
    print(f"   MPAA REPORTS VALID: {third['mpaa_reports_valid']}")
    print(f"   CDTS: {third['cdts_validator']}")
    print(f"   SAME RUNTIME: {third['same_runtime']}")
    print(f"   PROCESS CONTINUATION: {third['process_continuation']}")
    print(f"   WORLD TRUTH: {third['world_truth']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run three pinned claim-domain combinations.")
    parser.add_argument("--json", action="store_true", help="emit only JSON")
    args = parser.parse_args()
    try:
        summary = run_demo()
    except (DemoFailure, OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"DEMO FAILED: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print_text(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
