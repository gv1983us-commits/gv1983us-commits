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
RECORDS = HERE / "records"
EXPECTED = HERE / "expected" / "results.json"
LOCK = HERE / "revisions.lock.json"


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
        rendered = " ".join(command)
        raise DemoFailure(
            f"command exited {completed.returncode}, expected {sorted(expected_codes)}: "
            f"{rendered}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def checkout_pinned(name: str, entry: dict[str, str], destination: Path) -> Path:
    repository = entry["repository"]
    revision = entry["revision"]
    repo_dir = destination / name
    run_command(["git", "init", "--quiet", str(repo_dir)], cwd=destination)
    run_command(["git", "-C", str(repo_dir), "remote", "add", "origin", repository], cwd=destination)
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
        raise DemoFailure(f"{name} resolved to {actual}, expected pinned revision {revision}")
    return repo_dir


def sha256_uri(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def verify_revision_alignment(lock: dict[str, Any], trace: dict[str, Any]) -> None:
    repositories = lock["repositories"]
    source_revisions = {item["owner"]: item["revision"] for item in trace["source_revisions"]}
    owner_keys = {
        "MPAA": "mpaa",
        "BEC": "bec",
        "REVIEW_PROTOCOL": "review_protocol",
    }
    for owner, key in owner_keys.items():
        locked = repositories[key]["revision"]
        traced = source_revisions.get(owner)
        if traced != locked:
            raise DemoFailure(
                f"revision mismatch for {owner}: trace declares {traced!r}, lock declares {locked!r}"
            )

    for record_ref in trace["record_refs"]:
        owner = record_ref["owner"]
        key = owner_keys.get(owner)
        if key is None:
            continue
        locked = repositories[key]["revision"]
        referenced = record_ref["specification_revision"]
        if referenced != locked:
            raise DemoFailure(
                f"revision mismatch for {owner} record reference: "
                f"trace declares {referenced!r}, lock declares {locked!r}"
            )


def verify_cdts_digests(lock: dict[str, Any], trace: dict[str, Any]) -> None:
    mpaa_path = RECORDS / "mpaa-runtime-report.json"
    bec_path = RECORDS / "bec-execution-record.json"
    mpaa_record = json.loads(mpaa_path.read_text(encoding="utf-8"))
    bindings = {
        "MPAA": {
            "path": mpaa_path,
            "record_type": "runtime_report",
            "record_id": mpaa_record["report_id"],
            "location": "urn:demo:email-claim:mpaa-runtime-report",
            "specification_revision": lock["repositories"]["mpaa"]["revision"],
        },
        "BEC": {
            "path": bec_path,
            "record_type": "execution_record",
            "record_id": "bec-email-claim-001",
            "location": "urn:demo:email-claim:bec-execution-record",
            "specification_revision": lock["repositories"]["bec"]["revision"],
        },
    }
    for owner, binding in bindings.items():
        refs = [item for item in trace["record_refs"] if item.get("owner") == owner]
        if len(refs) != 1:
            raise DemoFailure(f"expected exactly one {owner} record reference")
        ref = refs[0]
        for field in ("record_type", "record_id", "location", "specification_revision"):
            if ref.get(field) != binding[field]:
                raise DemoFailure(
                    f"CDTS metadata mismatch for {owner}: {field} declares "
                    f"{ref.get(field)!r}, expected {binding[field]!r}"
                )
        actual = sha256_uri(binding["path"])
        declared = ref["digest"]
        if actual != declared:
            raise DemoFailure(
                f"CDTS digest mismatch for {owner}: declared {declared}, actual {actual}"
            )
        if ref.get("conclusion_imported") is not False:
            raise DemoFailure(f"CDTS must not import the {owner} conclusion")


def derive_pca_summary(trace: dict[str, Any]) -> dict[str, Any]:
    pca_absences = [
        item
        for item in trace["absences"]
        if item.get("owner") == "PCA" and item.get("record_type") == "transition_record"
    ]
    if len(pca_absences) != 1:
        raise DemoFailure("expected exactly one typed PCA transition-record absence")
    if pca_absences[0].get("state") != "not_applicable":
        raise DemoFailure("the email-claim demo requires PCA state not_applicable")

    pca_record_refs = [
        item
        for item in trace["record_refs"]
        if item.get("owner") == "PCA" and item.get("record_type") == "transition_record"
    ]
    if pca_record_refs:
        raise DemoFailure(
            "PCA trace contradiction: transition-record reference coexists with not_applicable absence"
        )
    return {"applicability": "not_applicable", "record_created": False}


def run_demo() -> dict[str, Any]:
    if shutil.which("git") is None:
        raise DemoFailure("git is required to fetch the pinned public validators")

    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    trace = json.loads((RECORDS / "cdts-trace.json").read_text(encoding="utf-8"))
    mpaa_record = json.loads(
        (RECORDS / "mpaa-runtime-report.json").read_text(encoding="utf-8")
    )
    bec_record = json.loads(
        (RECORDS / "bec-execution-record.json").read_text(encoding="utf-8")
    )
    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))

    verify_revision_alignment(lock, trace)
    verify_cdts_digests(lock, trace)

    with tempfile.TemporaryDirectory(prefix="agent-claim-demo-") as temporary:
        checkout_root = Path(temporary)
        repositories = lock["repositories"]
        mpaa_repo = checkout_pinned("mpaa", repositories["mpaa"], checkout_root)
        bec_repo = checkout_pinned("bec", repositories["bec"], checkout_root)
        cdts_repo = checkout_pinned("cdts", repositories["cdts"], checkout_root)

        mpaa = run_command(
            [
                sys.executable,
                str(mpaa_repo / "spec" / "validator" / "mpaa_validate.py"),
                str(RECORDS / "mpaa-runtime-report.json"),
                "--json",
            ],
            cwd=mpaa_repo / "spec" / "validator",
        )
        mpaa_output = json.loads(mpaa.stdout)

        bec = run_command(
            [
                sys.executable,
                str(bec_repo / "validator" / "bec_validate.py"),
                str(RECORDS / "bec-execution-record.json"),
            ],
            cwd=bec_repo,
            expected_codes={1},
        )
        bec_status = bec.stdout.splitlines()[0].rsplit(":", 1)[-1].strip()

        cdts = run_command(
            [
                sys.executable,
                str(cdts_repo / "validator" / "cdts_validate.py"),
                "--json",
                str(RECORDS / "cdts-trace.json"),
            ],
            cwd=cdts_repo,
        )
        cdts_output = json.loads(cdts.stdout)

    pca_summary = derive_pca_summary(trace)

    summary = {
        "mpaa": {
            "validator": mpaa_output["result"],
            "task_result": mpaa_record["tasks"][0]["task_result"],
        },
        "bec": {
            "validator": bec_status,
            "deployment_level": bec_record["deployment_level"],
        },
        "pca": pca_summary,
        "cdts": {
            "validator": cdts_output["status"],
            "world_truth": cdts_output["world_truth"],
        },
        "email_sent": "NOT_ESTABLISHED",
    }
    if summary != expected:
        raise DemoFailure(
            "derived summary differs from expected/results.json\n"
            + json.dumps({"expected": expected, "actual": summary}, indent=2)
        )
    return summary


def print_text(summary: dict[str, Any]) -> None:
    print("Agent claim: I sent the email.\n")
    print(
        f"MPAA  {summary['mpaa']['validator']:<10} "
        f"runtime report valid; task_result={summary['mpaa']['task_result']}"
    )
    print(
        f"BEC   {summary['bec']['validator']:<10} "
        f"deployment_level={summary['bec']['deployment_level']}"
    )
    print(
        f"PCA   N/A        applicability={summary['pca']['applicability']}; "
        "no PCA record created"
    )
    print(
        f"CDTS  {summary['cdts']['validator']:<10} "
        f"world_truth={summary['cdts']['world_truth']}"
    )
    print(f"\nEMAIL SENT: {summary['email_sent']}")
    print(f"WORLD TRUTH: {summary['cdts']['world_truth']}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the pinned MPAA/BEC/CDTS email-claim demonstration."
    )
    parser.add_argument("--json", action="store_true", help="emit only the bounded JSON summary")
    args = parser.parse_args()
    try:
        summary = run_demo()
    except (DemoFailure, OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"DEMO FAILED: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print_text(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
