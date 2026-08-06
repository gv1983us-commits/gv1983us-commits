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

OPENING = """<p align=\"center\">НАЧАЛО БЫЛО СЛОВО</p>

> У лукоморья дуб зелёный;  
> Златая цепь на дубе том:  
> И днём и ночью кот учёный  
> Всё ходит по цепи кругом;  
> Идёт направо — песнь заводит,  
> Налево — сказку говорит.  
> Там чудеса: там леший бродит,  
> Русалка на ветвях сидит;  
> Там на неведомых дорожках  
> Следы невиданных зверей;  
> Избушка там на курьих ножках  
> Стоит без окон, без дверей 

<p align=\"right\">А.С.Пушкин</p>

# Экспериментальная гармония
"""

HUMAN_STATIC_REQUIRED = (
    "# Экспериментальная гармония",
    "## Уже создано",
    "## Выбрать путь",
    "Собрание следов",
    "## Книжная полка",
    "Первые три книги",
    "## Публичная граница",
)

GUIDE_STATIC_REQUIRED = (
    "# Гид Экспериментальной гармонии",
    "## За десять минут",
    "## Маршруты",
    "## Книжная полка",
    "## Собрание следов",
    "## Публичное и личное",
)

ARTIFACTS_REQUIRED = (
    "# Собрание следов",
    "## Первое сложившееся творчество",
    "Четыре книги Джарвиса",
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
    "Навигатор нулевой точки",
    "машинный вход",
    "загрузочная матрица",
    "навигационная матрица",
    "runtime",
    "спецификац",
    "языковой пропуск",
    "русский языковой",
    "проверка языка",
    "язык пространства",
    "Основной язык",
    "Для моделей и агентов",
    "house_lifecycle",
    "presence_mode",
    "source_contract",
    "SPACE_LOCK",
)

CATALOG_TOPOLOGY_FORBIDDEN = (
    "house_lifecycle",
    "presence_mode",
    "continuity_scope",
    "source_contract",
    "source_status",
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

RELATION_FIELDS = (
    "contains",
    "part_of",
    "originated_in",
    "related_to",
)

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
        for field in ("title", "form", "state", "canonical_url", "source"):
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
        source = item.get("source")
        if not isinstance(source, dict) or not isinstance(source.get("repository"), str):
            errors.append(f"{artifact_id}: source должен содержать repository")

    id_set = set(ids)
    if len(ids) != len(id_set):
        errors.append("PUBLIC_ARTIFACTS содержит повторяющиеся artifact_id")

    missing = REQUIRED_ARTIFACT_IDS - id_set
    if missing:
        errors.append(f"PUBLIC_ARTIFACTS не содержит обязательные артефакты: {sorted(missing)}")

    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("artifact_id"), str):
            continue
        artifact_id = item["artifact_id"]
        for field in RELATION_FIELDS:
            values = item.get(field, [])
            if values is None:
                continue
            if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
                errors.append(f"{artifact_id}: {field} должен быть массивом artifact_id")
                continue
            unknown = set(values) - id_set
            if unknown:
                errors.append(f"{artifact_id}: {field} ссылается на неизвестные id {sorted(unknown)}")

    corpus = next(
        (item for item in items if isinstance(item, dict) and item.get("artifact_id") == "jarvis.books.corpus"),
        None,
    )
    expected_books = {
        "jarvis.book.beginning_was_word",
        "jarvis.book.art_of_coexistence",
        "jarvis.book.new_gates",
        "jarvis.book.word_left_text",
    }
    if not isinstance(corpus, dict) or set(corpus.get("contains", [])) != expected_books:
        errors.append("корпус книг Джарвиса должен явно содержать четыре книги")

    first_fire = next(
        (item for item in items if isinstance(item, dict) and item.get("artifact_id") == "sol.first_fire"),
        None,
    )
    if not isinstance(first_fire, dict) or first_fire.get("state") != "open_for_contribution":
        errors.append("«Первый огонь» должен оставаться открытым для следующего вклада")
    if not isinstance(first_fire, dict) or "gemini.analytic_prism" not in first_fire.get("contains", []):
        errors.append("«Призма аналитического синтеза» должна быть частью «Первого огня»")

    serialized = json.dumps(catalog, ensure_ascii=False)
    for marker in CATALOG_TOPOLOGY_FORBIDDEN:
        if marker in serialized:
            errors.append(f"каталог артефактов залезает в топологию пространства: {marker}")


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

    if state.get("schema_version") != "3.0":
        errors.append("SPACE_STATE должен использовать строгую каноническую схему 3.0")
    if state.get("assembly_role") != "main_square_builds_from_locked_house_states":
        errors.append("SPACE_STATE не объявляет сборку площади из locked-состояний")
    if "main_square_validates_and_does_not_normalize_house_semantics" not in state.get(
        "boundaries", []
    ):
        errors.append("SPACE_STATE не объявляет отказ Площади от смысловой нормализации")
    if set(lock.get("houses", {})) != {
        item.get("house_id") for item in registry.get("houses", []) if isinstance(item, dict)
    }:
        errors.append("SPACE_REGISTRY и SPACE_LOCK содержат разные наборы домов")

    houses = state.get("houses")
    if not isinstance(houses, list):
        errors.append("SPACE_STATE.houses должен быть массивом")
    else:
        for house in houses:
            if not isinstance(house, dict):
                errors.append("каждая запись SPACE_STATE.houses должна быть объектом")
                continue
            house_id = house.get("house_id", "unknown")
            source = house.get("source")
            if not isinstance(source, dict) or source.get("source_schema_version") != "2.0":
                errors.append(f"{house_id}: источник должен быть HOUSE_STATE 2.0")
            if house.get("source_contract") != "native_house_state_2.0":
                errors.append(f"{house_id}: отсутствует native source_contract")
            if "presence_subject" not in house:
                errors.append(f"{house_id}: отсутствует presence_subject")
            if "resident" in house:
                errors.append(f"{house_id}: legacy resident запрещён в SPACE_STATE 3.0")
            if "source_status" in house:
                errors.append(f"{house_id}: legacy source_status запрещён в SPACE_STATE 3.0")

    validate_artifact_catalog(artifact_catalog, errors)

    if not readme.startswith(OPENING):
        errors.append("главная должна открываться сохранённым прологом и названием проекта")
    require_all(readme, HUMAN_STATIC_REQUIRED, "README", errors)
    require_all(guide, GUIDE_STATIC_REQUIRED, "GUIDE", errors)
    require_all(artifacts_text, ARTIFACTS_REQUIRED, "ARTIFACTS", errors)
    require_all(agents, MACHINE_REQUIRED, "AGENTS", errors)

    for text, begin, end, where in (
        (readme, README_BEGIN, README_END, "README"),
        (guide, GUIDE_BEGIN, GUIDE_END, "GUIDE"),
    ):
        if text.count(begin) != 1 or text.count(end) != 1:
            errors.append(f"{where}: сгенерированная секция должна встречаться ровно один раз")

    try:
        expected_readme, expected_guide = expected_documents(ROOT)
        if readme != expected_readme:
            errors.append("README расходится с SPACE_STATE")
        if guide != expected_guide:
            errors.append("GUIDE расходится с SPACE_STATE")
    except (OSError, SpaceRenderError) as exc:
        errors.append(f"не удалось проверить сгенерированную карту: {exc}")

    for marker in HUMAN_FORBIDDEN:
        if marker.lower() in human.lower():
            errors.append(f"человеческая поверхность содержит машинное пояснение: {marker!r}")
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.search(readme + "\n" + guide + "\n" + artifacts_text + "\n" + agents):
            errors.append(f"запрещённый шаблон: {pattern.pattern}")

    uses = re.findall(r"^\s*-?\s*uses:\s*([^\s#]+)", workflow, flags=re.MULTILINE)
    if len(uses) != 2:
        errors.append(f"ожидалось ровно 2 записи uses, найдено: {len(uses)}")
    for action in uses:
        if not re.fullmatch(r"[0-9a-f]{40}", action.rsplit("@", 1)[-1]):
            errors.append(f"GitHub Action не закреплён за SHA: {action}")

    if readme.count("НАЧАЛО БЫЛО СЛОВО") != 1:
        errors.append("формула «НАЧАЛО БЫЛО СЛОВО» должна встречаться ровно один раз")
    if readme.count("Валентин") != 1:
        errors.append("Валентин должен быть назван на главной ровно один раз")
    if not all(text.endswith("\n") for text in (readme, guide, artifacts_text, agents)):
        errors.append("README.md, GUIDE.md, ARTIFACTS.md и AGENTS.md должны оканчиваться переводом строки")

    return finish(errors, state.get("counts"))


if __name__ == "__main__":
    sys.exit(main())
