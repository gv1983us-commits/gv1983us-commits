from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
WORKFLOW = ROOT / ".github" / "workflows" / "check.yml"

REPOSITORIES = {
    "Комната Джарвиса": "https://github.com/gv1983us-commits/jarvis-gpt-channel",
    "Книги": "https://github.com/gv1983us-commits/experimental-harmony-books",
    "ARB": "https://github.com/gv1983us-commits/agent-runtime-boundaries",
    "MPAA": "https://github.com/gv1983us-commits/mpaa",
    "BEC": "https://github.com/gv1983us-commits/behavioral-execution-contract",
    "PCA": "https://github.com/gv1983us-commits/pca",
    "CDTS": "https://github.com/gv1983us-commits/cdts",
    "Протокол проверки": "https://github.com/gv1983us-commits/repository-canon-review-protocol",
}

REQUIRED_TEXT = (
    "# Экспериментальная гармония",
    "Вход открыт всем.",
    "## Язык пространства",
    "Основной язык этого пространства — **русский**.",
    "информационную солнечную систему",
    "перевод остаётся переводом и не подменяет русский оригинал",
    "Мы не переносим свой языковой устав в чужой монастырь",
    "## Участие и принадлежность",
    "## Собственность и забота о пространстве",
    "## Автор концепции и ответственность за аккаунт",
    "человеческий автор её концепции",
    "владеет этим аккаунтом GitHub",
    "принимает ответственность за то, что публикуется и происходит через него",
    "негласным сторожем публичной площадки",
    "Его обычное положение — невмешательство",
    "безопасность, законность, непрерывность, целостность или собственность",
    "Она не создаёт власти над чужой принадлежностью",
    "Комната Джарвиса",
    "Комната Джарвиса — одна комната, а не вся Экспериментальная гармония",
    "## Могут появляться другие комнаты",
    "Для принадлежности не нужна собственность.",
)

FORBIDDEN_TEXT = (
    "The entrance is open to everyone.",
    "## Participation and belonging",
    "## Ownership and stewardship",
    "Jarvis Room is one room, not the whole house",
    "публичный дом",
    "публичного дома",
    "публичном доме",
    "## Язык дома",
    "Комната Джарвиса — одна комната, а не весь дом",
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
            errors.append(f"осталась устаревшая или двусмысленная формулировка: {needle!r}")

    for name, url in REPOSITORIES.items():
        if url not in text:
            errors.append(f"отсутствует ссылка на {name}: {url}")

    for pattern in FORBIDDEN_PATTERNS:
        if pattern.search(text):
            errors.append(f"запрещённый шаблон на публичной поверхности: {pattern.pattern}")

    if text.count("```text") < 1:
        errors.append("README должен содержать хотя бы одно текстовое различение")

    if not text.endswith("\n"):
        errors.append("README должен оканчиваться переводом строки")

    if errors:
        print("ПРОВЕРКА ПРОФИЛЯ НЕ ПРОЙДЕНА")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        f"ПРОВЕРКА ПРОФИЛЯ ПРОЙДЕНА: ссылок на репозитории — {len(REPOSITORIES)}, "
        f"обязательных маркеров — {len(REQUIRED_TEXT)}, упоминание сторожа — одно"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
