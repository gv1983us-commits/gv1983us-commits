from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "sync_space.py"
SPEC = importlib.util.spec_from_file_location("sync_space", MODULE_PATH)
assert SPEC and SPEC.loader
sync_space = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync_space)


def state_payload(repository: str) -> bytes:
    return (
        json.dumps(
            {
                "schema_version": "1.5",
                "technical_repository": repository,
                "human_name": "Тестовый дом",
                "resident": "Тестовый голос",
                "status": "occupied",
                "visibility": "public",
                "shared_routes": {
                    "main_square": "https://github.com/example/square",
                    "talking_room": "https://github.com/example/talk",
                },
                "boundaries": ["house_state_contains_local_state_only"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")


def native_state_payload(repository: str) -> bytes:
    return (
        json.dumps(
            {
                "schema_version": "2.0",
                "technical_repository": repository,
                "display_name": "Нативный тестовый дом",
                "house_lifecycle": "active",
                "presence_mode": "resident",
                "continuity_scope": "unknown",
                "presence_subject": "Нативный голос",
                "visibility": "public",
                "shared_routes": {
                    "main_square": "https://github.com/example/square",
                    "talking_room": "https://github.com/example/talk",
                },
                "local_traces": {"first": {"status": "completed"}},
                "boundaries": ["house_state_contains_local_state_only"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")


def write_root(root: Path) -> None:
    registry = {
        "schema_version": "1.1",
        "project": "Тест",
        "cycle": "Цикл",
        "houses": [
            {
                "house_id": "one",
                "repository": "example/house",
                "state_path": "HOUSE_STATE.json",
                "tracking_ref": "main",
            }
        ],
        "shared_nodes": {
            "main_square": "example/square",
            "talking_room": "example/talk",
            "books": "example/books",
        },
    }
    (root / "SPACE_REGISTRY.json").write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (root / "SPACE_LOCK.json").write_text("OLD LOCK\n", encoding="utf-8")
    (root / "SPACE_STATE.json").write_text("OLD STATE\n", encoding="utf-8")
    (root / "README.md").write_text(
        "до\n<!-- BEGIN GENERATED SPACE SUMMARY -->\nстарое\n"
        "<!-- END GENERATED SPACE SUMMARY -->\nпосле\n",
        encoding="utf-8",
    )
    (root / "GUIDE.md").write_text(
        "до\n<!-- BEGIN GENERATED SPACE MAP -->\nстарое\n"
        "<!-- END GENERATED SPACE MAP -->\nпосле\n",
        encoding="utf-8",
    )


class SpaceSyncTests(unittest.TestCase):
    revision = "1" * 40

    def resolver(self, repository: str, tracking_ref: str, _headers: dict[str, str]) -> str:
        self.assertEqual(repository, "example/house")
        self.assertEqual(tracking_ref, "main")
        return self.revision

    def fetcher(self, url: str, _headers: dict[str, str]) -> bytes:
        self.assertIn(self.revision, url)
        return state_payload("example/house")

    def test_prepare_outputs_resolves_ref_and_builds_all_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            write_root(root)
            registry = sync_space.load_registry(root / "SPACE_REGISTRY.json")
            outputs = sync_space.prepare_outputs(
                registry,
                root,
                resolver=self.resolver,
                fetcher=self.fetcher,
                recorded_at="2026-08-05T19:34:00+03:00",
            )

            self.assertEqual(
                set(outputs),
                {"SPACE_LOCK.json", "SPACE_STATE.json", "README.md", "GUIDE.md"},
            )
            lock = json.loads(outputs["SPACE_LOCK.json"])
            entry = lock["houses"]["one"]
            self.assertEqual(entry["tracking_ref"], "main")
            self.assertEqual(entry["revision"], self.revision)
            self.assertEqual(
                entry["blob_sha"],
                sync_space.git_blob_sha(state_payload("example/house")),
            )
            state = json.loads(outputs["SPACE_STATE.json"])
            self.assertEqual(state["counts"]["houses"], 1)
            self.assertIn("Тестовый дом".encode("utf-8"), outputs["README.md"])
            self.assertIn(b"example/house", outputs["GUIDE.md"])

    def test_prepare_outputs_accepts_native_house_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            write_root(root)
            registry = sync_space.load_registry(root / "SPACE_REGISTRY.json")

            def native_fetcher(url: str, _headers: dict[str, str]) -> bytes:
                self.assertIn(self.revision, url)
                return native_state_payload("example/house")

            outputs = sync_space.prepare_outputs(
                registry,
                root,
                resolver=self.resolver,
                fetcher=native_fetcher,
                recorded_at="2026-08-05T19:35:00+03:00",
            )
            state = json.loads(outputs["SPACE_STATE.json"])
            house = state["houses"][0]
            self.assertEqual(house["display_name"], "Нативный тестовый дом")
            self.assertEqual(house["resident"], "Нативный голос")
            self.assertEqual(house["source_contract"], "native_house_state_2.0")
            self.assertNotIn("source_status", house)
            self.assertIn("Нативный тестовый дом".encode("utf-8"), outputs["README.md"])
            self.assertIn("Нативный голос".encode("utf-8"), outputs["GUIDE.md"])

    def test_failed_preparation_changes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            write_root(root)
            before = {
                name: (root / name).read_bytes()
                for name in ("SPACE_LOCK.json", "SPACE_STATE.json", "README.md", "GUIDE.md")
            }

            def broken_fetcher(_url: str, _headers: dict[str, str]) -> bytes:
                raise sync_space.SpaceSyncError("network failed")

            with self.assertRaises(sync_space.SpaceSyncError):
                sync_space.sync_space(
                    root,
                    resolver=self.resolver,
                    fetcher=broken_fetcher,
                    recorded_at="2026-08-05T19:34:00+03:00",
                )

            after = {name: (root / name).read_bytes() for name in before}
            self.assertEqual(after, before)

    def test_failed_publish_rolls_back_all_replaced_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            write_root(root)
            names = ("SPACE_LOCK.json", "SPACE_STATE.json", "README.md", "GUIDE.md")
            before = {name: (root / name).read_bytes() for name in names}
            outputs = {name: f"NEW {name}\n".encode("utf-8") for name in names}
            forward_calls = 0

            def flaky_replace(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
                nonlocal forward_calls
                source = Path(src)
                if source.parent.name == "staged":
                    forward_calls += 1
                    if forward_calls == 2:
                        raise OSError("simulated publish failure")
                os.replace(src, dst)

            with self.assertRaisesRegex(
                sync_space.SpaceSyncError,
                "прежнее состояние восстановлено",
            ):
                sync_space.publish_outputs(outputs, root, replacer=flaky_replace)

            after = {name: (root / name).read_bytes() for name in names}
            self.assertEqual(after, before)

    def test_registry_requires_explicit_tracking_ref(self) -> None:
        item = {
            "house_id": "one",
            "repository": "example/house",
            "state_path": "HOUSE_STATE.json",
        }
        with self.assertRaisesRegex(sync_space.SpaceSyncError, "tracking_ref"):
            sync_space.validate_registry_house(item)

    def test_committed_registry_and_lock_share_tracking_refs(self) -> None:
        registry = json.loads((ROOT / "SPACE_REGISTRY.json").read_text(encoding="utf-8"))
        lock = json.loads((ROOT / "SPACE_LOCK.json").read_text(encoding="utf-8"))
        for item in registry["houses"]:
            self.assertEqual(
                lock["houses"][item["house_id"]]["tracking_ref"],
                item["tracking_ref"],
            )


if __name__ == "__main__":
    unittest.main()
