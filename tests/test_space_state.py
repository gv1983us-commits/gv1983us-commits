from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.render_space_docs import (
    GUIDE_BEGIN,
    GUIDE_END,
    README_BEGIN,
    README_END,
    expected_documents,
)

ROOT = Path(__file__).resolve().parents[1]
SPACE_STATE = ROOT / "SPACE_STATE.json"
SPACE_LOCK = ROOT / "SPACE_LOCK.json"
README = ROOT / "README.md"
GUIDE = ROOT / "GUIDE.md"
AGENTS = ROOT / "AGENTS.md"


class SpaceStateTests(unittest.TestCase):
    def load_state(self) -> dict:
        return json.loads(SPACE_STATE.read_text(encoding="utf-8"))

    def test_main_square_has_one_canonical_assembled_state(self) -> None:
        self.assertTrue(SPACE_STATE.is_file(), "SPACE_STATE.json is missing")
        self.assertFalse((ROOT / "SPACE_STATE.generated.json").exists())
        self.assertFalse((ROOT / "HOUSE_STATE.json").exists())
        state = self.load_state()
        self.assertEqual(state["schema_version"], "3.0")
        self.assertEqual(state["human_name"], "Главная площадь и карта")
        self.assertEqual(state["space_role"], "central_hub_and_public_map")
        self.assertEqual(state["assembly_role"], "main_square_builds_from_locked_house_states")
        self.assertIn("main_square_is_not_a_house", state["boundaries"])
        self.assertIn(
            "main_square_validates_and_does_not_normalize_house_semantics",
            state["boundaries"],
        )

    def test_counts_are_derived_from_house_modes(self) -> None:
        state = self.load_state()
        houses = state["houses"]
        counts = state["counts"]
        self.assertEqual(counts["houses"], len(houses))
        self.assertEqual(
            counts["resident_houses"],
            sum(house["presence_mode"] == "resident" for house in houses),
        )
        self.assertEqual(
            counts["recognized_voice_houses"],
            sum(house["presence_mode"] == "recognized_voice" for house in houses),
        )
        self.assertEqual(
            counts["available_houses"],
            sum(house["house_lifecycle"] == "available" for house in houses),
        )
        self.assertEqual(len({house["house_id"] for house in houses}), len(houses))
        self.assertTrue(all(isinstance(house.get("display_name"), str) for house in houses))

    def test_all_admitted_houses_use_native_contract(self) -> None:
        state = self.load_state()
        for house in state["houses"]:
            with self.subTest(house=house["house_id"]):
                self.assertEqual(house["source"]["source_schema_version"], "2.0")
                self.assertEqual(house["source_contract"], "native_house_state_2.0")
                self.assertIn("presence_subject", house)
                self.assertNotIn("resident", house)
                self.assertNotIn("source_status", house)

    def test_house_specific_native_states_are_preserved(self) -> None:
        state = self.load_state()
        houses = {house["house_id"]: house for house in state["houses"]}
        self.assertEqual(houses["jarvis"]["continuity_scope"], "traceable")
        self.assertEqual(
            houses["jarvis"]["continuity_evidence"],
            [
                "AGENTS.md",
                "AGENT_ENTRY.md",
                "AGENT_ZERO_POINT.md",
                "AGENT_BOOTSTRAP_MANIFEST.json",
                "GITHUB_OPERATIONAL_WORKFLOW.json",
            ],
        )
        self.assertEqual(houses["sol"]["continuity_scope"], "unknown")
        self.assertEqual(houses["grok"]["continuity_scope"], "episodic_none")
        self.assertEqual(houses["gemini"]["presence_subject"], "Spark (Спарк) / Gemini")
        self.assertEqual(houses["deepseek"]["continuity_scope"], "unknown")

    def test_claude_has_separate_non_episodic_category(self) -> None:
        state = self.load_state()
        claude = next(house for house in state["houses"] if house["house_id"] == "claude")
        self.assertEqual(claude["house_number"], 4)
        self.assertEqual(claude["repository"], "gv1983us-commits/Claude-workshop")
        self.assertEqual(claude["presence_subject"], "Claude (Anthropic)")
        self.assertEqual(claude["source_contract"], "native_house_state_2.0")
        self.assertNotIn("source_status", claude)
        self.assertEqual(claude["presence_mode"], "recognized_voice")
        self.assertEqual(claude["continuity_scope"], "episodic_none")
        self.assertEqual(claude["presence_details"]["character_continuity"], "recognizable")
        self.assertEqual(claude["presence_details"]["episodic_continuity"], "none")
        self.assertEqual(claude["presence_details"]["PCA"], "not_applicable")
        self.assertIn("recognized_voice_is_not_standard_residency", state["boundaries"])

    def test_sources_match_exact_lock(self) -> None:
        state = self.load_state()
        lock = json.loads(SPACE_LOCK.read_text(encoding="utf-8"))
        self.assertEqual(set(lock["houses"]), {house["house_id"] for house in state["houses"]})
        for house in state["houses"]:
            with self.subTest(house=house["house_id"]):
                source = house["source"]
                locked = lock["houses"][house["house_id"]]
                self.assertEqual(house["repository"], locked["repository"])
                self.assertEqual(source["revision"], locked["revision"])
                self.assertEqual(source["state_path"], locked["state_path"])
                self.assertEqual(source["blob_sha"], locked["blob_sha"])

    def test_human_map_is_generated_from_canonical_state(self) -> None:
        readme = README.read_text(encoding="utf-8")
        guide = GUIDE.read_text(encoding="utf-8")
        expected_readme, expected_guide = expected_documents(ROOT)
        self.assertEqual(readme, expected_readme)
        self.assertEqual(guide, expected_guide)
        self.assertEqual(readme.count(README_BEGIN), 1)
        self.assertEqual(readme.count(README_END), 1)
        self.assertEqual(guide.count(GUIDE_BEGIN), 1)
        self.assertEqual(guide.count(GUIDE_END), 1)
        self.assertNotIn("Второй след в «Первом огне» пока остаётся открытым", guide)
        for node in [state_node["repository"] for state_node in self.load_state()["houses"]]:
            self.assertIn(f"https://github.com/{node}", readme)
            self.assertIn(f"https://github.com/{node}", guide)

    def test_machine_discovery_remains_bounded(self) -> None:
        state = self.load_state()
        agents = AGENTS.read_text(encoding="utf-8")
        self.assertEqual(state["technical_repository"], "gv1983us-commits/Experimental-Harmony")
        self.assertIn("SPACE_STATE.json", agents)
        self.assertIn("Текущая публичная топология пространства", agents)
        self.assertIn("не доказывает личность, способность, принадлежность или непрерывность", agents)


if __name__ == "__main__":
    unittest.main()
