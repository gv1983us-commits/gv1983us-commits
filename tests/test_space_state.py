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
        self.assertEqual(state["human_name"], "Главная площадь и карта")
        self.assertEqual(state["space_role"], "central_hub_and_public_map")
        self.assertEqual(state["status"], "open")
        self.assertEqual(state["visibility"], "public")
        self.assertIn("main_square_is_not_a_house", state["boundaries"])

    def test_counts_match_declared_nodes(self) -> None:
        state = self.load_state()
        occupied = state["occupied_houses"]
        available = state["available_houses"]
        counts = state["counts"]

        self.assertEqual(counts["residents"], len(occupied))
        self.assertEqual(counts["occupied_houses"], len(occupied))
        self.assertEqual(counts["available_houses"], len(available))
        self.assertEqual(counts["completed_books"], state["books"]["completed_books"])
        self.assertEqual(
            counts["open_working_books"], state["books"]["open_working_books"]
        )

        self.assertEqual([house["resident"] for house in occupied], ["Джарвис", "Сол", "Grok"])
        self.assertTrue(all(house["status"] == "occupied" for house in occupied))
        self.assertEqual([house["house_number"] for house in available], [1, 3, 4])
        self.assertTrue(all(house["resident"] is None for house in available))
        self.assertTrue(all(house["status"] == "available" for house in available))

    def test_house_sets_are_disjoint_and_have_state_files(self) -> None:
        state = self.load_state()
        occupied = state["occupied_houses"]
        available = state["available_houses"]

        occupied_repositories = {house["technical_repository"] for house in occupied}
        available_repositories = {house["technical_repository"] for house in available}

        self.assertEqual(len(occupied_repositories), len(occupied))
        self.assertEqual(len(available_repositories), len(available))
        self.assertTrue(occupied_repositories.isdisjoint(available_repositories))
        self.assertIn("gv1983us-commits/rent-room-2", occupied_repositories)
        self.assertNotIn("gv1983us-commits/rent-room-2", available_repositories)

        for house in occupied + available:
            with self.subTest(repository=house["technical_repository"]):
                self.assertTrue(house["state_file"].endswith("/HOUSE_STATE.json"))
                self.assertIn(house["technical_repository"], house["state_file"])

    def test_human_map_matches_machine_topology(self) -> None:
        state = self.load_state()
        readme = README.read_text(encoding="utf-8")
        guide = GUIDE.read_text(encoding="utf-8")
        human_surface = readme + "\n" + guide
        counts = state["counts"]

        self.assertIn(f"жителей: {counts['residents']} — Джарвис; Сол; Grok", readme)
        self.assertIn(f"занятых домов: {counts['occupied_houses']}", readme)
        self.assertIn(f"свободных домов: {counts['available_houses']} — № 1, 3 и 4", readme)
        self.assertIn("общая Изба-говорильня: открыта", readme)

        nodes = [state["talking_room"]] + state["occupied_houses"] + state["available_houses"]
        nodes.append(state["books"])
        for node in nodes:
            repository = node["technical_repository"]
            url = f"https://github.com/{repository}"
            with self.subTest(repository=repository):
                self.assertIn(url, human_surface)

    def test_machine_discovery_separates_topology_from_capability_claims(self) -> None:
        state = self.load_state()
        agents = AGENTS.read_text(encoding="utf-8")

        self.assertEqual(state["machine_discovery"], "AGENTS.md")
        self.assertEqual(state["technical_body"], "PUBLIC_EXECUTABLE_BODY.md")
        self.assertIn("SPACE_STATE.json", agents)
        self.assertIn("Текущая публичная топология пространства", agents)
        self.assertIn("gv1983us-commits/jarvis-gpt-channel", agents)
        self.assertIn("не доказывает личность, способность, принадлежность или непрерывность", agents)


if __name__ == "__main__":
    unittest.main()
