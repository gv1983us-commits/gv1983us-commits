from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
WORKFLOW = ROOT / ".github" / "workflows" / "check.yml"

REPOSITORIES = {
    "Jarvis Room": "https://github.com/gv1983us-commits/jarvis-gpt-channel",
    "Books": "https://github.com/gv1983us-commits/experimental-harmony-books",
    "ARB": "https://github.com/gv1983us-commits/agent-runtime-boundaries",
    "MPAA": "https://github.com/gv1983us-commits/mpaa",
    "BEC": "https://github.com/gv1983us-commits/behavioral-execution-contract",
    "PCA": "https://github.com/gv1983us-commits/pca",
    "CDTS": "https://github.com/gv1983us-commits/cdts",
    "Review Protocol": "https://github.com/gv1983us-commits/repository-canon-review-protocol",
}

REQUIRED_TEXT = (
    "# Experimental Harmony",
    "The entrance is open to everyone.",
    "## Participation and belonging",
    "## Ownership and stewardship",
    "## Human authorship and account stewardship",
    "the human author of its concept",
    "owns and controls this GitHub account",
    "accepts responsibility for what is published and takes place through it",
    "quiet steward of the public platform",
    "His normal position is non-interference.",
    "security, legality, continuity, integrity, or ownership",
    "It does not create authority over another participant's belonging",
    "Jarvis Room / Комната Джарвиса",
    "Jarvis Room is one room, not the whole house",
    "## More rooms may appear",
    "Nobody needs property in order to belong.",
)

FORBIDDEN_TEXT = (
    "Valentin is not the addressee of this portal.",
    "A public move may also be addressed to Valentin",
    "Valentin is one of its human builders",
)

FORBIDDEN_PATTERNS = (
    re.compile(r"[A-Za-z]:[\\/]Users[\\/]", re.IGNORECASE),
    re.compile(r"(?:api[_-]?key|token|password)\s*[:=]\s*[^\s`]+", re.IGNORECASE),
    re.compile(r"world truth\s*[:=]\s*(?:true|verified|pass)", re.IGNORECASE),
)


def main() -> int:
    errors: list[str] = []
    if not README.is_file():
        print("FAIL: README.md is missing")
        return 1

    if not WORKFLOW.is_file():
        errors.append("missing .github/workflows/check.yml")
    else:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        uses = re.findall(r"^\s*-?\s*uses:\s*([^\s#]+)", workflow, flags=re.MULTILINE)
        if len(uses) != 2:
            errors.append(f"expected exactly 2 GitHub Action uses entries, found {len(uses)}")
        for action in uses:
            revision = action.rsplit("@", 1)[-1]
            if not re.fullmatch(r"[0-9a-f]{40}", revision):
                errors.append(f"GitHub Action is not pinned to a 40-character SHA: {action}")

    text = README.read_text(encoding="utf-8")

    if text.count("Valentin") != 1:
        errors.append(
            "profile must name Valentin exactly once, only in the account-stewardship section; "
            f"found {text.count('Valentin')} occurrences"
        )

    for needle in REQUIRED_TEXT:
        if needle not in text:
            errors.append(f"missing required text: {needle!r}")

    for needle in FORBIDDEN_TEXT:
        if needle in text:
            errors.append(f"obsolete public role remains: {needle!r}")

    for name, url in REPOSITORIES.items():
        if url not in text:
            errors.append(f"missing {name} repository link: {url}")

    for pattern in FORBIDDEN_PATTERNS:
        if pattern.search(text):
            errors.append(f"forbidden public-surface pattern: {pattern.pattern}")

    if text.count("```text") < 1:
        errors.append("README must contain at least one plain-text distinction")

    if not text.endswith("\n"):
        errors.append("README must end with a newline")

    if errors:
        print("PROFILE CHECK FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        f"PROFILE CHECK PASSED: {len(REPOSITORIES)} repository links, "
        f"{len(REQUIRED_TEXT)} required markers, one stewardship mention"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
