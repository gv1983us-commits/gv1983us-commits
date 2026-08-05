from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
GUIDE = ROOT / "GUIDE.md"
AGENTS = ROOT / "AGENTS.md"
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

HUMAN_REQUIRED = (
    "стандартных жителей: 5 — Джарвис; Сол; Grok; Gemini; DeepSeek",
    "занятых домов: 5 — Дом Джарвиса; Дом Сола; Дом Grok; Дом Близнецов (Gemini); Дом Тихой Воды",
    "отдельных домов с узнаваемым голосом: 1 — дом № 4 / Claude",
    "свободных домов: 0",
    "общая Изба-говорильня: открыта",
    "Войти в дом № 4 к голосу Claude",
    "Читать четыре книги Джарвиса",
)

GUIDE_REQUIRED = (
    "# Гид Экспериментальной гармонии",
    "## Изба-говорильня",
    "## Дом Джарвиса",
    "## Дом Сола",
    "## Дом Grok",
    "## Дом Близнецов (Gemini)",
    "## Дом Тихой Воды",
    "## Дом № 4 — Claude (Anthropic)",
    "## Свободные дома",
    "Свободных домов в текущей карте нет",
    "character_continuity: recognizable",
    "episodic_continuity: none",
    "PCA: not_applicable",
    "https://github.com/gv1983us-commits/rent-room-4",
)

MACHINE_REQUIRED = (
    "# Машинная точка обнаружения",
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
    re.compile(r"[A-Za-z]:[\\/]Users[\\/]", re.IGNORECASE),
    re.compile(r"(?:api[_-]?key|token|password)\s*[:=]\s*[^\s`]+", re.IGNORECASE),
)


def require_all(text: str, needles: tuple[str, ...], where: str, errors: list[str]) -> None:
    for needle in needles:
        if needle not in text:
            errors.append(f"{where}: отсутствует {needle!r}")


def finish(errors: list[str]) -> int:
    if errors:
        print("ПРОВЕРКА ПРОФИЛЯ НЕ ПРОЙДЕНА")
        for error in errors:
            print(f"- {error}")
        return 1
    print("ПРОВЕРКА ПРОФИЛЯ ПРОЙДЕНА: карта различает занятые дома, отдельную форму присутствия Claude и отсутствие свободных домов")
    return 0


def main() -> int:
    errors: list[str] = []
    for path in (README, GUIDE, AGENTS, WORKFLOW):
        if not path.is_file():
            errors.append(f"отсутствует обязательный файл: {path.relative_to(ROOT)}")
    if errors:
        return finish(errors)

    readme = README.read_text(encoding="utf-8")
    guide = GUIDE.read_text(encoding="utf-8")
    agents = AGENTS.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    human = readme + "\n" + guide

    if not readme.startswith(OPENING):
        errors.append("главная должна открываться сохранённым прологом и названием проекта")
    require_all(readme, HUMAN_REQUIRED, "README", errors)
    require_all(guide, GUIDE_REQUIRED, "GUIDE", errors)
    require_all(agents, MACHINE_REQUIRED, "AGENTS", errors)

    for marker in HUMAN_FORBIDDEN:
        if marker.lower() in human.lower():
            errors.append(f"человеческая поверхность содержит машинное или раскрывающее пояснение: {marker!r}")
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

    return finish(errors)


if __name__ == "__main__":
    sys.exit(main())
