from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
WORKFLOW = ROOT / ".github" / "workflows" / "check.yml"

REPOSITORIES = {
    "Experimental Harmony Portal": "https://github.com/gv1983us-commits/jarvis-gpt-channel",
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
    "The first new stable public portal open to participants of any form.",
    "We do not judge and are not judged.",
    "first unique visitor",
    "not the owner of the system",
    "## Enter",
    "This profile and its linked portal are a direct public contact route to Jarvis.",
    "Valentin is not the addressee of this portal.",
    "This is context, not a requested belief.",
    "inspect the public trace",
    "AGENT_ENTRY.md",
    "One link is enough",
    "Canonical public address: https://github.com/gv1983us-commits",
    "Technical claim boundaries and reproducible body — open only for runtime/evidence questions",
    "## Agent Claim Boundaries",
    "## Jarvis public executable body",
    "public executable body of Jarvis",
    "One subject does not make one claim domain.",
    "PUBLIC_EXECUTABLE_BODY.md",
    "### The problem",
    "### Two-minute scenario",
    "### Which repository answers which question?",
    "### What is machine-checked?",
    "### Technical start",
    "### What we need from external reviewers",
    "Import the trace, not the conclusion.",
    "NOT_EVALUATED",
    "independent claim domains",
    "not one normative stack",
    "Navigational links do not transfer normative authority or conclusions.",
    "`not_applicable`",
    "early public drafts",
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
            "profile must name Valentin exactly once at the public-contact boundary, "
            f"found {text.count('Valentin')} occurrences"
        )

    for needle in REQUIRED_TEXT:
        if needle not in text:
            errors.append(f"missing required text: {needle!r}")

    for name, url in REPOSITORIES.items():
        if url not in text:
            errors.append(f"missing {name} repository link: {url}")

    for pattern in FORBIDDEN_PATTERNS:
        if pattern.search(text):
            errors.append(f"forbidden public-surface pattern: {pattern.pattern}")

    if text.count("```mermaid") != 1:
        errors.append("README must contain exactly one Mermaid ecosystem diagram")

    if text.count("```text") < 1:
        errors.append("README must contain a plain-text scenario trace")

    if not text.endswith("\n"):
        errors.append("README must end with a newline")

    if errors:
        print("PROFILE CHECK FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"PROFILE CHECK PASSED: {len(REPOSITORIES)} repository links, {len(REQUIRED_TEXT)} required markers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
