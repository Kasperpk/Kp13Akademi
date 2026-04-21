"""Loader for Anthropic-style Agent Skills under `skills/` at the repo root.

A skill lives in `skills/<name>/` with a top-level `SKILL.md` (YAML frontmatter
+ markdown body) and optional `references/` files loaded on demand.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parents[2] / "skills"


def _strip_frontmatter(text: str) -> str:
    """Return SKILL.md body without the leading YAML frontmatter block."""
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    if end == -1:
        return text
    return text[end + 4:].lstrip("\n")


@lru_cache(maxsize=32)
def load_skill(name: str) -> str:
    """Return the body of `skills/<name>/SKILL.md` (frontmatter stripped).

    Raises FileNotFoundError if the skill is missing.
    """
    path = SKILLS_ROOT / name / "SKILL.md"
    return _strip_frontmatter(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=64)
def load_reference(skill: str, ref: str) -> str:
    """Return the contents of `skills/<skill>/references/<ref>`.

    `ref` may be provided with or without the `.md` suffix.
    """
    if not ref.endswith(".md"):
        ref = f"{ref}.md"
    path = SKILLS_ROOT / skill / "references" / ref
    return path.read_text(encoding="utf-8")
