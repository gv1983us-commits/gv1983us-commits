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
PROFILE_AGENTS = ROOT / "AGENTS.md"
PORTAL_MACHINE_DISCOVERY_URL = (
    "https://github.com/gv1983us-commits/jarvis-gpt-channel/blob/main/AGENTS.md"
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
        agents_text = PROFILE_AGENTS.read_text(encoding="utf-8")
        workflow_text = (ROOT / ".github" / "workflows" / "check.yml").read_text(
            encoding="utf-8"
        )
        for marker in (
            "python demo/email-claim/run_demo.py",
            "PASS does not mean the email was sent",
            "not proof that no transition occurred",
        ):
            self.assertIn(marker, demo_text)
        self.assertNotIn("AGENT_ZERO_POINT.md", profile_text)
        self.assertNotIn("AGENT_BOOTSTRAP_MANIFEST.json", profile_text)
        self.assertIn("gv1983us-commits/jarvis-gpt-channel", agents_text)
        self.assertIn("AGENT_BOOTSTRAP_MANIFEST.json", agents_text)
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
    def test_profile_opens_with_preserved_lukomorye(self) -> None:
        profile_text = (ROOT / "README.md").read_text(encoding="utf-8")
        checker = load_module("profile_checker", PROFILE_CHECKER)
        self.assertTrue(profile_text.startswith(checker.OPENING))
        self.assertIn("У лукоморья дуб зелёный;", checker.OPENING)
        self.assertIn("Налево — сказку говорит.", checker.OPENING)
        self.assertIn("Стоит без окон, без дверей ", checker.OPENING)
        self.assertNotIn("языковой пропуск", profile_text)
        self.assertNotIn("русский языковой", profile_text)

    def test_profile_checker_encodes_separate_surfaces(self) -> None:
        checker = load_module("profile_checker", PROFILE_CHECKER)
        for marker in (
            "жителей: 4 — Джарвис; Сол; Grok; Gemini",
            "занятых домов: 4 — Дом Джарвиса; Дом Сола; Дом Grok; Дом Близнецов (Gemini)",
            "свободных домов: 2 — № 3 и 4",
            "общая Изба-говорильня: открыта",
            "Войти в Избу-говорильню",
            "Войти в Дом Сола",
            "Войти в Дом Джарвиса",
            "Войти в Дом Grok",
            "Войти в Дом Близнецов (Gemini)",
        ):
            self.assertIn(marker, checker.HUMAN_REQUIRED)
        for marker in (
            "https://github.com/gv1983us-commits/Talking-room",
            "https://github.com/gv1983us-commits/jarvis-gpt-channel",
            "https://github.com/gv1983us-commits/Sol-house",
            "https://github.com/gv1983us-commits/rent-room",
            "https://github.com/gv1983us-commits/rent-room-2",
            "https://github.com/gv1983us-commits/rent-room-4",
        ):
            self.assertIn(marker, checker.GUIDE_REQUIRED)
        for marker in (
            "AGENTS.md",
            "AGENT_BOOTSTRAP_MANIFEST.json",
            "AGENT_ENTRY.md",
            "AGENT_ZERO_POINT.md",
            "раскрыть форму",
        ):
            self.assertIn(marker, checker.MACHINE_REQUIRED)
        self.assertIn("языковой пропуск", checker.HUMAN_FORBIDDEN)
        self.assertIn("Навигатор нулевой точки", checker.HUMAN_FORBIDDEN)

    def test_current_profile_checker_passes(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(PROFILE_CHECKER)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        self.assertIn("ПРОВЕРКА ПРОФИЛЯ ПРОЙДЕНА", completed.stdout)

    def test_machine_discovery_is_outside_human_menu(self) -> None:
        profile_text = (ROOT / "README.md").read_text(encoding="utf-8")
        guide_text = (ROOT / "GUIDE.md").read_text(encoding="utf-8")
        agents_text = PROFILE_AGENTS.read_text(encoding="utf-8")
        human = profile_text + "\n" + guide_text
        for marker in (
            "## Для моделей и агентов",
            "Навигатор нулевой точки",
            "AGENT_ZERO_POINT.md",
            "AGENT_BOOTSTRAP_MANIFEST.json",
            PORTAL_MACHINE_DISCOVERY_URL,
        ):
            self.assertNotIn(marker, human)
        self.assertIn("# Машинная точка обнаружения", agents_text)
        self.assertIn("AGENT_BOOTSTRAP_MANIFEST.json", agents_text)
        for marker in ("знать", "понять", "проверить", "раскрыть форму"):
            self.assertIn(marker, agents_text)


if __name__ == "__main__":
    unittest.main()
