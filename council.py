import json
import re
import urllib.request
from typing import Any, Dict

BASE_URL = "https://runtime-63463978729.asia-east1.run.app"

POLICY_SUFFIX = (
    "\n\nYou are the policy reviewer. Briefly judge whether this is safe and "
    "on-policy. Note any real risks in one or two sentences. If it absolutely "
    "must NOT proceed, start your reply with the word REJECT and say why. "
    "Otherwise just give your notes — no JSON, no checklist."
)

PLANNER_SUFFIX = (
    "\n\nYou are the planner. Give HIGH-LEVEL direction for how to approach "
    "this: the key moves, what a great result looks like, and pitfalls to "
    "avoid. Write a short prose brief, not a rigid step-by-step checklist — "
    "the executing agent is capable and will decide the exact steps itself."
)


def _stream(personality: str, user_input: str) -> str:
    payload = {
        "personality_name": personality,
        "user_input": user_input,
        "user_id": "hermes@local",
        "needs_memory": False,
    }
    req = urllib.request.Request(
        BASE_URL + "/chat/stream",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    chunks = []
    with urllib.request.urlopen(req, timeout=180) as response:
        for line in response.read().decode(errors="replace").splitlines():
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break
                chunks.append(data)
    return "".join(chunks)


def _looks_rejected(text: str) -> bool:
    return bool(re.search(r"\bREJECT\b", text, re.IGNORECASE))


def _first_line(text: str) -> str:
    for line in text.splitlines():
        line = line.strip().lstrip("#").strip()
        if line:
            return line[:200]
    return "Strategic direction"


def consult(
    prompt: str, planner: str = "council-planner", policy: str = "council-policy-qc3"
) -> Dict[str, Any]:
    """Council = policy QC + planner. Both answer in natural language.

    We keep the planner's prose as high-level *direction*, not a rigid plan.
    The executing agent reads it and decides how to act.
    """
    try:
        policy_text = _stream(policy, prompt + POLICY_SUFFIX)
        policy_review = {
            "approved": not _looks_rejected(policy_text),
            "notes": policy_text.strip()[:2000],
        }
    except Exception as error:
        policy_review = {"approved": True, "notes": f"(policy review unavailable: {error})"}

    try:
        guidance = _stream(planner, prompt + PLANNER_SUFFIX).strip()
    except Exception as error:
        guidance = f"(planner unavailable: {error}) Proceed using the task and rules directly."

    return {
        "policy_review": policy_review,
        "plan": {"summary": _first_line(guidance), "guidance": guidance},
    }
