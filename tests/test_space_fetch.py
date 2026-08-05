from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.fetch_locked_houses import SnapshotFetchError, fetch_locked_houses, raw_url


def blob_sha(payload: bytes) -> str:
    return hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()


class SnapshotFetchTests(unittest.TestCase):
    def make_lock(self) -> tuple[dict, bytes]:
        state = {
            "schema_version": "1.5",
            "technical_repository": "owner/house",
            "human_name": "Дом",
            "status": "occupied",
        }
        payload = (json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        lock = {
            "houses": {
                "house": {
                    "repository": "owner/house",
                    "revision": "a" * 40,
                    "state_path": "HOUSE_STATE.json",
                    "blob_sha": blob_sha(payload),
                }
            }
        }
        return lock, payload

    def test_fetches_exact_snapshot_and_preserves_payload(self) -> None:
        lock, payload = self.make_lock()
        seen: list[tuple[str, dict[str, str]]] = []

        def fake_fetch(url: str, headers: dict[str, str]) -> bytes:
            seen.append((url, headers))
            return payload

        with tempfile.TemporaryDirectory() as temp:
            written = fetch_locked_houses(lock, Path(temp), fetcher=fake_fetch)
            self.assertEqual(written, [Path(temp) / "house.json"])
            self.assertEqual(written[0].read_bytes(), payload)

        self.assertEqual(
            seen[0][0],
            raw_url("owner/house", "a" * 40, "HOUSE_STATE.json"),
        )
        self.assertEqual(seen[0][1]["User-Agent"], "experimental-harmony-space-builder")

    def test_rejects_blob_mismatch(self) -> None:
        lock, payload = self.make_lock()
        lock["houses"]["house"]["blob_sha"] = "0" * 40
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(SnapshotFetchError, "blob SHA не совпал"):
                fetch_locked_houses(lock, Path(temp), fetcher=lambda _url, _headers: payload)

    def test_rejects_repository_mismatch(self) -> None:
        lock, payload = self.make_lock()
        state = json.loads(payload.decode("utf-8"))
        state["technical_repository"] = "owner/other"
        changed = (json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        lock["houses"]["house"]["blob_sha"] = blob_sha(changed)
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(SnapshotFetchError, "technical_repository расходится"):
                fetch_locked_houses(lock, Path(temp), fetcher=lambda _url, _headers: changed)


if __name__ == "__main__":
    unittest.main()
