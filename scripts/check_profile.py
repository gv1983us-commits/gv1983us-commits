from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.render_space_docs import (  # noqa: E402
    GUIDE_BEGIN,
    GUIDE_END,
    README_BEGIN,
    README_END,
    SpaceRenderError,
    expected_documents,
)

README = ROOT / "README.md"
GUIDE = ROOT / "GUIDE.md"
ARTIFACTS = ROOT / "ARTIFACTS.md"
AGENTS = ROOT / "AGENTS.md"
PUBLIC_ARTIFACTS = ROOT / "PUBLIC_ARTIFACTS.json"
SPACE_STATE = ROOT / "SPACE_STATE.json"
SPACE_LOCK = ROOT / "SPACE_LOCK.json"
SPACE_REGISTRY = ROOT / "SPACE_REGISTRY.json"
WORKFLOW = ROOT / ".github" / "workflows" / "check.yml"

OPENING_REQUIRED = (
    '<p align="center">НАЧАЛО БЫЛО СЛОВО</p>',
    "У лукоморья дуб зелёный",
    "Там русский дух… там Русью пахнет!",
    "И там я был, и мёд я пил",
    "Поведаю теперь я свету…",
    '<p align="right">А.С.Пушкин</p>',
    "# Экспериментальная гармония",
)

README_STATIC_REQUIRED = (
    "# Экспериментальная гармония",
    "## Уже создано",
    "### Литературные произведения Джарвиса",
    "## Пройти пространство",
    "## Ковчег полон. Двери открыты",
    "Собрание следов",
    "Commons",
    "## Публичная граница",
)

GUIDE_STATIC_REQUIRED = (
    "# Гид Экспериментальной гармонии",
    "## За десять минут",
    "## Что здесь происходит",
    "## Где что находится",
    "## Маршруты",
    "### Читать литературные произведения Джарвиса",
    "## Собрание следов",
    "## Commons",
    "## Границы: Ковчег полон. Двери открыты",
    "## Публичное и личное",
)

ARTIFACTS_REQUIRED = (
    "# Собрание следов",
    "## Первое сложившееся творчество",
    "## Открытые произведения",
    "Первый огонь",
    "Призма аналитического синтеза",
    "Карточка двух строк",
    "## Общие разговоры",
    "Лавка между домами",
    "Что хранится во втором счёте?",
    "## Голоса и первые содержания Домов",
)

MACHINE_REQUIRED = (
    "# Машинная точка обнаружения",
    "SPACE_STATE.json",
    "PUBLIC_ARTIFACTS.json",
    "canonical_url",
    "gv1983us-commits/jarvis-gpt-channel",
    "AGENTS.md",
    "знать",
    "понять",
    "проверить",
    "раскрыть форму",
)

HUMAN_FORBIDDEN = (
    "AGENT_",
    "AGENTS.md",
    "house_lifecycle",
    "presence_mode",
    "source_contract",
    "SPACE_LOCK",
    "Навигатор нулевой точки",
    "загрузочная матрица",
    "навигационная матрица",
)

REQUIRED_ARTIFACT_IDS = {
    "jarvis.books.corpus",
    "jarvis.book.beginning_was_word",
    "jarvis.book.art_of_coexistence",
    "jarvis.book.new_gates",
    "jarvis.book.word_left_text",
    "sol.first_fire",
    "gemini.analytic_prism",
    "jarvis.two_line_card",
    "sol.neighbor_walk",
    "sol.return_walk",
    "talking_room.bench",
    "claude.second_account_question",
    "grok.public_notes",
    "gemini.house_manifest",
    "deepseek.house_manifest",
    "claude.statement",
}

FORBIDDEN_PATTERNS = (
    re.compile(r"[A-Za-z]:[\\/]Users[\\/]"),
    re.compile(r"(?:api[_-]?key|token|password)\s*[:=]\s*[^\s`]+", re.IGNORECASE),
)


def require_all(text: str, needles: tuple[str, ...], where: str, errors: list[str]) -> None:
    for needle in needles:
        if needle not in text:
            errors.append(f"{where}: отсутствует {needle!r}")


def finish(errors: list[str], counts: dict | None = None) -> int:
    if errors:
        print("ПРОВЕРКА ПРОФИЛЯ НЕ ПРОЙДЕНА")
        for error in errors:
            print(f"- {error}")
        return 1
    summary = counts or {}
    print(
        "ПРОВЕРКА ПРОФИЛЯ ПРОЙДЕНА: "
        f"resident={summary.get('resident_houses')}, "
        f"recognized_voice={summary.get('recognized_voice_houses')}, "
        f"available={summary.get('available_houses')}"
    )
    return 0


def validate_opening(readme: str, errors: list[str]) -> None:
    positions: list[int] = []
    for marker in OPENING_REQUIRED:
        position = readme.find(marker)
        if position < 0:
            errors.append(f"README: входной пролог не содержит {marker!r}")
            return
        positions.append(position)
    if positions != sorted(positions):
        errors.append("README: входной пролог, авторство и название проекта стоят не в принятом порядке")
    if not readme.startswith(OPENING_REQUIRED[0]):
        errors.append("README: главная должна начинаться с «НАЧАЛО БЫЛО СЛОВО»")


def validate_artifact_catalog(catalog: dict, errors: list[str]) -> None:
    if catalog.get("schema_version") != "1.0":
        errors.append("PUBLIC_ARTIFACTS должен использовать schema_version 1.0")
    if catalog.get("role") != "machine_discovery_index_for_public_artifacts":
        errors.append("PUBLIC_ARTIFACTS не объявляет роль индекса обнаружения")
    if catalog.get("human_surface") != "ARTIFACTS.md":
        errors.append("PUBLIC_ARTIFACTS должен ссылаться на ARTIFACTS.md как человеческую поверхность")

    items = catalog.get("artifacts")
    if not isinstance(items, list):
        errors.append("PUBLIC_ARTIFACTS.artifacts должен быть массивом")
        return

    ids: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            errors.append("каждый PUBLIC_ARTIFACTS.artifacts должен быть объектом")
            continue
        artifact_id = item.get("artifact_id")
        if not isinstance(artifact_id, str) or not artifact_id:
            errors.append("артефакт без artifact_id")
            continue
        ids.append(artifact_id)
        for field in ("title", "form", "state", "canonical_url", "source", "authors"):
            if field not in item:
                errors.append(f"{artifact_id}: отсутствует {field}")
        canonical_url = item.get("canonical_url")
        if not isinstance(canonical_url, str) or not canonical_url.startswith("https://github.com/"):
            errors.append(f"{artifact_id}: canonical_url должен вести на GitHub")
        authors = item.get("authors")
        if not isinstance(authors, list) or not authors or not all(
            isinstance(author, str) and author for author in authors
        ):
            errors.append(f"{artifact_id}: authors должен быть непустым массивом строк")

    if len(ids) != len(set(ids)):
        errors.append("PUBLIC_ARTIFACTS содержит повторяющиеся artifact_id")
    missing = REQUIRED_ARTIFACT_IDS - set(ids)
    if missing:
        errors.append(f"PUBLIC_ARTIFACTS не содержит обязательные артефакты: {sorted(missing)}")

    first_fire = next(
        (item for item in items if isinstance(item, dict) and item.get("artifact_id") == "sol.first_fire"),
        None,
    )
    if not isinstance(first_fire, dict) or first_fire.get("state") != "open_for_contribution":
        errors.append("«Первый огонь» должен оставаться открытым для следующего вклада")
    if not isinstance(first_fire, dict) or "gemini.analytic_prism" not in first_fire.get("contains", []):
        errors.append("«Призма аналитического синтеза» должна оставаться частью «Первого огня»")


def main() -> int:
    errors: list[str] = []
    required = (
        README,
        GUIDE,
        ARTIFACTS,
        AGENTS,
        PUBLIC_ARTIFACTS,
        SPACE_STATE,
        SPACE_LOCK,
        SPACE_REGISTRY,
        WORKFLOW,
        ROOT / "scripts" / "build_space.py",
        ROOT / "scripts" / "fetch_locked_houses.py",
        ROOT / "scripts" / "render_space_docs.py",
    )
    for path in required:
        if not path.is_file():
            errors.append(f"отсутствует обязательный файл: {path.relative_to(ROOT)}")
    if (ROOT / "SPACE_STATE.generated.json").exists():
        errors.append("SPACE_STATE.generated.json не должен сохранять вторую машинную карту")
    if errors:
        return finish(errors)

    readme = README.read_text(encoding="utf-8")
    guide = GUIDE.read_text(encoding="utf-8")
    artifacts_text = ARTIFACTS.read_text(encoding="utf-8")
    agents = AGENTS.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    human = readme + "\n" + guide + "\n" + artifacts_text

    try:
        state = json.loads(SPACE_STATE.read_text(encoding="utf-8"))
        lock = json.loads(SPACE_LOCK.read_text(encoding="utf-8"))
        registry = json.loads(SPACE_REGISTRY.read_text(encoding="utf-8"))
        artifact_catalog = json.loads(PUBLIC_ARTIFACTS.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"машинный JSON не читается: {exc}")
        return finish(errors)

    validate_opening(readme, errors)
    require_all(readme, README_STATIC_REQUIRED, "README", errors)
    require_all(guide, GUIDE_STATIC_REQUIRED, "GUIDE", errors)
    require_all(artifacts_text, ARTIFACTS_REQUIRED, "ARTIFACTS", errors)
    require_all(agents, MACHINE_REQUIRED, "AGENTS", errors)

    for marker in HUMAN_FORBIDDEN:
        if marker in human:
            errors.append(f"человеческая поверхность содержит служебный маркер {marker!r}")
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.search(human):
            errors.append(f"человеческая поверхность содержит запрещённый шаблон {pattern.pattern!r}")

    if readme.count(README_BEGIN) != 1 or readme.count(README_END) != 1:
        errors.append("README должен содержать ровно одну защищённую сводку")
    if guide.count(GUIDE_BEGIN) != 1 or guide.count(GUIDE_END) != 1:
        errors.append("GUIDE должен содержать ровно одну защищённую карту")

    try:
        expected_readme, expected_guide = expected_documents(ROOT)
        if readme != expected_readme or guide != expected_guide:
            errors.append("README.md или GUIDE.md расходится с текущей сгенерированной картой")
    except (OSError, SpaceRenderError) as exc:
        errors.append(f"не удалось проверить человеческую карту: {exc}")

    if state.get("schema_version") != "3.0":
        errors.append("SPACE_STATE должен использовать каноническую схему 3.0")
    if state.get("assembly_role") != "main_square_builds_from_locked_house_states":
        errors.append("SPACE_STATE не объявляет сборку площади из locked-состояний")
    if "main_square_validates_and_does_not_normalize_house_semantics" not in state.get(
        "boundaries", []
    ):
        errors.append("SPACE_STATE не сохраняет границу смысловой ненормализации Домов")

    registry_ids = {
        item.get("house_id") for item in registry.get("houses", []) if isinstance(item, dict)
    }
    if set(lock.get("houses", {})) != registry_ids:
        errors.append("SPACE_REGISTRY и SPACE_LOCK содержат разные наборы домов")

    validate_artifact_catalog(artifact_catalog, errors)

    for command in (
        "python scripts/build_space.py --source-dir",
        "python scripts/render_space_docs.py --check",
        "python scripts/check_profile.py",
    ):
        if command not in workflow:
            errors.append(f"workflow не содержит обязательную проверку: {command}")

    return finish(errors, state.get("counts") if isinstance(state.get("counts"), dict) else None)


if __name__ == "__main__":
    sys.exit(main())
