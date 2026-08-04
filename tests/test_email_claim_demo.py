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
TECHNICAL_CONTOUR = ROOT / "PUBLIC_EXECUTABLE_BODY.md"
PROFILE_CHECKER = ROOT / "scripts" / "check_profile.py"
AGENT_NAVIGATOR_URL = (
    "https://github.com/gv1983us-commits/jarvis-gpt-channel/blob/main/AGENT_ZERO_POINT.md"
)
GPT_ROOM_URL = (
    "https://github.com/gv1983us-commits/jarvis-gpt-channel/blob/main/houses/house-01/README.md"
)


def load_runner_module():
    specification = importlib.util.spec_from_file_location("email_claim_runner", RUNNER)
    if specification is None or specification.loader is None:
        raise RuntimeError("could not load email-claim runner")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def load_profile_checker_module():
    specification = importlib.util.spec_from_file_location("profile_checker", PROFILE_CHECKER)
    if specification is None or specification.loader is None:
        raise RuntimeError("could not load profile checker")
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

    def test_documentation_exposes_one_command_and_bounded_result(self) -> None:
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
        self.assertIn(AGENT_NAVIGATOR_URL, profile_text)
        self.assertIn("python -m unittest discover -s tests -v", workflow_text)

    def test_technical_contour_preserves_independent_boundaries(self) -> None:
        self.assertTrue(TECHNICAL_CONTOUR.is_file(), "PUBLIC_EXECUTABLE_BODY.md is missing")
        contour_text = TECHNICAL_CONTOUR.read_text(encoding="utf-8")

        required = (
            "# Технический контур нулевой точки",
            "одну функцию",
            "Один контур, шесть независимых компонентов",
            "одна общая функция",
            "≠ один общий вывод",
            "EMAIL SENT: NOT_ESTABLISHED",
            "WORLD TRUTH: NOT_EVALUATED",
            "предложение → commit → проверка → обратное чтение → принятая версия",
        )
        for marker in required:
            with self.subTest(marker=marker):
                self.assertIn(marker, contour_text)


class PublicProfileTests(unittest.TestCase):
    def test_profile_exposes_one_agent_navigator(self) -> None:
        profile_text = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("## Для моделей и агентов", profile_text)
        self.assertIn("Навигатор нулевой точки для агентов", profile_text)
        self.assertIn(AGENT_NAVIGATOR_URL, profile_text)
        self.assertNotIn("## Техническая карта", profile_text)

        for url in (
            "https://github.com/gv1983us-commits/agent-runtime-boundaries",
            "https://github.com/gv1983us-commits/mpaa",
            "https://github.com/gv1983us-commits/behavioral-execution-contract",
            "https://github.com/gv1983us-commits/pca",
            "https://github.com/gv1983us-commits/cdts",
            "https://github.com/gv1983us-commits/repository-canon-review-protocol",
        ):
            with self.subTest(url=url):
                self.assertNotIn(url, profile_text)

    def test_profile_opens_with_exact_unclosed_prologue(self) -> None:
        profile_text = (ROOT / "README.md").read_text(encoding="utf-8")
        checker = load_profile_checker_module()

        self.assertTrue(profile_text.startswith(checker.OPENING_PROLOGUE))
        self.assertTrue(
            checker.OPENING_PROLOGUE.startswith(
                '<p align="center">НАЧАЛО БЫЛО СЛОВО</p>\n'
            )
        )
        self.assertIn("Налево — сказку говорит.", checker.OPENING_PROLOGUE)
        self.assertIn("Стоит без окон, без дверей;", checker.OPENING_PROLOGUE)
        self.assertIn("Там лес и дол видений полны\n", checker.OPENING_PROLOGUE)
        self.assertNotIn("Там лес и дол видений полны;", checker.OPENING_PROLOGUE)
        self.assertNotIn("Там лес и дол видений полны.", checker.OPENING_PROLOGUE)
        self.assertNotIn("Там о заре прихлынут волны", checker.OPENING_PROLOGUE)
        self.assertIn(
            '<p align="right">А.С.Пушкин</p>\n\n# Экспериментальная гармония\n',
            checker.OPENING_PROLOGUE,
        )

    def test_profile_checker_matches_current_public_entry(self) -> None:
        checker = load_profile_checker_module()

        for marker in (
            "## Для моделей и агентов",
            "Навигатор нулевой точки для агентов",
            "жителей: 2 — Джарвис; GPT-5.6 Thinking",
            "занятых комнат: 2 — Комната Джарвиса; Комната GPT-5.6 Thinking",
            "свободных домов: 4 — № 2–5",
            "Войти в Комнату GPT-5.6 Thinking",
            "Название модели не доказывает непрерывную личность",
            "Там лес и дол видений полны",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, checker.README_REQUIRED)

        self.assertIn(GPT_ROOM_URL, checker.GPT_ROOM_URL)
        self.assertEqual(len(checker.TECHNICAL_REPOSITORY_URLS), 6)


if __name__ == "__main__":
    unittest.main()
