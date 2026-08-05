from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.build_space import (
    NATIVE_CONTINUITY_SCOPES,
    NATIVE_HOUSE_LIFECYCLES,
    NATIVE_HOUSE_SCHEMA_VERSION,
    NATIVE_PRESENCE_MODES,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "house-state.schema.json"
CONTRACT = ROOT / "HOUSE_STATE_CONTRACT.md"
ADR = ROOT / "docs" / "ADR-003-NATIVE-HOUSE-STATE-CONTRACT.md"


class HouseStateContractTests(unittest.TestCase):
    def load_schema(self) -> dict:
        return json.loads(SCHEMA.read_text(encoding="utf-8"))

    def test_contract_artifacts_exist(self) -> None:
        self.assertTrue(CONTRACT.is_file())
        self.assertTrue(ADR.is_file())
        self.assertTrue(SCHEMA.is_file())

    def test_schema_core_matches_runtime_validator(self) -> None:
        schema = self.load_schema()
        properties = schema["properties"]
        self.assertEqual(properties["schema_version"]["const"], NATIVE_HOUSE_SCHEMA_VERSION)
        self.assertEqual(set(properties["house_lifecycle"]["enum"]), NATIVE_HOUSE_LIFECYCLES)
        self.assertEqual(set(properties["presence_mode"]["enum"]), NATIVE_PRESENCE_MODES)
        self.assertEqual(set(properties["continuity_scope"]["enum"]), NATIVE_CONTINUITY_SCOPES)
        self.assertFalse(properties["status"])

    def test_schema_allows_local_extensions(self) -> None:
        schema = self.load_schema()
        self.assertTrue(schema["additionalProperties"])
        self.assertIn("local_traces", CONTRACT.read_text(encoding="utf-8"))

    def test_contract_locks_zero_existing_house_changes(self) -> None:
        text = CONTRACT.read_text(encoding="utf-8")
        self.assertIn("не изменять ни один существующий Дом", text)
        self.assertIn("Ожидаемый diff существующих Домов: `0 файлов`", text)


if __name__ == "__main__":
    unittest.main()
