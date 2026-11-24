"""Load versioned Dossier v2 prompt files from disk."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts" / "dossier_v2"
_CACHE: Dict[str, str] = {}


class PromptNotFound(RuntimeError):
    pass


def load_prompt(name: str, **variables: Any) -> str:
    """Load ``name.md`` and substitute {variable} placeholders."""
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise PromptNotFound(f"Missing prompt file: {path}")
    if name not in _CACHE:
        _CACHE[name] = path.read_text(encoding="utf-8")
    template = _CACHE[name]
    safe = {key: value if isinstance(value, str) else _json(value) for key, value in variables.items()}
    try:
        return template.format(**safe)
    except KeyError as exc:
        raise ValueError(f"Prompt {name} is missing variable {exc}") from exc


def _json(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, default=str)


def prompt_version(section: str) -> str:
    return f"{section}@v1"
