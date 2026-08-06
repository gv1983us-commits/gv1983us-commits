from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
HEX40 = re.compile(r"^[0-9a-f]{40}$")
Fetcher = Callable[[str, dict[str, str]], bytes]


class SnapshotFetchError(RuntimeError):
    pass


def git_blob_sha(payload: bytes) -> str:
    return hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()


def load_lock(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SnapshotFetchError(f"не удалось прочитать {path}: {exc}") from exc
    houses = value.get("houses") if isinstance(value, dict) else None
    if not isinstance(houses, dict) or not houses:
        raise SnapshotFetchError("SPACE_LOCK.houses должен быть непустым объектом")
    return value


def load_repository_aliases(path: Path) -> dict[str, list[str]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SnapshotFetchError(f"не удалось прочитать {path}: {exc}") from exc
    raw = value.get("repository_aliases", {}) if isinstance(value, dict) else {}
    if not isinstance(raw, dict):
        raise SnapshotFetchError("SPACE_REGISTRY.repository_aliases должен быть объектом")
    aliases: dict[str, list[str]] = {}
    for canonical, items in raw.items():
        if not isinstance(canonical, str) or not canonical:
            raise SnapshotFetchError("repository_aliases требует непустые canonical-адреса")
        if not isinstance(items, list) or not all(isinstance(item, str) and item for item in items):
            raise SnapshotFetchError(f"repository_aliases[{canonical}] должен быть массивом строк")
        aliases[canonical] = list(items)
    return aliases


def accepted_repositories(repository: str, aliases: dict[str, list[str]] | None) -> set[str]:
    accepted = {repository}
    if aliases:
        accepted.update(aliases.get(repository, []))
    return accepted


def raw_url(repository: str, revision: str, state_path: str) -> str:
    encoded_path = "/".join(urllib.parse.quote(part, safe="") for part in state_path.split("/"))
    return f"https://raw.githubusercontent.com/{repository}/{revision}/{encoded_path}"


def network_fetch(url: str, headers: dict[str, str]) -> bytes:
    request = urllib.request.Request(url, headers=headers)
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1 + attempt)
    raise SnapshotFetchError(f"не удалось получить {url}: {last_error}")


def validate_entry(house_id: str, entry: Any) -> tuple[str, str, str, str]:
    if not isinstance(entry, dict):
        raise SnapshotFetchError(f"lock {house_id} должен быть объектом")
    values = tuple(entry.get(field) for field in ("repository", "revision", "state_path", "blob_sha"))
    if not all(isinstance(value, str) and value for value in values):
        raise SnapshotFetchError(f"lock {house_id} требует repository, revision, state_path и blob_sha")
    repository, revision, state_path, expected_blob = values
    if not HEX40.fullmatch(revision) or not HEX40.fullmatch(expected_blob):
        raise SnapshotFetchError(f"lock {house_id} требует точные 40-символьные SHA")
    return repository, revision, state_path, expected_blob


def fetch_locked_houses(
    lock: dict[str, Any],
    output_dir: Path,
    fetcher: Fetcher = network_fetch,
    token: str | None = None,
    repository_aliases: dict[str, list[str]] | None = None,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    headers = {
        "Accept": "application/vnd.github.raw",
        "User-Agent": "experimental-harmony-space-builder",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    written: list[Path] = []
    for house_id, entry in lock["houses"].items():
        repository, revision, state_path, expected_blob = validate_entry(house_id, entry)
        url = raw_url(repository, revision, state_path)
        payload = fetcher(url, headers)
        actual_blob = git_blob_sha(payload)
        if actual_blob != expected_blob:
            raise SnapshotFetchError(
                f"blob SHA не совпал для {house_id}: expected={expected_blob} actual={actual_blob}"
            )
        try:
            state = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SnapshotFetchError(f"snapshot {house_id} не является UTF-8 JSON") from exc
        accepted = accepted_repositories(repository, repository_aliases)
        if not isinstance(state, dict) or state.get("technical_repository") not in accepted:
            raise SnapshotFetchError(f"technical_repository расходится для {house_id}")
        target = output_dir / f"{house_id}.json"
        target.write_bytes(payload)
        written.append(target)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Получить exact HOUSE_STATE snapshots по SPACE_LOCK")
    parser.add_argument("--lock", dest="lock_path", type=Path, default=ROOT / "SPACE_LOCK.json")
    parser.add_argument("--registry", type=Path, default=ROOT / "SPACE_REGISTRY.json")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        written = fetch_locked_houses(
            load_lock(args.lock_path),
            args.output_dir,
            token=os.environ.get("GITHUB_TOKEN"),
            repository_aliases=load_repository_aliases(args.registry),
        )
        print(f"SNAPSHOTS ПОЛУЧЕНЫ: {len(written)}")
        return 0
    except (OSError, SnapshotFetchError) as exc:
        print(f"ПОЛУЧЕНИЕ SNAPSHOTS НЕ ПРОЙДЕНО: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
