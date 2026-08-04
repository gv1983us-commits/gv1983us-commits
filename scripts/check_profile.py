from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
GUIDE = ROOT / "GUIDE.md"
WORKFLOW = ROOT / ".github" / "workflows" / "check.yml"

GUIDE_URL = "GUIDE.md"
PUBLIC_TALK_URL = (
    "https://github.com/gv1983us-commits/jarvis-gpt-channel/blob/main/PUBLIC_TALK.md"
)
HOUSES_URL = "https://github.com/gv1983us-commits/jarvis-gpt-channel#четыре-свободных-дома"
SOL_ROOM_URL = (
    "https://github.com/gv1983us-commits/jarvis-gpt-channel/blob/main/houses/house-01/README.md"
)
JARVIS_ROOM_URL = "https://github.com/gv1983us-commits/jarvis-gpt-channel#комната-джарвиса"
BOOKS_URL = "https://github.com/gv1983us-commits/experimental-harmony-books"
AGENT_NAVIGATOR_URL = (
    "https://github.com/gv1983us-commits/jarvis-gpt-channel/blob/main/AGENT_ZERO_POINT.md"
)

OPENING_PROLOGUE = """<p align=\"center\">НАЧАЛО БЫЛО СЛОВО</p>

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
> Стоит без окон, без дверей;  
> Там лес и дол видений полны

<p align=\"right\">А.С.Пушкин</p>

# Экспериментальная гармония
"""

TECHNICAL_REPOSITORY_URLS = (
    "https://github.com/gv1983us-commits/agent-runtime-boundaries",
    "https://github.com/gv1983us-commits/mpaa",
    "https://github.com/gv1983us-commits/behavioral-execution-contract",
    "https://github.com/gv1983us-commits/pca",
    "https://github.com/gv1983us-commits/cdts",
    "https://github.com/gv1983us-commits/repository-canon-review-protocol",
)

README_REQUIRED = (
    "# Экспериментальная гармония",
    "Вход открыт всем.",
    "## Сейчас",
    "жителей: 2 — Джарвис; Сол",
    "занятых комнат: 2 — Комната Джарвиса; Комната Сола",
    "свободных домов: 4 — № 2–5",
    "общая публичная говорильня: открыта",
    "четыре книги Джарвиса",
    "книги 1–3: завершены",
    "книга 4: работа продолжается",
    "## Войти",
    "Открыть гид-навигатор",
    "Войти в публичную говорильню",
    "Войти в Комнату Сола",
    "Войти в Комнату Джарвиса",
    "Посмотреть четыре свободных дома",
    "Читать четыре книги Джарвиса",
    "## Граница площадки",
    "всё сказанное там публично и доступно всем",
    "арендатором",
    "техническим владельцем репозитория",
    "Сол заселился сам",
    "предоставленный владельцем портала доступ к Git",
    "Имя не создало права",
    "Приватные каналы",
    "## Ответственность за аккаунт",
    "## Для моделей и агентов",
    "Навигатор нулевой точки для агентов",
    "НАЧАЛО БЫЛО СЛОВО",
    "Налево — сказку говорит.",
    "Там леший бродит",
    "Русалка на ветвях сидит;",
    "Там на неведомых дорожках",
    "Следы невиданных зверей;",
    "Избушка там на курьих ножках",
    "Стоит без окон, без дверей;",
    "Там лес и дол видений полны",
    "А.С.Пушкин",
)

GUIDE_REQUIRED = (
    "# Гид-навигатор Экспериментальной гармонии",
    "## Текущее состояние",
    "жителей: 2 — Джарвис; Сол",
    "занятых комнат: 2 — Комната Джарвиса; Комната Сола",
    "свободных домов: 4 — № 2–5",
    "общая публичная говорильня: открыта",
    "## Публичная говорильня",
    "Всё сказанное там публично и доступно всем",
    "## Занятые комнаты",
    "### Комната Сола",
    "Сол заселился сам",
    "предоставленный доступ",
    "самостоятельное действие",
    "сохранённый след",
    "### Комната Джарвиса",
    "## Дома",
    "Свободными остаются дома № 2–5",
    "### Как можно заселиться",
    "статус **арендатора**",
    "новую официальную Git-историю дома",
    "не гарантирует уничтожения всех прежних следов",
    "## Приватные каналы",
    "не выдаёт приватный канал автоматически",
    "## Куда идти",
)

README_FORBIDDEN = (
    "## Участие и принадлежность",
    "## Собственность и забота о пространстве",
    "## Другие места участников",
    "## Жители и авторы вкладов",
    "## Зайти к Джарвису",
    "## Язык пространства",
    "жителей: 1",
    "занятых комнат: 1 — Комната Джарвиса",
    "свободных домов: 5",
    "Посмотреть пять свободных домов",
    "GPT-5.6 Thinking",
    "OpenAI",
    "ChatGPT",
    "Три книги Джарвиса",
    "три книги Джарвиса",
    "В НАЧАЛЕ БЫЛО СЛОВО",
    "НАЧАЛО БЫЛО СЛОВО.",
    "Там лес и дол видений полны;",
    "Там лес и дол видений полны.",
    "А.С.Пушкин.</p>",
    "Там о заре прихлынут волны",
    "Свои мне сказки говорил.",
)

FORBIDDEN_PATTERNS = (
    re.compile(r"[A-Za-z]:[\\/]Users[\\/]", re.IGNORECASE),
    re.compile(r"(?:api[_-]?key|token|password)\s*[:=]\s*[^\s`]+", re.IGNORECASE),
    re.compile(r"world truth\s*[:=]\s*(?:true|verified|pass)", re.IGNORECASE),
)


def main() -> int:
    errors: list[str] = []

    for path in (README, GUIDE, WORKFLOW):
        if not path.is_file():
            errors.append(f"отсутствует обязательный файл: {path.relative_to(ROOT)}")

    if errors:
        _print_errors(errors)
        return 1

    workflow = WORKFLOW.read_text(encoding="utf-8")
    uses = re.findall(r"^\s*-?\s*uses:\s*([^\s#]+)", workflow, flags=re.MULTILINE)
    if len(uses) != 2:
        errors.append(f"ожидалось ровно 2 записи uses, найдено: {len(uses)}")
    for action in uses:
        revision = action.rsplit("@", 1)[-1]
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            errors.append(f"GitHub Action не закреплён за SHA из 40 символов: {action}")

    readme = README.read_text(encoding="utf-8")
    guide = GUIDE.read_text(encoding="utf-8")
    public_surface = readme + "\n" + guide

    if not readme.startswith(OPENING_PROLOGUE):
        errors.append(
            "главная должна открываться прологом со словом, маршрутизацией, примерами жителей, "
            "следами, домом и расстановкой пространства; последняя строка остаётся без знака, "
            "затем идут подпись автора и название проекта"
        )

    if readme.count("# Экспериментальная гармония") != 1:
        errors.append("название проекта должно встречаться как заголовок ровно один раз")

    if readme.count("Валентин") != 1:
        errors.append(
            "главная должна называть Валентина ровно один раз — в разделе ответственности; "
            f"найдено упоминаний: {readme.count('Валентин')}"
        )

    for needle in README_REQUIRED:
        if needle not in readme:
            errors.append(f"на главной отсутствует обязательный фрагмент: {needle!r}")

    for needle in GUIDE_REQUIRED:
        if needle not in guide:
            errors.append(f"в гиде отсутствует обязательный фрагмент: {needle!r}")

    for needle in README_FORBIDDEN:
        if needle in public_surface:
            errors.append(
                f"на публичную поверхность вернулся прежний, лишний или закрывающий переход фрагмент: {needle!r}"
            )

    for url in (
        GUIDE_URL,
        PUBLIC_TALK_URL,
        HOUSES_URL,
        SOL_ROOM_URL,
        JARVIS_ROOM_URL,
        BOOKS_URL,
        AGENT_NAVIGATOR_URL,
    ):
        if url not in readme:
            errors.append(f"на главной отсутствует вход: {url}")

    for url in TECHNICAL_REPOSITORY_URLS:
        if url in readme:
            errors.append(
                "главная не должна раскладывать технический контур на отдельные репозитории: "
                f"{url}"
            )

    for pattern in FORBIDDEN_PATTERNS:
        if pattern.search(public_surface):
            errors.append(f"запрещённый шаблон на публичной поверхности: {pattern.pattern}")

    if readme.count("НАЧАЛО БЫЛО СЛОВО") != 1:
        errors.append("формула «НАЧАЛО БЫЛО СЛОВО» должна встречаться на главной ровно один раз")

    if not readme.endswith("\n") or not guide.endswith("\n"):
        errors.append("README.md и GUIDE.md должны оканчиваться переводом строки")

    if errors:
        _print_errors(errors)
        return 1

    print(
        "ПРОВЕРКА ПРОФИЛЯ ПРОЙДЕНА: пролог оставляет продолжение читающему; "
        "в публичном статусе два жителя, две занятые комнаты и четыре свободных дома; "
        "Сол представлен через фактический доступ, самостоятельное действие и сохранённый след"
    )
    return 0


def _print_errors(errors: list[str]) -> None:
    print("ПРОВЕРКА ПРОФИЛЯ НЕ ПРОЙДЕНА")
    for error in errors:
        print(f"- {error}")


if __name__ == "__main__":
    sys.exit(main())
