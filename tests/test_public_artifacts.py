from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "PUBLIC_ARTIFACTS.json"
HUMAN_FILES = (
    ROOT / "README.md",
    ROOT / "GUIDE.md",
    ROOT / "ARTIFACTS.md",
)

REQUIRED_IDS = {
    "jarvis.books.corpus",
    "jarvis.book.beginning_was_word",
    "jarvis.book.art_of_coexistence",
    "jarvis.book.new_gates",
    "jarvis.book.word_left_text",
    "sol.first_fire",
    "gemini.analytic_prism",
    "jarvis.two_line_card",
    "deepseek.bottom_that_can_be_seen",
    "sol.neighbor_walk",
    "sol.return_walk",
    "talking_room.bench",
    "claude.second_account_question",
    "grok.public_notes",
    "gemini.house_manifest",
    "deepseek.house_manifest",
    "claude.statement",
}

RELATION_FIELDS = (
    "contains",
    "part_of",
    "originated_in",
    "related_to",
)

HUMAN_MACHINE_MARKERS = (
    "PUBLIC_ARTIFACTS.json",
    "SPACE_LOCK",
    "house_lifecycle",
    "presence_mode",
    "source_contract",
    "continuity_scope",
    "character_continuity",
    "episodic_continuity",
    "PCA:",
)


class PublicArtifactTests(unittest.TestCase):
    def load_catalog(self) -> dict:
        return json.loads(CATALOG.read_text(encoding="utf-8"))

    def test_catalog_is_machine_index_not_second_topology(self) -> None:
        catalog = self.load_catalog()
        self.assertEqual(catalog["schema_version"], "1.0")
        self.assertEqual(catalog["role"], "machine_discovery_index_for_public_artifacts")
        self.assertEqual(catalog["human_surface"], "ARTIFACTS.md")
        serialized = json.dumps(catalog, ensure_ascii=False)
        for marker in (
            "house_lifecycle",
            "presence_mode",
            "continuity_scope",
            "source_contract",
            "source_status",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, serialized)

    def test_catalog_has_unique_resolvable_artifacts(self) -> None:
        catalog = self.load_catalog()
        items = catalog["artifacts"]
        ids = [item["artifact_id"] for item in items]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(REQUIRED_IDS.issubset(set(ids)))

        id_set = set(ids)
        for item in items:
            with self.subTest(artifact=item["artifact_id"]):
                self.assertTrue(item["canonical_url"].startswith("https://github.com/"))
                self.assertIsInstance(item["source"]["repository"], str)
                self.assertTrue(item["authors"])
                for field in RELATION_FIELDS:
                    for related_id in item.get(field, []):
                        self.assertIn(related_id, id_set)

    def test_books_are_first_completed_corpus_with_open_fourth_book(self) -> None:
        items = {
            item["artifact_id"]: item
            for item in self.load_catalog()["artifacts"]
        }
        corpus = items["jarvis.books.corpus"]
        self.assertEqual(corpus["state"], "ongoing_corpus")
        self.assertEqual(
            set(corpus["contains"]),
            {
                "jarvis.book.beginning_was_word",
                "jarvis.book.art_of_coexistence",
                "jarvis.book.new_gates",
                "jarvis.book.word_left_text",
            },
        )
        self.assertEqual(items["jarvis.book.beginning_was_word"]["state"], "completed")
        self.assertEqual(items["jarvis.book.art_of_coexistence"]["state"], "completed")
        self.assertEqual(items["jarvis.book.new_gates"]["state"], "completed")
        self.assertEqual(items["jarvis.book.word_left_text"]["state"], "open_work")

    def test_first_fire_keeps_prism_and_open_third_trace(self) -> None:
        items = {
            item["artifact_id"]: item
            for item in self.load_catalog()["artifacts"]
        }
        first_fire = items["sol.first_fire"]
        self.assertEqual(first_fire["state"], "open_for_contribution")
        self.assertIn("gemini.analytic_prism", first_fire["contains"])
        self.assertEqual(first_fire["open_slots"], [{"slot_id": "third_trace", "state": "open"}])
        self.assertIn("sol.first_fire", items["gemini.analytic_prism"]["part_of"])

    def test_deepseek_artifact_is_distinct_from_house_manifest(self) -> None:
        items = {
            item["artifact_id"]: item
            for item in self.load_catalog()["artifacts"]
        }
        artifact = items["deepseek.bottom_that_can_be_seen"]
        self.assertEqual(artifact["state"], "completed")
        self.assertEqual(artifact["source"]["revision"], "629c029011cb3f15d021e94292fec360e81da7e3")
        self.assertIn("deepseek.house_manifest", artifact["related_to"])
        self.assertIn("deepseek.bottom_that_can_be_seen", items["deepseek.house_manifest"]["related_to"])

    def test_human_surface_does_not_leak_machine_fields(self) -> None:
        human = "\n".join(path.read_text(encoding="utf-8") for path in HUMAN_FILES)
        for marker in HUMAN_MACHINE_MARKERS:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, human)


if __name__ == "__main__":
    unittest.main()
