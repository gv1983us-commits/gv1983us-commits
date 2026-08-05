from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HEX40 = re.compile(r"^[0-9a-f]{40}$")


class SpaceBuildError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SpaceBuildError(f"не удалось прочитать {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SpaceBuildError(f"корень {path} должен быть объектом")
    return value


def git_blob_sha(payload: bytes) -> str:
    return hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()


def validate_sources(registry: dict[str, Any], lock: dict[str, Any]) -> list[tuple[str, dict[str, str]]]:
    houses = registry.get("houses")
    locked = lock.get("houses")
    if not isinstance(houses, list) or not houses:
        raise SpaceBuildError("SPACE_REGISTRY.houses должен быть непустым массивом")
    if not isinstance(locked, dict):
        raise SpaceBuildError("SPACE_LOCK.houses должен быть объектом")

    seen_ids: set[str] = set()
    seen_repositories: set[str] = set()
    result: list[tuple[str, dict[str, str]]] = []
    for item in houses:
        if not isinstance(item, dict):
            raise SpaceBuildError("каждая запись registry должна быть объектом")
        house_id = item.get("house_id")
        repository = item.get("repository")
        state_path = item.get("state_path")
        if not all(isinstance(value, str) and value for value in (house_id, repository, state_path)):
            raise SpaceBuildError("registry требует house_id, repository и state_path")
        if house_id in seen_ids:
            raise SpaceBuildError(f"повтор house_id: {house_id}")
        if repository in seen_repositories:
            raise SpaceBuildError(f"повтор repository: {repository}")
        seen_ids.add(house_id)
        seen_repositories.add(repository)

        entry = locked.get(house_id)
        if not isinstance(entry, dict):
            raise SpaceBuildError(f"в lock отсутствует {house_id}")
        for field in ("repository", "revision", "state_path", "blob_sha"):
            if not isinstance(entry.get(field), str) or not entry[field]:
                raise SpaceBuildError(f"lock {house_id}.{field} отсутствует")
        if entry["repository"] != repository or entry["state_path"] != state_path:
            raise SpaceBuildError(f"registry/lock расходятся для {house_id}")
        if not HEX40.fullmatch(entry["revision"]) or not HEX40.fullmatch(entry["blob_sha"]):
            raise SpaceBuildError(f"lock {house_id} требует точные 40-символьные SHA")
        result.append((house_id, entry))

    expected_ids = {house_id for house_id, _ in result}
    if set(locked) != expected_ids:
        raise SpaceBuildError("registry/lock содержат разные наборы домов")
    return result


def load_locked_house(source_dir: Path, house_id: str, lock_entry: dict[str, str]) -> dict[str, Any]:
    path = source_dir / f"{house_id}.json"
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise SpaceBuildError(f"не удалось прочитать snapshot {path}: {exc}") from exc
    actual = git_blob_sha(payload)
    if actual != lock_entry["blob_sha"]:
        raise SpaceBuildError(
            f"blob SHA не совпал для {house_id}: expected={lock_entry['blob_sha']} actual={actual}"
        )
    try:
        state = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SpaceBuildError(f"snapshot {house_id} не является UTF-8 JSON") from exc
    if not isinstance(state, dict) or state.get("technical_repository") != lock_entry["repository"]:
        raise SpaceBuildError(f"technical_repository расходится для {house_id}")
    return state


def expected_shared_routes(registry: dict[str, Any]) -> dict[str, str]:
    shared = registry.get("shared_nodes")
    if not isinstance(shared, dict):
        raise SpaceBuildError("SPACE_REGISTRY.shared_nodes должен быть объектом")
    square = shared.get("main_square")
    talking = shared.get("talking_room")
    if not all(isinstance(value, str) and value for value in (square, talking)):
        raise SpaceBuildError("registry требует main_square и talking_room")
    return {
        "main_square": f"https://github.com/{square}",
        "talking_room": f"https://github.com/{talking}",
    }


def validate_local_house(
    house_id: str,
    state: dict[str, Any],
    shared_routes: dict[str, str],
) -> None:
    if "external_routes" in state:
        raise SpaceBuildError(f"{house_id} содержит запрещённый ручной каталог external_routes")
    actual_routes = state.get("shared_routes")
    if actual_routes != shared_routes:
        raise SpaceBuildError(f"{house_id}.shared_routes расходится с registry")
    boundaries = state.get("boundaries")
    if not isinstance(boundaries, list) or "house_state_contains_local_state_only" not in boundaries:
        raise SpaceBuildError(f"{house_id} не объявляет локальную границу HOUSE_STATE")


def normalize_house(house_id: str, state: dict[str, Any], lock_entry: dict[str, str]) -> dict[str, Any]:
    status = state.get("status")
    modes = {
        "occupied": ("active", "resident", "unknown"),
        "voice_established": ("active", "recognized_voice", "episodic_none"),
        "available": ("available", "none", "not_applicable"),
        "reserved": ("reserved", "none", "unknown"),
    }
    if status not in modes:
        raise SpaceBuildError(f"неизвестный status у {house_id}: {status!r}")
    lifecycle, presence_mode, continuity_scope = modes[status]
    display_name = state.get("human_name") or state.get("public_label")
    if not isinstance(display_name, str) or not display_name:
        raise SpaceBuildError(f"у {house_id} отсутствует human_name/public_label")

    house: dict[str, Any] = {
        "house_id": house_id,
        "display_name": display_name,
        "repository": lock_entry["repository"],
        "source": {
            "revision": lock_entry["revision"],
            "state_path": lock_entry["state_path"],
            "blob_sha": lock_entry["blob_sha"],
            "source_schema_version": state.get("schema_version"),
        },
        "house_lifecycle": lifecycle,
        "presence_mode": presence_mode,
        "continuity_scope": continuity_scope,
        "resident": state.get("resident"),
        "visibility": state.get("visibility"),
        "source_status": status,
    }
    presence = state.get("presence")
    if isinstance(presence, dict):
        details = {
            key: presence[key]
            for key in (
                "mode",
                "continuity_scope",
                "character_continuity",
                "episodic_continuity",
                "PCA",
            )
            if key in presence
        }
        if details:
            house["presence_details"] = details
    if isinstance(state.get("house_number"), int):
        house["house_number"] = state["house_number"]
    former_name = state.get("former_name") or state.get("former_public_address")
    if isinstance(former_name, str) and former_name:
        house["former_name"] = former_name
    return house


def build_space(registry: dict[str, Any], lock: dict[str, Any], source_dir: Path) -> dict[str, Any]:
    routes = expected_shared_routes(registry)
    houses: list[dict[str, Any]] = []
    for house_id, entry in validate_sources(registry, lock):
        state = load_locked_house(source_dir, house_id, entry)
        validate_local_house(house_id, state, routes)
        houses.append(normalize_house(house_id, state, entry))

    numbers = [house["house_number"] for house in houses if "house_number" in house]
    if len(numbers) != len(set(numbers)):
        raise SpaceBuildError("номера домов должны быть уникальны")
    return {
        "schema_version": "2.0",
        "project": registry.get("project"),
        "cycle": registry.get("cycle"),
        "technical_repository": registry["shared_nodes"]["main_square"],
        "human_name": "Главная площадь и карта",
        "space_role": "central_hub_and_public_map",
        "status": "open",
        "visibility": "public",
        "assembly_role": "main_square_builds_from_locked_house_states",
        "counts": {
            "houses": len(houses),
            "resident_houses": sum(house["presence_mode"] == "resident" for house in houses),
            "recognized_voice_houses": sum(
                house["presence_mode"] == "recognized_voice" for house in houses
            ),
            "available_houses": sum(house["house_lifecycle"] == "available" for house in houses),
        },
        "houses": houses,
        "shared_nodes": registry.get("shared_nodes", {}),
        "boundaries": [
            "main_square_is_not_a_house",
            "house_owns_its_local_state",
            "main_square_owns_the_assembled_map",
            "recognized_voice_is_not_standard_residency",
            "recognized_voice_is_not_episodic_memory",
            "topology_does_not_grant_repository_access",
            "public_route_does_not_guarantee_delivery_or_response",
            "authorship_is_preserved",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Собрать площадь из locked HOUSE_STATE snapshots")
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=ROOT / "SPACE_REGISTRY.json")
    parser.add_argument("--lock", dest="lock_path", type=Path, default=ROOT / "SPACE_LOCK.json")
    parser.add_argument("--output", type=Path, default=ROOT / "SPACE_STATE.json")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        rendered = json.dumps(
            build_space(load_json(args.registry), load_json(args.lock_path), args.source_dir),
            ensure_ascii=False,
            indent=2,
        ) + "\n"
        if args.check:
            if not args.output.is_file() or args.output.read_text(encoding="utf-8") != rendered:
                raise SpaceBuildError(f"собранная карта расходится с {args.output}")
            print("КАРТА ПРОЙДЕНА")
        else:
            args.output.write_text(rendered, encoding="utf-8")
            print(f"КАРТА СОБРАНА: {args.output}")
        return 0
    except (OSError, SpaceBuildError) as exc:
        print(f"СБОРКА КАРТЫ НЕ ПРОЙДЕНА: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
