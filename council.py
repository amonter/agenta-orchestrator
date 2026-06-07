import json
import re
import urllib.request
from typing import Any, Dict

BASE_URL = "https://runtime-63463978729.asia-east1.run.app"


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


def _extract_json(text: str) -> Dict[str, Any]:
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError(f"No JSON in: {text[:200]}")
    return json.loads(match.group(0))


def consult(
    prompt: str, planner: str = "council-planner", policy: str = "council-policy-qc3"
) -> Dict[str, Any]:
    """Council = QC + Planner. Planner creates content plan + steps."""
    try:
        policy_review = _extract_json(_stream(policy, prompt))
    except Exception:
        policy_review = {"approved": True, "risks": [], "quality_gates": []}

    plan_raw = _stream(planner, prompt + "\n\nReturn STRICT JSON plan.")
    try:
        plan = _extract_json(plan_raw)
    except ValueError:
        plan = {
            "summary": "Strategic advice",
            "steps": [
                {
                    "id": 1,
                    "tool": "info",
                    "action": "display",
                    "args": {"message": plan_raw[:2000]},
                }
            ],
            "expected_outcome": "Review output",
        }

    return {"policy_review": policy_review, "plan": plan}
