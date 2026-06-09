import json
import re
import urllib.request
import ssl  # Ensure this is at the top of council.py
from typing import Any, Dict
from urllib.error import HTTPError

BASE_URL = "https://runtime-server-63463978729.us-central1.run.app"


def _looks_rejected(text: str) -> bool:
    return bool(re.search(r"\bREJECT\b", text, re.IGNORECASE))


def _first_line(text: str) -> str:
    for line in text.splitlines():
        line = line.strip().lstrip("#").strip()
        if line:
            return line[:200]
    return "Strategic direction"


def _is_council_resolution_error(error_text: str) -> bool:
    pattern = r"\b(403|404|forbidden|unauthorized|not found|missing|denied)\b"
    return bool(re.search(pattern, error_text, re.IGNORECASE))


def consult(prompt: str, council: str | None = None) -> Dict[str, Any]:
    """Hits the /council/runtime endpoint executing a Multi-Model Council."""
    # Order matters here so we can reliably index the responses list
    policy_member = "gptoss20b_universal"
    planner_member = "gpt54mini_universal"

    payload = {
        "user_input": prompt,
        "user_id": "hermes@local",
        "conversation_id": None,
        "members": [policy_member, planner_member],  # Ordered council members
        "mode": "default",
        "needs_memory": False,
    }

    if council:
        payload["council"] = council

    req = urllib.request.Request(
        f"{BASE_URL}/council/runtime",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    # --- FIX: Safe Initialization outside the Try Block ---
    council_error = None
    context = ssl._create_unverified_context()

    try:
        with urllib.request.urlopen(req, timeout=180, context=context) as response:
            response_data = json.loads(response.read().decode(errors="replace"))

            if "error" in response_data:
                raise RuntimeError(response_data["error"])

            raw_responses = response_data.get("responses", [])

            # Extract text safely checking for the backend's "response" key
            policy_obj = raw_responses[0] if len(raw_responses) > 0 else ""
            if isinstance(policy_obj, dict):
                # Try "response" first, then fall back to "text" or raw dump
                policy_text = policy_obj.get("response", policy_obj.get("text", json.dumps(policy_obj)))
            else:
                policy_text = str(policy_obj)

            planner_obj = raw_responses[1] if len(raw_responses) > 1 else ""
            if isinstance(planner_obj, dict):
                # Try "response" first, then fall back to "text" or raw dump
                guidance = planner_obj.get("response", planner_obj.get("text", json.dumps(planner_obj))).strip()
            else:
                guidance = str(planner_obj).strip()

            if not guidance and response_data.get("final"):
                guidance = response_data.get("final", "").strip()

    except HTTPError as error:
        detail = f"{error.code} {error.reason}"
        policy_text = f"(policy review unavailable: {detail})"
        guidance = (
            f"(planner unavailable: {detail}) Proceed using the task and rules directly."
        )
        if council and _is_council_resolution_error(detail):
            council_error = detail
    except Exception as error:
        detail = str(error)
        policy_text = f"(policy review unavailable: {detail})"
        guidance = (
            f"(planner unavailable: {detail}) Proceed using the task and rules directly."
        )
        if council and _is_council_resolution_error(detail):
            council_error = detail

    policy_review = {
        "approved": not _looks_rejected(policy_text),
        "notes": policy_text.strip()[:2000],
    }

    result = {
        "policy_review": policy_review,
        "plan": {"summary": _first_line(guidance), "guidance": guidance},
    }
    if council_error:
        result["council_error"] = council_error

    return result