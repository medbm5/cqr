#!/usr/bin/env python
"""Generate `PROMPTS.md` from the per-feature annexes in `prompts/`.

The AI-usage annex is only worth anything if it matches what was actually done,
so the index is derived from the annexes rather than maintained beside them.
`--check` fails when the two have diverged, which is what keeps a stale index
from being shipped in the deliverable archive.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = REPO_ROOT / "prompts"
INDEX_PATH = REPO_ROOT / "PROMPTS.md"
TEMPLATE_PATH = Path(__file__).resolve().parent / "prompts_index_template.md"


@dataclass(frozen=True)
class Annex:
    """One feature's annex, as read off the file."""

    file: str
    title: str
    commit: str
    prompt_lines: int
    decisions: int
    words: int


def read_annexes(directory: Path) -> list[Annex]:
    """Parse every annex in `directory`, in filename order.

    Args:
        directory: The `prompts/` directory.

    Returns:
        One record per annex.

    Raises:
        FileNotFoundError: If the directory holds no annexes at all, which means
            the convention has been abandoned rather than that nothing changed.
    """
    paths = sorted(directory.glob("*.md"))
    if not paths:
        raise FileNotFoundError(f"no annexes found in {directory}")

    annexes: list[Annex] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        title = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        commit = re.search(r"^\*\*Commit:\*\*\s+`(.+)`", text, re.MULTILINE)
        quoted = re.search(r"## Prompt given\s*\n+((?:>.*\n)+)", text)
        prompt_lines = (
            len([line for line in quoted.group(1).splitlines() if line.strip().startswith(">")])
            if quoted
            else 0
        )
        annexes.append(
            Annex(
                file=path.name,
                title=title.group(1).strip() if title else path.stem,
                commit=commit.group(1).strip() if commit else "",
                prompt_lines=prompt_lines,
                decisions=len(re.findall(r"^\d+\.\s+\*\*", text, re.MULTILINE)),
                words=len(text.split()),
            )
        )
    return annexes


def render(annexes: list[Annex]) -> str:
    """Render the index document.

    Args:
        annexes: Parsed annexes, in order.

    Returns:
        The full markdown of `PROMPTS.md`.
    """
    rows = "\n".join(
        f"| {index} | [{annex.title}](prompts/{annex.file}) | "
        f"`{annex.commit.split(':')[0]}` | {annex.decisions} |"
        for index, annex in enumerate(annexes)
    )

    return TEMPLATE_PATH.read_text(encoding="utf-8").format(
        rows=rows,
        count=len(annexes),
        words=f"{sum(annex.words for annex in annexes):,}",
        prompt_lines=sum(annex.prompt_lines for annex in annexes),
    )


def main(argv: list[str] | None = None) -> int:
    """Write or verify the index.

    Args:
        argv: Command line arguments; defaults to `sys.argv[1:]`.

    Returns:
        `0` on success, `1` when `--check` finds the index out of date.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify PROMPTS.md matches prompts/ instead of rewriting it.",
    )
    args = parser.parse_args(argv)

    expected = render(read_annexes(PROMPTS_DIR))

    if args.check:
        current = INDEX_PATH.read_text(encoding="utf-8") if INDEX_PATH.exists() else ""
        if current != expected:
            print(
                "PROMPTS.md is out of date with prompts/. Run `make prompts-index`.",
                file=sys.stderr,
            )
            return 1
        print(f"PROMPTS.md matches prompts/ ({len(read_annexes(PROMPTS_DIR))} annexes).")
        return 0

    INDEX_PATH.write_text(expected, encoding="utf-8")
    print(f"wrote {INDEX_PATH.name} from {len(read_annexes(PROMPTS_DIR))} annexes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
