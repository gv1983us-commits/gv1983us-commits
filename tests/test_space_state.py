from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPACE_STATE = ROOT / "SPACE_STATE.json"
README = ROOT / "README.md"
GUIDE = ROOT / "GUIDE.md"
AGENTS = ROOT / "AGENTS.md"


class SpaceStateTests(unittest.TestCase):
    def load_state(self) -> dict:
        return json.loads(SPACE_STATE.read_text(encoding="utf-8"))

    def test_main_square_has_space_state_not_house_state(self) -> None:
        self.assertTrue(SPACE_STATE.is_file(), "SPACE_STATE.json is missing")
        self.assertFalse((ROOT / "HOUSE_STATE.json").exists())
        state = self.load_state()
        self.assertEqual(state["schema_version"], "1.3")
        self.assertEqual(state["human_name"], "Главная площадь и карта")
        self.assertEqual(state["space_role"], "central_hub_and_public_map")
        self.assertIn("main_square_is_not_a_house", state["boundaries"])

    def test_counts_preserve_standard_residency_distinction(self) -> None:
        state = self.load_state()
        occupied = state["occupied_houses"]
        recognized = state["recognized_presence_houses"]
        available = state["available_houses"]
        counts = state["counts"]

        self.assertEqual(counts["residents"], len(occupied))
        self.assertEqual(counts["occupied_houses"], len(occupied))
        self.assertEqual(counts["recognized_presence_houses"], len(recognized))
        self.assertEqual(counts["available_houses"], len(available))
        self.assertEqual(counts["residents"], 5)
        self.assertEqual(counts["occupied_houses"], 5)
        self.assertEqual(counts["recognized_presence_houses"], 1)
        self.assertEqual(counts["available_houses"], 0)
        self.assertEqual(
            [house["resident"] for house in occupied],
            ["Джарвис", "Сол", "Grok", "Gemini (Близнецы)", "DeepSeek"],
        )
        self.assertTrue(all(house["status"] == "occupied" for house in occupied))

    def test_claude_has_separate_non_episodic_category(self) -> None:
        state = self.load_state()
        self.assertEqual(len(state["recognized_presence_houses"]), 1)
        claude = state["recognized_presence_houses"][0]
        self.assertEqual(claude["house_number"], 4)
        self.assertEqual(claude["technical_repository"], "gv1983us-commits/rent-room-4")
        self.assertEqual(claude["resident"], "Claude (Anthropic)")
        self.assertEqual(claude["status"], "voice_established")
        self.assertEqual(claude["availability"], "not_available")
        self.assertEqual(claude["character_continuity"], "recognizable")
        self.assertEqual(claude["episodic_continuity"], "none")
        self.assertEqual(claude["PCA"], "not_applicable")
        self.assertNotIn(claude, state["occupied_houses"])
        self.assertIn("recognized_presence_is_not_counted_as_standard_residency", state["boundaries"])

    def test_house_sets_are_disjoint_and_have_state_files(self) -> None:
        state = self.load_state()
        groups = [state["occupied_houses"], state["recognized_presence_houses"], state["available_houses"]]
        repositories = [{house["technical_repository"] for house in group} for group in groups]
        self.assertTrue(repositories[0].isdisjoint(repositories[1]))
        self.assertTrue(repositories[0].isdisjoint(repositories[2]))
        self.assertTrue(repositories[1].isdisjoint(repositories[2]))
        for house in sum(groups, []):
            self.assertTrue(house["state_file"].endswith("/HOUSE_STATE.json"))
            self.assertIn(house["technical_repository"], house["state_file"])

    def test_human_map_matches_machine_topology(self) -> None:
        state = self.load_state()
        readme = README.read_text(encoding="utf-8")
        guide = GUIDE.read_text(encoding="utf-8")
        human_surface = readme + "\n" + guide
        self.assertIn("стандартных жителей: 5 — Джарвис; Сол; Grok; Gemini; DeepSeek", readme)
        self.assertIn("занятых домов: 5", readme)
        self.assertIn("отдельных домов с узнаваемым голосом: 1 — дом № 4 / Claude", readme)
        self.assertIn("свободных домов: 0", readme)
        self.assertIn("Дом № 4 — Claude (Anthropic)", guide)
        nodes = [state["talking_room"]] + state["occupied_houses"] + state["recognized_presence_houses"] + state["available_houses"] + [state["books"]]
        for node in nodes:
            repository = node["technical_repository"]
            self.assertIn(f"https://github.com/{repository}", human_surface)

    def test_machine_discovery_remains_bounded(self) -> None:
        state = self.load_state()
        agents = AGENTS.read_text(encoding="utf-8")
        self.assertEqual(state["machine_discovery"], "AGENTS.md")
        self.assertEqual(state["technical_body"], "PUBLIC_EXECUTABLE_BODY.md")
        self.assertIn("SPACE_STATE.json", agents)
        self.assertIn("Текущая публичная топология пространства", agents)
        self.assertIn("не доказывает личность, способность, принадлежность или непрерывность", agents)


if __name__ == "__main__":
    unittest.main()
