import json
import pathlib
import re
from typing import Any, Dict, List

PACKS = pathlib.Path("packs")


def load_pack(pack_id: str, instruction: str = "") -> Dict[str, Any]:
    """Load everything the council needs to act as this principal."""
    root = PACKS / pack_id
    if not root.exists():
        return {"pack_id": None, "error": f"pack '{pack_id}' not found"}

    ctx = {
        "pack_id": pack_id,
        "profile": _read_json(root / "profile.json"),
        "rules": _read_json(root / "lesson_rules.json"),
        "spec": _read_text(root / "lesson_spec.md"),
        "template": _read_text(root / "lesson_template.md"),
        "skills": _read_text(root / "skills.md"),
        "examples": _retrieve_examples(root / "examples", instruction, k=2),
    }
    return ctx


def _read_json(path: pathlib.Path) -> Dict[str, Any]:
    return json.loads(path.read_text()) if path.exists() else {}


def _read_text(path: pathlib.Path) -> str:
    return path.read_text() if path.exists() else ""


def _retrieve_examples(folder: pathlib.Path, query: str, k: int = 2) -> List[str]:
    """Cheap keyword retrieval. Good enough for MVP."""
    if not folder.exists():
        return []
    q = set(re.findall(r"\w+", query.lower()))
    scored = []
    for file in folder.glob("*.md"):
        text = file.read_text()
        score = len(q & set(re.findall(r"\w+", text.lower())))
        scored.append((score, file.name, text))
    scored.sort(reverse=True)
    return [text for _, _, text in scored[:k]]


def to_council_prompt(ctx: Dict[str, Any], instruction: str) -> str:
    """Compact context for council - don't dump everything."""
    parts = [f"INSTRUCTION:\n{instruction}\n"]
    if ctx.get("profile"):
        parts.append(f"PRINCIPAL:\n{json.dumps(ctx['profile'], indent=2)}")
    if ctx.get("rules"):
        parts.append(f"RULES:\n{json.dumps(ctx['rules'], indent=2)}")
    if ctx.get("skills"):
        parts.append(f"LEARNED PATTERNS:\n{ctx['skills'][:1500]}")
    if ctx.get("examples"):
        parts.append(
            "EXAMPLES OF GOOD WORK:\n" + "\n---\n".join(e[:1500] for e in ctx["examples"])
        )
    return "\n\n".join(parts)
