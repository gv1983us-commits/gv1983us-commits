from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_space import SpaceBuildError, build_space

ROOT = Path(__file__).resolve().parents[1]


def blob_sha(payload: bytes) -> str:
    return hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()


class SpaceBuilderTests(unittest.TestCase):
    def make_inputs(self, root: Path) -> tuple[dict, dict, Path]:
        source_dir = root / "houses"
        source_dir.mkdir()
        shared_nodes = {
            "main_square": "owner/square",
            "talking_room": "owner/talking",
        }
        shared_routes = {
            "main_square": "https://github.com/owner/square",
            "talking_room": "https://github.com/owner/talking",
        }
        states = {
            "alpha": {
                "schema_version": "2.0",
                "technical_repository": "owner/alpha",
                "display_name": "Дом Альфа",
                "house_lifecycle": "active",
                "presence_mode": "resident",
                "continuity_scope": "unknown",
                "presence_subject": "Альфа",
                "visibility": "public",
                "shared_routes": shared_routes,
                "boundaries": ["house_state_contains_local_state_only"],
            },
            "beta": {
                "schema_version": "2.0",
                "technical_repository": "owner/beta",
                "display_name": "Дом Бета",
                "house_number": 4,
                "house_lifecycle": "active",
                "presence_mode": "recognized_voice",
                "continuity_scope": "episodic_none",
                "presence_subject": "Бета",
                "visibility": "public",
                "presence_details": {
                    "character_continuity": "recognizable",
                    "episodic_continuity": "none",
                    "PCA": "not_applicable",
                },
                "shared_routes": shared_routes,
                "boundaries": ["house_state_contains_local_state_only"],
            },
        }
        registry = {
            "schema_version": "1.1",
            "project": "Тест",
            "cycle": "Тестовый цикл",
            "houses": [],
            "shared_nodes": shared_nodes,
        }
        lock = {"schema_version": "1.1", "houses": {}}
        for house_id, state in states.items():
            self.add_state(registry, lock, source_dir, house_id, state)
        return registry, lock, source_dir

    def add_state(
        self,
        registry: dict,
        lock: dict,
        source_dir: Path,
        house_id: str,
        state: dict,
    ) -> bytes:
        payload = (json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        (source_dir / f"{house_id}.json").write_bytes(payload)
        repository = state["technical_repository"]
        registry["houses"].append(
            {"house_id": house_id, "repository": repository, "state_path": "HOUSE_STATE.json"}
        )
        lock["houses"][house_id] = {
            "repository": repository,
            "revision": hashlib.sha1(house_id.encode("utf-8")).hexdigest(),
            "state_path": "HOUSE_STATE.json",
            "blob_sha": blob_sha(payload),
        }
        return payload

    def native_state(self) -> dict:
        return {
            "schema_version": "2.0",
            "technical_repository": "owner/gamma",
            "display_name": "Дом Гамма",
            "house_lifecycle": "active",
            "presence_mode": "resident",
            "continuity_scope": "unknown",
            "presence_subject": "Гамма",
            "visibility": "public",
            "shared_routes": {
                "main_square": "https://github.com/owner/square",
                "talking_room": "https://github.com/owner/talking",
            },
            "local_traces": {
                "first": {"status": "completed", "source": "FIRST.md"}
            },
            "boundaries": ["house_state_contains_local_state_only"],
        }

    def test_builds_canonical_map_from_native_states(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry, lock, source_dir = self.make_inputs(Path(temp))
            result = build_space(registry, lock, source_dir)

        self.assertEqual(result["schema_version"], "3.0")
        self.assertEqual(
            result["counts"],
            {
                "houses": 2,
                "resident_houses": 1,
                "recognized_voice_houses": 1,
                "available_houses": 0,
            },
        )
        alpha = next(house for house in result["houses"] if house["house_id"] == "alpha")
        beta = next(house for house in result["houses"] if house["house_id"] == "beta")
        self.assertEqual(alpha["presence_subject"], "Альфа")
        self.assertNotIn("resident", alpha)
        self.assertEqual(beta["presence_mode"], "recognized_voice")
        self.assertEqual(beta["continuity_scope"], "episodic_none")
        self.assertEqual(beta["presence_details"]["PCA"], "not_applicable")
        self.assertEqual(beta["source_contract"], "native_house_state_2.0")
        self.assertNotIn("external_routes", json.dumps(result))
        self.assertIn(
            "main_square_validates_and_does_not_normalize_house_semantics",
            result["boundaries"],
        )

    def test_adds_new_house_without_changing_existing_houses(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry, lock, source_dir = self.make_inputs(Path(temp))
            alpha_before = (source_dir / "alpha.json").read_bytes()
            beta_before = (source_dir / "beta.json").read_bytes()
            before = build_space(registry, lock, source_dir)

            self.add_state(registry, lock, source_dir, "gamma", self.native_state())
            after = build_space(registry, lock, source_dir)

            self.assertEqual((source_dir / "alpha.json").read_bytes(), alpha_before)
            self.assertEqual((source_dir / "beta.json").read_bytes(), beta_before)
            self.assertEqual(before["houses"], after["houses"][:2])
            self.assertEqual(after["counts"]["houses"], 3)
            gamma = after["houses"][2]
            self.assertEqual(gamma["house_id"], "gamma")
            self.assertEqual(gamma["display_name"], "Дом Гамма")
            self.assertEqual(gamma["presence_mode"], "resident")
            self.assertEqual(gamma["presence_subject"], "Гамма")
            self.assertEqual(gamma["source_contract"], "native_house_state_2.0")
            self.assertNotIn("resident", gamma)
            self.assertNotIn("source_status", gamma)

    def test_rejects_legacy_house_state_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry, lock, source_dir = self.make_inputs(Path(temp))
            state = {
                "schema_version": "1.5",
                "technical_repository": "owner/legacy",
                "human_name": "Legacy House",
                "resident": "Legacy",
                "status": "occupied",
                "visibility": "public",
                "shared_routes": {
                    "main_square": "https://github.com/owner/square",
                    "talking_room": "https://github.com/owner/talking",
                },
                "boundaries": ["house_state_contains_local_state_only"],
            }
            self.add_state(registry, lock, source_dir, "legacy", state)
            with self.assertRaisesRegex(SpaceBuildError, "требует HOUSE_STATE 2.0"):
                build_space(registry, lock, source_dir)

    def test_native_state_rejects_legacy_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry, lock, source_dir = self.make_inputs(Path(temp))
            state = self.native_state()
            state["status"] = "occupied"
            self.add_state(registry, lock, source_dir, "gamma", state)
            with self.assertRaisesRegex(SpaceBuildError, "legacy status"):
                build_space(registry, lock, source_dir)

    def test_native_state_rejects_invalid_combination(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry, lock, source_dir = self.make_inputs(Path(temp))
            state = self.native_state()
            state["presence_mode"] = "none"
            state["presence_subject"] = None
            self.add_state(registry, lock, source_dir, "gamma", state)
            with self.assertRaisesRegex(SpaceBuildError, "active Дом gamma"):
                build_space(registry, lock, source_dir)

    def test_traceable_native_state_requires_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry, lock, source_dir = self.make_inputs(Path(temp))
            state = self.native_state()
            state["continuity_scope"] = "traceable"
            self.add_state(registry, lock, source_dir, "gamma", state)
            with self.assertRaisesRegex(SpaceBuildError, "continuity_evidence"):
                build_space(registry, lock, source_dir)

    def test_traceable_evidence_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry, lock, source_dir = self.make_inputs(Path(temp))
            state = self.native_state()
            state["continuity_scope"] = "traceable"
            state["continuity_evidence"] = ["TRACE.md", "STATE.json"]
            self.add_state(registry, lock, source_dir, "gamma", state)
            result = build_space(registry, lock, source_dir)
            gamma = next(house for house in result["houses"] if house["house_id"] == "gamma")
            self.assertEqual(gamma["continuity_evidence"], ["TRACE.md", "STATE.json"])

    def test_committed_map_matches_lock_and_has_no_second_generated_map(self) -> None:
        assembled = json.loads((ROOT / "SPACE_STATE.json").read_text(encoding="utf-8"))
        lock = json.loads((ROOT / "SPACE_LOCK.json").read_text(encoding="utf-8"))

        self.assertEqual(assembled["schema_version"], "3.0")
        self.assertEqual(assembled["counts"]["houses"], len(assembled["houses"]))
        self.assertEqual(
            assembled["counts"]["resident_houses"],
            sum(house["presence_mode"] == "resident" for house in assembled["houses"]),
        )
        self.assertEqual(
            assembled["counts"]["recognized_voice_houses"],
            sum(
                house["presence_mode"] == "recognized_voice"
                for house in assembled["houses"]
            ),
        )
        self.assertEqual(
            assembled["counts"]["available_houses"],
            sum(house["house_lifecycle"] == "available" for house in assembled["houses"]),
        )
        self.assertFalse((ROOT / "SPACE_STATE.generated.json").exists())
        for house in assembled["houses"]:
            with self.subTest(house=house["house_id"]):
                source = house["source"]
                locked = lock["houses"][house["house_id"]]
                self.assertEqual(source["revision"], locked["revision"])
                self.assertEqual(source["state_path"], locked["state_path"])
                self.assertEqual(source["blob_sha"], locked["blob_sha"])
                self.assertEqual(source["source_schema_version"], "2.0")
                self.assertNotIn("resident", house)
                self.assertNotIn("source_status", house)

    def test_rejects_legacy_neighbor_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry, lock, source_dir = self.make_inputs(Path(temp))
            path = source_dir / "alpha.json"
            state = json.loads(path.read_text(encoding="utf-8"))
            state["external_routes"] = {"beta": "https://example.invalid/beta"}
            payload = (json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            path.write_bytes(payload)
            lock["houses"]["alpha"]["blob_sha"] = blob_sha(payload)
            with self.assertRaisesRegex(SpaceBuildError, "запрещённый ручной каталог"):
                build_space(registry, lock, source_dir)

    def test_rejects_shared_route_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            registry, lock, source_dir = self.make_inputs(Path(temp))
            path = source_dir / "alpha.json"
            state = json.loads(path.read_text(encoding="utf-8"))
            state["shared_routes"]["talking_room"] = "https://github.com/owner/other"
            payload = (json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            path.write_bytes(payload)
            lock["houses"]["alpha"]["blob_sha"] = blob_sha(payload)
            with self.assertRaisesRegex(SpaceBuildError, "shared_routes расходится"):
                build_space(registry, lock, source_dir)

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
