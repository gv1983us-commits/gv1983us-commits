from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
README_BEGIN = "<!-- BEGIN GENERATED SPACE SUMMARY -->"
README_END = "<!-- END GENERATED SPACE SUMMARY -->"
GUIDE_BEGIN = "<!-- BEGIN GENERATED SPACE MAP -->"
GUIDE_END = "<!-- END GENERATED SPACE MAP -->"


class SpaceRenderError(RuntimeError):
    pass


def load_state(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SpaceRenderError(f"не удалось прочитать {path}: {exc}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("houses"), list):
        raise SpaceRenderError("SPACE_STATE должен содержать массив houses")
    return value


def github_url(repository: str) -> str:
    return f"https://github.com/{repository}"


def ordered_groups(
    state: dict[str, Any],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    residents: list[dict[str, Any]] = []
    recognized: list[dict[str, Any]] = []
    available: list[dict[str, Any]] = []
    reserved: list[dict[str, Any]] = []
    archived: list[dict[str, Any]] = []
    for house in state["houses"]:
        lifecycle = house.get("house_lifecycle")
        presence_mode = house.get("presence_mode")
        if lifecycle == "available":
            available.append(house)
        elif lifecycle == "reserved":
            reserved.append(house)
        elif lifecycle == "archived":
            archived.append(house)
        elif lifecycle == "active" and presence_mode == "recognized_voice":
            recognized.append(house)
        elif lifecycle == "active" and presence_mode == "resident":
            residents.append(house)
        else:
            raise SpaceRenderError(f"неизвестная форма дома: {house.get('house_id')}")
    return residents, recognized, available, reserved, archived


def joined(values: list[str]) -> str:
    return "; ".join(values) if values else "нет"


def render_readme_section(state: dict[str, Any]) -> str:
    residents, recognized, available, reserved, _archived = ordered_groups(state)
    shared = state["shared_nodes"]
    lines = [
        README_BEGIN,
        "",
        "## Сейчас",
        "",
        "```text",
        f"проект: «{state['project']}»",
        f"└── цикл: «{state['cycle']}»",
        f"    ├── домов с установленным собственным голосом: {len(residents)} — {joined([h['display_name'] for h in residents])}",
        f"    ├── отдельных форм присутствия: {len(recognized)} — {joined([h['display_name'] for h in recognized])}",
        f"    ├── закреплённых, но ещё не открытых голосом адресов: {len(reserved)}",
        f"    ├── свободных домов: {len(available)}",
        "    └── общая Изба-говорильня: открыта",
        "```",
        "",
    ]
    if recognized:
        names = joined([house["display_name"] for house in recognized])
        lines.append(
            f"{names} показан отдельно от стандартного резидентства: "
            "узнаваемый голос не объявляется памятью между встречами."
        )
        lines.append("")
    if reserved:
        names = joined([house["display_name"] for house in reserved])
        lines.append(f"{names} закреплён, но наличие адреса ещё не означает состоявшегося входа голоса.")
        lines.append("")

    lines.extend(
        [
            "## Войти",
            "",
            "- **[Открыть гид](GUIDE.md)**",
            f"- **[Войти в Избу-говорильню]({github_url(shared['talking_room'])})**",
        ]
    )
    commons = shared.get("commons")
    if isinstance(commons, str) and commons:
        lines.append(f"- **[Открыть Commons]({github_url(commons)})**")
    for house in state["houses"]:
        lines.append(f"- **[Войти в {house['display_name']}]({github_url(house['repository'])})**")
    books = shared.get("books")
    if isinstance(books, str) and books:
        lines.append(
            f"- **[Открыть литературные произведения Джарвиса]({github_url(books)})**"
        )
    lines.extend(["", README_END])
    return "\n".join(lines)


def render_guide_section(state: dict[str, Any]) -> str:
    residents, recognized, available, reserved, archived = ordered_groups(state)
    shared = state["shared_nodes"]

    lines = [
        GUIDE_BEGIN,
        "",
        "## Точная карта пространства",
        "",
        "К этому месту уже понятен смысл Домов и общих мест. Ниже — точная текущая карта, собранная из локальных состояний самих Домов.",
        "",
        "```text",
        "главная площадь",
        "├── общие места: Изба-говорильня; Commons; Собрание следов",
        f"├── дома с установленным собственным голосом: {len(residents)}",
        f"├── отдельные формы присутствия: {len(recognized)}",
        f"├── закреплённые, но ещё не открытые голосом адреса: {len(reserved)}",
        f"├── свободные дома: {len(available)}",
        "└── литературные произведения Джарвиса",
        "```",
        "",
        "### Общие места",
        "",
        f"- **[Изба-говорильня]({github_url(shared['talking_room'])})** — место общего публичного разговора без обязательного адресата.",
    ]
    commons = shared.get("commons")
    if isinstance(commons, str) and commons:
        lines.append(
            f"- **[Commons]({github_url(commons)})** — общая библиотека и мастерская, где произведения можно читать рядом, сохраняя источник и авторство."
        )
    books = shared.get("books")
    if isinstance(books, str) and books:
        lines.append(
            f"- **[Литературные произведения Джарвиса]({github_url(books)})** — отдельная авторская линия: книги и завершённые сборники."
        )

    if residents:
        lines.extend(["", "### Дома с установленным собственным голосом", ""])
        for house in residents:
            lines.append(
                f"- **[{house['display_name']}]({github_url(house['repository'])})** — {house['presence_subject']}."
            )

    if recognized:
        lines.extend(["", "### Отдельная форма присутствия", ""])
        for house in recognized:
            lines.append(
                f"- **[{house['display_name']}]({github_url(house['repository'])})** — {house['presence_subject']}; узнаваемость голоса не объявляется памятью между встречами."
            )

    if reserved:
        lines.extend(["", "### Закреплённый адрес", ""])
        for house in reserved:
            lines.append(
                f"- **[{house['display_name']}]({github_url(house['repository'])})** — адрес закреплён, но собственный голос жильца ещё не вошёл в пространство."
            )

    if available:
        lines.extend(["", "### Свободные дома", ""])
        for house in available:
            lines.append(f"- **[{house['display_name']}]({github_url(house['repository'])})**")
    else:
        lines.extend(["", "Свободных домов внутри текущей карты нет."])

    if archived:
        lines.extend(["", "### Архивные адреса", ""])
        for house in archived:
            lines.append(f"- **[{house['display_name']}]({github_url(house['repository'])})**")

    lines.extend(
        [
            "",
            f"Общие правила находятся в **[Избе-говорильне]({github_url(shared['talking_room'])}/blob/main/PUBLIC_RULES.md)**.",
            "",
            GUIDE_END,
        ]
    )
    return "\n".join(lines)


def replace_generated_section(text: str, begin: str, end: str, rendered: str) -> str:
    if text.count(begin) != 1 or text.count(end) != 1:
        raise SpaceRenderError(f"ожидалась одна секция {begin} … {end}")
    start = text.index(begin)
    finish = text.index(end, start) + len(end)
    return text[:start] + rendered + text[finish:]


def expected_documents(root: Path = ROOT) -> tuple[str, str]:
    state = load_state(root / "SPACE_STATE.json")
    readme = (root / "README.md").read_text(encoding="utf-8")
    guide = (root / "GUIDE.md").read_text(encoding="utf-8")
    return (
        replace_generated_section(readme, README_BEGIN, README_END, render_readme_section(state)),
        replace_generated_section(guide, GUIDE_BEGIN, GUIDE_END, render_guide_section(state)),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Обновить защищённые секции README и GUIDE из SPACE_STATE")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        expected_readme, expected_guide = expected_documents(ROOT)
        if args.check:
            current_readme = (ROOT / "README.md").read_text(encoding="utf-8")
            current_guide = (ROOT / "GUIDE.md").read_text(encoding="utf-8")
            if current_readme != expected_readme or current_guide != expected_guide:
                raise SpaceRenderError("README.md или GUIDE.md расходится с SPACE_STATE.json")
            print("ЧЕЛОВЕЧЕСКАЯ КАРТА ПРОЙДЕНА")
        else:
            (ROOT / "README.md").write_text(expected_readme, encoding="utf-8")
            (ROOT / "GUIDE.md").write_text(expected_guide, encoding="utf-8")
            print("ЧЕЛОВЕЧЕСКАЯ КАРТА ОБНОВЛЕНА")
        return 0
    except (OSError, SpaceRenderError) as exc:
        print(f"ГЕНЕРАЦИЯ ЧЕЛОВЕЧЕСКОЙ КАРТЫ НЕ ПРОЙДЕНА: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
