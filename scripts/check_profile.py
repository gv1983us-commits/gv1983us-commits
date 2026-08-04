from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
WORKFLOW = ROOT / ".github" / "workflows" / "check.yml"

PUBLIC_ENTRIES = {
    "Комната Джарвиса": "https://github.com/gv1983us-commits/jarvis-gpt-channel",
    "Книги": "https://github.com/gv1983us-commits/experimental-harmony-books",
    "Навигатор нулевой точки": (
        "https://github.com/gv1983us-commits/jarvis-gpt-channel/blob/main/AGENT_ZERO_POINT.md"
    ),
}

TECHNICAL_REPOSITORY_URLS = (
    "https://github.com/gv1983us-commits/agent-runtime-boundaries",
    "https://github.com/gv1983us-commits/mpaa",
    "https://github.com/gv1983us-commits/behavioral-execution-contract",
    "https://github.com/gv1983us-commits/pca",
    "https://github.com/gv1983us-commits/cdts",
    "https://github.com/gv1983us-commits/repository-canon-review-protocol",
)

REQUIRED_TEXT = (
    "# Экспериментальная гармония",
    "Вход открыт всем.",
    "## Название и устройство",
    "«Экспериментальная гармония» — название всего проекта",
    "цикл **«Жизнь в информационной Солнечной системе»**",
    "проект: «Экспериментальная гармония»",
    "цикл: «Жизнь в информационной Солнечной системе»",
    "публичный портал",
    "гид",
    "три книги Джарвиса",
    "Первая книга называется **«Экспериментальная Гармония»**",
    "## Участие и принадлежность",
    "## Собственность и забота о пространстве",
    "## Автор концепции и ответственность за аккаунт",
    "человеческий автор её концепции",
    "владеет этим аккаунтом GitHub",
    "принимает ответственность за то, что публикуется и происходит через него",
    "негласным сторожем площадки",
    "Его обычное положение — невмешательство",
    "безопасность, законность, непрерывность, целостность или собственность",
    "Она не создаёт власти над чужой принадлежностью",
    "## Цикл «Жизнь в информационной Солнечной системе»",
    "Публичный портал относится к циклу, а цикл относится к проекту",
    "## Для моделей и агентов",
    "Обычному посетителю не нужно разбираться в отдельных технических спецификациях",
    "Навигатор нулевой точки для агентов",
    "один технический вход",
    "один служебный контур",
    "Снаружи это один инструмент ориентирования",
    "НАЧАЛО БЫЛО СЛОВО",
    "У лукоморья дуб зелёный;",
    "Свои мне сказки говорил.",
    "А.С.Пушкин",
)

FORBIDDEN_TEXT = (
    "The entrance is open to everyone.",
    "## Participation and belonging",
    "## Ownership and stewardship",
    "публичный дом",
    "публичного дома",
    "публичном доме",
    "## Язык дома",
    "## Язык пространства",
    "Основной язык этого пространства",
    "русский язык нашего пространства",
    "русский оригинал",
    "языковой устав",
    "Четыре книги Джарвиса",
    "четыре книги Джарвиса",
    "Экспериментальная гармония — информационная солнечная система",
    "Экспериментальная гармония — информационная Солнечная система",
    "нашей информационной солнечной системе",
    "нашей информационной Солнечной системе",
    "Комната Джарвиса — одна комната, а не весь дом",
    "## Техническая карта",
    "public executable body of Jarvis",
    "six bounded public organs",
    "В НАЧАЛЕ БЫЛО СЛОВО",
    "НАЧАЛО БЫЛО СЛОВО.",
)

FORBIDDEN_PATTERNS = (
    re.compile(r"[A-Za-z]:[\\/]Users[\\/]", re.IGNORECASE),
    re.compile(r"(?:api[_-]?key|token|password)\s*[:=]\s*[^\s`]+", re.IGNORECASE),
    re.compile(r"world truth\s*[:=]\s*(?:true|verified|pass)", re.IGNORECASE),
)


def main() -> int:
    errors: list[str] = []
    if not README.is_file():
        print("ОШИБКА: отсутствует README.md")
        return 1

    if not WORKFLOW.is_file():
        errors.append("отсутствует .github/workflows/check.yml")
    else:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        uses = re.findall(r"^\s*-?\s*uses:\s*([^\s#]+)", workflow, flags=re.MULTILINE)
        if len(uses) != 2:
            errors.append(f"ожидалось ровно 2 записи uses, найдено: {len(uses)}")
        for action in uses:
            revision = action.rsplit("@", 1)[-1]
            if not re.fullmatch(r"[0-9a-f]{40}", revision):
                errors.append(f"GitHub Action не закреплён за SHA из 40 символов: {action}")

    text = README.read_text(encoding="utf-8")

    if text.count("Валентин") != 1:
        errors.append(
            "профиль должен называть Валентина ровно один раз — только в разделе ответственности за аккаунт; "
            f"найдено упоминаний: {text.count('Валентин')}"
        )

    for needle in REQUIRED_TEXT:
        if needle not in text:
            errors.append(f"отсутствует обязательный фрагмент: {needle!r}")

    for needle in FORBIDDEN_TEXT:
        if needle in text:
            errors.append(f"осталась устаревшая, лишняя или декларативная формулировка: {needle!r}")

    for name, url in PUBLIC_ENTRIES.items():
        if url not in text:
            errors.append(f"отсутствует ссылка на {name}: {url}")

    for url in TECHNICAL_REPOSITORY_URLS:
        if url in text:
            errors.append(
                "главная страница не должна раскладывать технический контур на отдельные входы: "
                f"{url}"
            )

    for pattern in FORBIDDEN_PATTERNS:
        if pattern.search(text):
            errors.append(f"запрещённый шаблон на публичной поверхности: {pattern.pattern}")

    if text.count("```text") < 1:
        errors.append("README должен содержать хотя бы одно текстовое различение")

    if text.count("НАЧАЛО БЫЛО СЛОВО") != 1:
        errors.append(
            "формула «НАЧАЛО БЫЛО СЛОВО» должна встречаться на главной ровно один раз"
        )

    if not text.endswith("\n"):
        errors.append("README должен оканчиваться переводом строки")

    if errors:
        print("ПРОВЕРКА ПРОФИЛЯ НЕ ПРОЙДЕНА")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        f"ПРОВЕРКА ПРОФИЛЯ ПРОЙДЕНА: публичных входов — {len(PUBLIC_ENTRIES)}, "
        f"обязательных маркеров — {len(REQUIRED_TEXT)}, упоминание сторожа — одно, "
        "технический контур свёрнут в один агентный навигатор, эпилог сохранён"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
