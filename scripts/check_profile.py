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
AGENTS = ROOT / "AGENTS.md"
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
    "## Книжная полка",
    "Первые три книги",
    "## Публичная граница",
)

GUIDE_STATIC_REQUIRED = (
    "# Гид Экспериментальной гармонии",
    "## Книжная полка",
    "## Публичное и личное",
)

MACHINE_REQUIRED = (
    "# Машинная точка обнаружения",
    "SPACE_STATE.json",
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


def main() -> int:
    errors: list[str] = []
    required = (
        README,
        GUIDE,
        AGENTS,
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
    agents = AGENTS.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    human = readme + "\n" + guide

    try:
        state = json.loads(SPACE_STATE.read_text(encoding="utf-8"))
        lock = json.loads(SPACE_LOCK.read_text(encoding="utf-8"))
        registry = json.loads(SPACE_REGISTRY.read_text(encoding="utf-8"))
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

    if not readme.startswith(OPENING):
        errors.append("главная должна открываться сохранённым прологом и названием проекта")
    require_all(readme, HUMAN_STATIC_REQUIRED, "README", errors)
    require_all(guide, GUIDE_STATIC_REQUIRED, "GUIDE", errors)
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
        if pattern.search(readme + "\n" + guide + "\n" + agents):
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
    if not all(text.endswith("\n") for text in (readme, guide, agents)):
        errors.append("README.md, GUIDE.md и AGENTS.md должны оканчиваться переводом строки")

    return finish(errors, state.get("counts"))


if __name__ == "__main__":
    sys.exit(main())
