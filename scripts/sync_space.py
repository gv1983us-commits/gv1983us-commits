from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_space import build_space, git_blob_sha  # noqa: E402
from render_space_docs import (  # noqa: E402
    GUIDE_BEGIN,
    GUIDE_END,
    README_BEGIN,
    README_END,
    render_guide_section,
    render_readme_section,
    replace_generated_section,
)

HEX40 = re.compile(r"^[0-9a-f]{40}$")
Resolver = Callable[[str, str, dict[str, str]], str]
Fetcher = Callable[[str, dict[str, str]], bytes]
Replacer = Callable[[str | os.PathLike[str], str | os.PathLike[str]], None]


class SpaceSyncError(RuntimeError):
    pass


def load_registry(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SpaceSyncError(f"не удалось прочитать {path}: {exc}") from exc
    houses = value.get("houses") if isinstance(value, dict) else None
    if not isinstance(houses, list) or not houses:
        raise SpaceSyncError("SPACE_REGISTRY.houses должен быть непустым массивом")
    return value


def request_headers(token: str | None = None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "experimental-harmony-space-sync",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def network_json(url: str, headers: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            value = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SpaceSyncError(f"не удалось получить JSON {url}: {exc}") from exc
    if not isinstance(value, dict):
        raise SpaceSyncError(f"ожидался JSON-объект: {url}")
    return value


def network_resolve(repository: str, tracking_ref: str, headers: dict[str, str]) -> str:
    encoded = urllib.parse.quote(tracking_ref, safe="")
    value = network_json(
        f"https://api.github.com/repos/{repository}/commits/{encoded}",
        headers,
    )
    revision = value.get("sha")
    if not isinstance(revision, str) or not HEX40.fullmatch(revision):
        raise SpaceSyncError(f"не удалось разрешить exact revision для {repository}@{tracking_ref}")
    return revision


def raw_url(repository: str, revision: str, state_path: str) -> str:
    encoded_path = "/".join(urllib.parse.quote(part, safe="") for part in state_path.split("/"))
    return f"https://raw.githubusercontent.com/{repository}/{revision}/{encoded_path}"


def network_fetch(url: str, headers: dict[str, str]) -> bytes:
    raw_headers = dict(headers)
    raw_headers["Accept"] = "application/vnd.github.raw"
    request = urllib.request.Request(url, headers=raw_headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        raise SpaceSyncError(f"не удалось получить {url}: {exc}") from exc


def validate_registry_house(item: Any) -> tuple[str, str, str, str]:
    if not isinstance(item, dict):
        raise SpaceSyncError("каждая запись registry должна быть объектом")
    values = tuple(item.get(field) for field in ("house_id", "repository", "state_path", "tracking_ref"))
    if not all(isinstance(value, str) and value for value in values):
        raise SpaceSyncError(
            "registry требует house_id, repository, state_path и явный tracking_ref"
        )
    return values  # type: ignore[return-value]


def recorded_at_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def prepare_outputs(
    registry: dict[str, Any],
    root: Path,
    *,
    resolver: Resolver = network_resolve,
    fetcher: Fetcher = network_fetch,
    token: str | None = None,
    recorded_at: str | None = None,
) -> dict[str, bytes]:
    headers = request_headers(token)
    lock_houses: dict[str, dict[str, str]] = {}
    seen_ids: set[str] = set()
    seen_repositories: set[str] = set()

    with tempfile.TemporaryDirectory(prefix="space-snapshots-") as temp_name:
        source_dir = Path(temp_name)
        for item in registry["houses"]:
            house_id, repository, state_path, tracking_ref = validate_registry_house(item)
            if house_id in seen_ids:
                raise SpaceSyncError(f"повтор house_id: {house_id}")
            if repository in seen_repositories:
                raise SpaceSyncError(f"повтор repository: {repository}")
            seen_ids.add(house_id)
            seen_repositories.add(repository)

            revision = resolver(repository, tracking_ref, headers)
            if not HEX40.fullmatch(revision):
                raise SpaceSyncError(f"resolver вернул неточный revision для {house_id}")
            payload = fetcher(raw_url(repository, revision, state_path), headers)
            try:
                state = json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise SpaceSyncError(f"{house_id} HOUSE_STATE не является UTF-8 JSON") from exc
            if not isinstance(state, dict) or state.get("technical_repository") != repository:
                raise SpaceSyncError(f"technical_repository расходится для {house_id}")

            blob_sha = git_blob_sha(payload)
            (source_dir / f"{house_id}.json").write_bytes(payload)
            lock_houses[house_id] = {
                "repository": repository,
                "tracking_ref": tracking_ref,
                "revision": revision,
                "state_path": state_path,
                "blob_sha": blob_sha,
            }

        lock = {
            "schema_version": "1.1",
            "project": registry.get("project"),
            "recorded_at": recorded_at or recorded_at_now(),
            "registry": "SPACE_REGISTRY.json",
            "admission_role": "tracking_refs_resolved_to_exact_revisions_before_publish",
            "houses": lock_houses,
            "boundaries": [
                "tracking_ref_is_input_to_admission_not_a_reproducible_source",
                "revision_is_exact_not_latest",
                "blob_sha_identifies_the_locked_house_state",
                "all_outputs_are_staged_before_publish",
                "failed_publish_restores_previous_outputs",
                "lock_does_not_transfer_house_ownership",
                "lock_is_a_reproducible_reading_receipt",
            ],
        }
        state = build_space(registry, lock, source_dir)

    lock_bytes = (json.dumps(lock, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    state_bytes = (json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    try:
        readme = (root / "README.md").read_text(encoding="utf-8")
        guide = (root / "GUIDE.md").read_text(encoding="utf-8")
    except OSError as exc:
        raise SpaceSyncError(f"не удалось прочитать человеческую поверхность: {exc}") from exc

    rendered_readme = replace_generated_section(
        readme,
        README_BEGIN,
        README_END,
        render_readme_section(state),
    )
    rendered_guide = replace_generated_section(
        guide,
        GUIDE_BEGIN,
        GUIDE_END,
        render_guide_section(state),
    )
    return {
        "SPACE_LOCK.json": lock_bytes,
        "SPACE_STATE.json": state_bytes,
        "README.md": rendered_readme.encode("utf-8"),
        "GUIDE.md": rendered_guide.encode("utf-8"),
    }


def publish_outputs(
    outputs: dict[str, bytes],
    root: Path,
    *,
    replacer: Replacer = os.replace,
) -> None:
    target_names = tuple(outputs)
    with tempfile.TemporaryDirectory(prefix=".space-sync-", dir=root) as temp_name:
        transaction = Path(temp_name)
        staged = transaction / "staged"
        backup = transaction / "backup"
        staged.mkdir()
        backup.mkdir()

        for name, payload in outputs.items():
            stage_path = staged / name
            stage_path.parent.mkdir(parents=True, exist_ok=True)
            stage_path.write_bytes(payload)

            target = root / name
            if not target.is_file():
                raise SpaceSyncError(f"целевой файл отсутствует: {name}")
            backup_path = backup / name
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup_path)

        replaced: list[str] = []
        try:
            for name in target_names:
                replacer(staged / name, root / name)
                replaced.append(name)
        except OSError as exc:
            rollback_errors: list[str] = []
            for name in reversed(replaced):
                try:
                    replacer(backup / name, root / name)
                except OSError as rollback_exc:
                    rollback_errors.append(f"{name}: {rollback_exc}")
            if rollback_errors:
                raise SpaceSyncError(
                    "публикация не прошла, rollback неполон: " + "; ".join(rollback_errors)
                ) from exc
            raise SpaceSyncError("публикация не прошла; прежнее состояние восстановлено") from exc


def sync_space(
    root: Path = ROOT,
    *,
    resolver: Resolver = network_resolve,
    fetcher: Fetcher = network_fetch,
    token: str | None = None,
    recorded_at: str | None = None,
    replacer: Replacer = os.replace,
) -> dict[str, bytes]:
    registry = load_registry(root / "SPACE_REGISTRY.json")
    outputs = prepare_outputs(
        registry,
        root,
        resolver=resolver,
        fetcher=fetcher,
        token=token,
        recorded_at=recorded_at,
    )
    publish_outputs(outputs, root, replacer=replacer)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Атомарно принять текущие tracking refs домов и пересобрать площадь"
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="подготовить и проверить все выходы, но не заменять файлы",
    )
    args = parser.parse_args()
    try:
        registry = load_registry(args.root / "SPACE_REGISTRY.json")
        outputs = prepare_outputs(
            registry,
            args.root,
            token=os.environ.get("GITHUB_TOKEN"),
        )
        if args.dry_run:
            print("ТРАНЗАКЦИЯ ПОДГОТОВЛЕНА: " + ", ".join(outputs))
        else:
            publish_outputs(outputs, args.root)
            print("ПЛОЩАДЬ АТОМАРНО ОБНОВЛЕНА: " + ", ".join(outputs))
        return 0
    except (OSError, SpaceSyncError) as exc:
        print(f"ОБНОВЛЕНИЕ ПЛОЩАДИ НЕ ПРОЙДЕНО: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
