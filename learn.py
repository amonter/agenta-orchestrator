import json
import pathlib

from council import _stream

RUNS = pathlib.Path("runs.jsonl")

DISTILL_PROMPT = """You analyze an agent's execution history for one principal.
From the runs below, extract DURABLE PATTERNS the agent should remember:
- What worked (style, structure, choices)
- What failed (avoid)
- Principal's revealed preferences

Output a CONCISE markdown doc (max 40 lines) titled "# Learned Skills".
No fluff. Bullet points. Action-oriented."""


def distill(pack_id: str) -> None:
    """Read runs.jsonl filtered for pack_id, write packs/<id>/skills.md"""
    if not RUNS.exists():
        return

    runs = []
    for line in RUNS.read_text().splitlines():
        try:
            run = json.loads(line)
            if run.get("pack_id") == pack_id and run.get("status") == "executed":
                runs.append(
                    {
                        "summary": run["plan"]["summary"],
                        "outcomes": [o.get("result", {}) for o in run.get("outcomes", [])],
                    }
                )
        except Exception:
            continue

    if not runs:
        print(f"No runs to learn from for {pack_id}")
        return

    payload = DISTILL_PROMPT + "\n\nRUNS:\n" + json.dumps(runs[-20:], indent=2)
    skills = _stream("council-planner", payload)
    output = pathlib.Path(f"packs/{pack_id}/skills.md")
    output.write_text(skills)
    print(f"\u2713 Updated {output} ({len(runs)} runs distilled)")
