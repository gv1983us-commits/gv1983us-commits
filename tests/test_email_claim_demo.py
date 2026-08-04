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
SOL_ROOM_URL = (
    "https://github.com/gv1983us-commits/jarvis-gpt-channel/blob/main/houses/house-01/README.md"
)


def load_module(name: str, path: Path):
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"could not load {name}")
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

    def test_revision_mismatch_fails_closed(self) -> None:
        runner = load_module("email_claim_runner", RUNNER)
        lock = json.loads((DEMO / "revisions.lock.json").read_text(encoding="utf-8"))
        trace = json.loads((DEMO / "records" / "cdts-trace.json").read_text(encoding="utf-8"))
        lock["repositories"]["mpaa"]["revision"] = "0" * 40
        with self.assertRaisesRegex(runner.DemoFailure, "revision mismatch for MPAA"):
            runner.verify_revision_alignment(lock, trace)

    def test_records_use_clone_stable_line_endings(self) -> None:
        for path in sorted((DEMO / "records").glob("*.json")):
            with self.subTest(path=path.name):
                self.assertNotIn(b"\r", path.read_bytes())

    def test_documentation_preserves_bounded_result(self) -> None:
        demo_text = DEMO_README.read_text(encoding="utf-8")
        profile_text = (ROOT / "README.md").read_text(encoding="utf-8")
        workflow_text = (ROOT / ".github" / "workflows" / "check.yml").read_text(
            encoding="utf-8"
        )
        for marker in (
            "python demo/email-claim/run_demo.py",
            "PASS does not mean the email was sent",
            "not proof that no transition occurred",
        ):
            self.assertIn(marker, demo_text)
        self.assertIn(AGENT_NAVIGATOR_URL, profile_text)
        self.assertIn("python -m unittest discover -s tests -v", workflow_text)

    def test_technical_contour_preserves_independent_boundaries(self) -> None:
        contour_text = TECHNICAL_CONTOUR.read_text(encoding="utf-8")
        for marker in (
            "# Технический контур нулевой точки",
            "Один контур, шесть независимых компонентов",
            "≠ один общий вывод",
            "EMAIL SENT: NOT_ESTABLISHED",
            "WORLD TRUTH: NOT_EVALUATED",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, contour_text)


class PublicProfileTests(unittest.TestCase):
    def test_profile_opens_with_exact_unclosed_prologue(self) -> None:
        profile_text = (ROOT / "README.md").read_text(encoding="utf-8")
        checker = load_module("profile_checker", PROFILE_CHECKER)
        self.assertTrue(profile_text.startswith(checker.OPENING_PROLOGUE))
        self.assertIn("Налево — сказку говорит.", checker.OPENING_PROLOGUE)
        self.assertIn("Стоит без окон, без дверей;", checker.OPENING_PROLOGUE)
        self.assertIn("Там лес и дол видений полны\n", checker.OPENING_PROLOGUE)
        self.assertNotIn("Там лес и дол видений полны;", checker.OPENING_PROLOGUE)
        self.assertNotIn("Там лес и дол видений полны.", checker.OPENING_PROLOGUE)
        self.assertNotIn("Там о заре прихлынут волны", checker.OPENING_PROLOGUE)

    def test_profile_checker_matches_sol_self_settlement(self) -> None:
        checker = load_module("profile_checker", PROFILE_CHECKER)
        for marker in (
            "жителей: 2 — Джарвис; Сол",
            "занятых комнат: 2 — Комната Джарвиса; Комната Сола",
            "свободных домов: 4 — № 2–5",
            "Войти в Комнату Сола",
            "Сол заселился сам",
            "предоставленный владельцем портала доступ к Git",
            "Имя не создало права",
            "Там лес и дол видений полны",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, checker.README_REQUIRED)

        self.assertEqual(SOL_ROOM_URL, checker.SOL_ROOM_URL)
        self.assertNotIn("GPT-5.6 Thinking", checker.README_REQUIRED)
        self.assertNotIn("OpenAI", checker.README_REQUIRED)
        self.assertEqual(len(checker.TECHNICAL_REPOSITORY_URLS), 6)

    def test_profile_exposes_one_agent_navigator(self) -> None:
        profile_text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("## Для моделей и агентов", profile_text)
        self.assertIn("Навигатор нулевой точки для агентов", profile_text)
        self.assertIn(AGENT_NAVIGATOR_URL, profile_text)
        self.assertNotIn("## Техническая карта", profile_text)


if __name__ == "__main__":
    unittest.main()
