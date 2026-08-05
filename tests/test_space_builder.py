from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_space import SpaceBuildError, build_space


def blob_sha(payload: bytes) -> str:
    return hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()


class SpaceBuilderTests(unittest.TestCase):
    def make_inputs(self, root: Path) -> tuple[dict, dict, Path]:
        source_dir = root / "houses"
        source_dir.mkdir()
        states = {
            "alpha": {
                "schema_version": "1.3",
                "technical_repository": "owner/alpha",
                "human_name": "Дом Альфа",
                "resident": "Альфа",
                "status": "occupied",
                "visibility": "public",
                "external_routes": {"beta": "https://example.invalid/beta"},
            },
            "beta": {
                "schema_version": "1.2",
                "technical_repository": "owner/beta",
                "public_label": "Дом Бета",
                "house_number": 4,
                "resident": "Бета",
                "status": "voice_established",
                "visibility": "public",
                "external_routes": {"alpha": "https://example.invalid/alpha"},
            },
        }
        registry = {
            "schema_version": "1.0",
            "project": "Тест",
            "cycle": "Тестовый цикл",
            "houses": [],
            "shared_nodes": {"main_square": "owner/square"},
        }
        lock = {"schema_version": "1.0", "houses": {}}
        for house_id, state in states.items():
            payload = (json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            (source_dir / f"{house_id}.json").write_bytes(payload)
            repository = state["technical_repository"]
            registry["houses"].append(
                {"house_id": house_id, "repository": repository, "state_path": "HOUSE_STATE.json"}
            )
            lock["houses"][house_id] = {
                "repository": repository,
                "revision": ("a" if house_id == "alpha" else "b") * 40,
                "state_path": "HOUSE_STATE.json",
                "blob_sha": blob_sha(payload),
            }
        return registry, lock, source_dir

    def test_builds_map_without_copying_neighbor_catalogs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry, lock, source_dir = self.make_inputs(Path(temp))
            result = build_space(registry, lock, source_dir)

        self.assertEqual(result["counts"]["houses"], 2)
        self.assertEqual(result["counts"]["resident_houses"], 1)
        self.assertEqual(result["counts"]["recognized_voice_houses"], 1)
        self.assertEqual(result["counts"]["legacy_neighbor_catalogs"], 2)
        self.assertNotIn("external_routes", result["houses"][0])
        beta = next(house for house in result["houses"] if house["house_id"] == "beta")
        self.assertEqual(beta["presence_mode"], "recognized_voice")
        self.assertEqual(beta["continuity_scope"], "episodic_none")

    def test_rejects_duplicate_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry, lock, source_dir = self.make_inputs(Path(temp))
            registry["houses"][1]["repository"] = registry["houses"][0]["repository"]
            with self.assertRaisesRegex(SpaceBuildError, "повтор repository"):
                build_space(registry, lock, source_dir)

    def test_rejects_blob_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry, lock, source_dir = self.make_inputs(Path(temp))
            lock["houses"]["alpha"]["blob_sha"] = "0" * 40
            with self.assertRaisesRegex(SpaceBuildError, "blob SHA не совпал"):
                build_space(registry, lock, source_dir)

    def test_rejects_registry_lock_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry, lock, source_dir = self.make_inputs(Path(temp))
            del lock["houses"]["beta"]
            with self.assertRaisesRegex(SpaceBuildError, "в lock отсутствует"):
                build_space(registry, lock, source_dir)


if __name__ == "__main__":
    unittest.main()
