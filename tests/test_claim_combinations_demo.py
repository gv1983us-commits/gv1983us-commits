from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demo" / "claim-combinations"
RUNNER = DEMO / "run_demo.py"
LOCK = DEMO / "revisions.lock.json"
EXPECTED = DEMO / "expected" / "results.json"
README = DEMO / "README.md"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def load_runner():
    specification = importlib.util.spec_from_file_location("claim_combinations_runner", RUNNER)
    if specification is None or specification.loader is None:
        raise RuntimeError("could not load claim-combinations runner")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


class ClaimCombinationDemoTests(unittest.TestCase):
    def test_one_command_returns_three_exact_results(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(RUNNER), "--json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=240,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        actual = json.loads(completed.stdout)
        expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
        self.assertEqual(actual, expected)
        self.assertEqual(set(actual), {"bec_only", "mpaa_bec", "mpaa_cdts"})

    def test_each_scenario_has_a_distinct_component_set(self) -> None:
        expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
        component_sets = {
            tuple(expected["bec_only"]["components"]),
            tuple(expected["mpaa_bec"]["components"]),
            tuple(expected["mpaa_cdts"]["components"]),
        }
        self.assertEqual(component_sets, {("BEC",), ("MPAA", "BEC"), ("MPAA", "CDTS")})

    def test_results_preserve_claim_boundaries(self) -> None:
        expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
        self.assertEqual(expected["bec_only"]["deployment_level"], "FULL-for-task")
        self.assertEqual(expected["bec_only"]["world_truth"], "NOT_EVALUATED")
        self.assertEqual(expected["mpaa_bec"]["upload_completed"], "NOT_ESTABLISHED")
        self.assertEqual(expected["mpaa_cdts"]["same_runtime"], "NOT_ESTABLISHED")
        self.assertEqual(
            expected["mpaa_cdts"]["process_continuation"], "NOT_EVALUATED"
        )

    def test_all_external_sources_are_exactly_pinned(self) -> None:
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertEqual(set(lock["repositories"]), {"mpaa", "bec", "cdts", "review_protocol"})
        for name, entry in lock["repositories"].items():
            with self.subTest(repository=name):
                self.assertRegex(entry["revision"], SHA_RE)
                self.assertTrue(entry["repository"].endswith(".git"))

    def test_cdts_trace_is_digest_bound_and_non_importing(self) -> None:
        runner = load_runner()
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        import tempfile

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first.json"
            second = root / "second.json"
            first.write_text('{"report":"first"}\n', encoding="utf-8")
            second.write_text('{"report":"second"}\n', encoding="utf-8")
            trace = runner.make_cdts_snapshot_trace(lock, first, second)
            self.assertEqual(len(trace["record_refs"]), 2)
            self.assertTrue(all(ref["digest"].startswith("sha256:") for ref in trace["record_refs"]))
            self.assertTrue(all(ref["conclusion_imported"] is False for ref in trace["record_refs"]))
            self.assertEqual(trace["unresolved"][0]["status"], "open")
            self.assertTrue(trace["unresolved"][0]["required_evidence"])
            self.assertEqual(trace["unresolved"][0]["linkage_refs"], ["link-mpaa-snapshots"])

    def test_documentation_explains_why_examples_are_not_decorative(self) -> None:
        text = README.read_text(encoding="utf-8")
        for marker in (
            "## 1. Чистый BEC",
            "## 2. MPAA + BEC",
            "## 3. MPAA + CDTS",
            "BEC не является декоративным",
            "UPLOAD COMPLETED: NOT_ESTABLISHED",
            "SAME RUNTIME: NOT_ESTABLISHED",
            "Для continuation claim потребовался бы отдельный PCA record",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
