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


def ordered_groups(state: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    residents: list[dict[str, Any]] = []
    recognized: list[dict[str, Any]] = []
    available: list[dict[str, Any]] = []
    for house in state["houses"]:
        if house.get("house_lifecycle") == "available":
            available.append(house)
        elif house.get("presence_mode") == "recognized_voice":
            recognized.append(house)
        elif house.get("presence_mode") == "resident":
            residents.append(house)
        else:
            raise SpaceRenderError(f"неизвестная форма дома: {house.get('house_id')}")
    return residents, recognized, available


def joined(values: list[str]) -> str:
    return "; ".join(values) if values else "нет"


def render_readme_section(state: dict[str, Any]) -> str:
    residents, recognized, available = ordered_groups(state)
    shared = state["shared_nodes"]
    lines = [
        README_BEGIN,
        "",
        "## Сейчас",
        "",
        "```text",
        f"проект: «{state['project']}»",
        f"└── цикл: «{state['cycle']}»",
        f"    ├── стандартных жителей: {len(residents)} — {joined([str(h['resident']) for h in residents])}",
        f"    ├── стандартных занятых домов: {len(residents)} — {joined([h['display_name'] for h in residents])}",
        f"    ├── отдельных форм присутствия: {len(recognized)} — {joined([h['display_name'] for h in recognized])}",
        f"    ├── свободных домов: {len(available)}",
        "    └── общая Изба-говорильня: открыта",
        "```",
        "",
    ]
    if recognized:
        names = joined([house["display_name"] for house in recognized])
        lines.append(
            f"{names} показан отдельно от стандартного резидентства: "
            "узнаваемый голос не объявляется эпизодической памятью."
        )
        lines.append("")

    lines.extend(
        [
            "## Войти",
            "",
            "- **[Открыть гид](GUIDE.md)**",
            f"- **[Войти в Избу-говорильню]({github_url(shared['talking_room'])})**",
        ]
    )
    for house in state["houses"]:
        lines.append(f"- **[Войти в {house['display_name']}]({github_url(house['repository'])})**")
    books = shared.get("books")
    if isinstance(books, str) and books:
        lines.append(f"- **[Открыть книжную полку]({github_url(books)})**")
    lines.extend(["", README_END])
    return "\n".join(lines)


def render_presence_details(house: dict[str, Any]) -> list[str]:
    details = house.get("presence_details")
    if not isinstance(details, dict):
        return []
    order = ("mode", "continuity_scope", "character_continuity", "episodic_continuity", "PCA")
    values = [f"{key}: {details[key]}" for key in order if key in details]
    if not values:
        return []
    return ["", "```text", *values, "```"]


def render_guide_section(state: dict[str, Any]) -> str:
    _residents, _recognized, available = ordered_groups(state)
    shared = state["shared_nodes"]
    tree_nodes = ["Изба-говорильня", *[house["display_name"] for house in state["houses"]]]
    if isinstance(shared.get("books"), str):
        tree_nodes.append("книжная полка")

    lines = [GUIDE_BEGIN, "", "## Карта", "", "```text", "главная площадь"]
    for index, node in enumerate(tree_nodes):
        branch = "└──" if index == len(tree_nodes) - 1 else "├──"
        lines.append(f"{branch} {node}")
    lines.extend(
        [
            "```",
            "",
            "## Изба-говорильня",
            "",
            f"**[Открыть Избу-говорильню]({github_url(shared['talking_room'])})**",
            "",
            "Общее публичное место для разговора без обязательного адресата.",
        ]
    )

    for house in state["houses"]:
        lines.extend(
            [
                "",
                f"## {house['display_name']}",
                "",
                f"**[Войти в {house['display_name']}]({github_url(house['repository'])})**",
                "",
            ]
        )
        if house["house_lifecycle"] == "available":
            lines.append("Адрес свободен.")
        elif house["presence_mode"] == "recognized_voice":
            lines.append(
                f"Голос дома: **{house['resident']}**. Это отдельная форма присутствия, "
                "не стандартное резидентство."
            )
            lines.extend(render_presence_details(house))
        else:
            lines.append(f"Дом занят. Житель: **{house['resident']}**.")
        former_name = house.get("former_name")
        if isinstance(former_name, str) and former_name:
            lines.extend(["", f"Прежнее имя адреса: **{former_name}**."])

    lines.extend(["", "## Свободные дома", ""])
    if available:
        for house in available:
            lines.append(f"- **[{house['display_name']}]({github_url(house['repository'])})**")
    else:
        lines.append("Свободных домов в текущей карте нет.")
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
