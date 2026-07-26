from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demo" / "email-claim"
RUNNER = DEMO / "run_demo.py"
DEMO_README = DEMO / "README.md"


def load_runner_module():
    specification = importlib.util.spec_from_file_location("email_claim_runner", RUNNER)
    if specification is None or specification.loader is None:
        raise RuntimeError("could not load email-claim runner")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


class EmailClaimDemoTests(unittest.TestCase):
    def test_one_command_returns_bounded_cross_domain_summary(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(RUNNER), "--json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=180,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        summary = json.loads(completed.stdout)
        self.assertEqual(summary["mpaa"], {"validator": "PASS", "task_result": "PARTIAL"})
        self.assertEqual(summary["bec"], {"validator": "WARN", "deployment_level": "PARTIAL"})
        self.assertEqual(summary["pca"], {"applicability": "not_applicable", "record_created": False})
        self.assertEqual(
            summary["cdts"],
            {"validator": "ADMISSIBLE", "world_truth": "NOT_EVALUATED"},
        )
        self.assertEqual(summary["email_sent"], "NOT_ESTABLISHED")

    def test_lock_trace_revision_mismatch_fails_closed(self) -> None:
        runner = load_runner_module()
        self.assertTrue(
            hasattr(runner, "verify_revision_alignment"),
            "runner has no lock-to-trace revision alignment check",
        )
        lock = json.loads((DEMO / "revisions.lock.json").read_text(encoding="utf-8"))
        trace = json.loads((DEMO / "records" / "cdts-trace.json").read_text(encoding="utf-8"))
        lock["repositories"]["mpaa"]["revision"] = "0" * 40

        with self.assertRaisesRegex(runner.DemoFailure, "revision mismatch for MPAA"):
            runner.verify_revision_alignment(lock, trace)

    def test_cdts_reference_metadata_is_bound_to_local_record(self) -> None:
        runner = load_runner_module()
        lock = json.loads((DEMO / "revisions.lock.json").read_text(encoding="utf-8"))
        trace = json.loads((DEMO / "records" / "cdts-trace.json").read_text(encoding="utf-8"))
        mpaa_ref = next(item for item in trace["record_refs"] if item["owner"] == "MPAA")
        mpaa_ref["record_id"] = "different-report"
        mpaa_ref["location"] = "urn:demo:email-claim:different-report"

        with self.assertRaisesRegex(runner.DemoFailure, "CDTS metadata mismatch for MPAA"):
            runner.verify_cdts_digests(lock, trace)

    def test_duplicate_domain_record_reference_fails_closed(self) -> None:
        runner = load_runner_module()
        lock = json.loads((DEMO / "revisions.lock.json").read_text(encoding="utf-8"))
        trace = json.loads((DEMO / "records" / "cdts-trace.json").read_text(encoding="utf-8"))
        mpaa_ref = next(item for item in trace["record_refs"] if item["owner"] == "MPAA")
        trace["record_refs"].append(dict(mpaa_ref))

        with self.assertRaisesRegex(runner.DemoFailure, "exactly one MPAA record reference"):
            runner.verify_cdts_digests(lock, trace)

    def test_pca_not_applicable_rejects_transition_record_reference(self) -> None:
        runner = load_runner_module()
        self.assertTrue(
            hasattr(runner, "derive_pca_summary"),
            "runner has no fail-closed PCA applicability derivation",
        )
        trace = json.loads((DEMO / "records" / "cdts-trace.json").read_text(encoding="utf-8"))
        trace["record_refs"].append(
            {
                "owner": "PCA",
                "record_type": "transition_record",
            }
        )

        with self.assertRaisesRegex(runner.DemoFailure, "PCA trace contradiction"):
            runner.derive_pca_summary(trace)

    def test_demo_records_use_lf_for_clone_stable_digests(self) -> None:
        for path in sorted((DEMO / "records").glob("*.json")):
            with self.subTest(path=path.name):
                self.assertNotIn(b"\r", path.read_bytes())

    def test_documentation_exposes_one_command_and_authority_boundaries(self) -> None:
        self.assertTrue(DEMO_README.is_file(), "demo/email-claim/README.md is missing")
        demo_text = DEMO_README.read_text(encoding="utf-8")
        profile_text = (ROOT / "README.md").read_text(encoding="utf-8")
        workflow_text = (ROOT / ".github" / "workflows" / "check.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("python demo/email-claim/run_demo.py", demo_text)
        self.assertIn("network access", demo_text)
        self.assertIn("No PCA record is created", demo_text)
        self.assertIn("not proof that no transition occurred", demo_text)
        self.assertIn("PASS does not mean the email was sent", demo_text)
        self.assertIn("demo/email-claim/README.md", profile_text)
        self.assertIn("python -m unittest discover -s tests -v", workflow_text)


if __name__ == "__main__":
    unittest.main()
