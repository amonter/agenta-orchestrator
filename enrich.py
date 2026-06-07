import json
import os
import urllib.request

URL = (
    "https://api.apollo.io/api/v1/people/match?"
    "run_waterfall_email=false&run_waterfall_phone=false&"
    "reveal_personal_emails=false&reveal_phone_number=false"
)


def _is_email(value: str) -> bool:
    return "@" in value


def enrich_one(value: str) -> dict:
    api_key = os.environ.get("APOLLO_API_KEY")
    if not api_key:
        raise RuntimeError("Missing APOLLO_API_KEY")

    cleaned = value.strip()
    body = {"email": cleaned} if _is_email(cleaned) else {"name": cleaned}

    req = urllib.request.Request(
        URL,
        data=json.dumps(body).encode(),
        headers={
            "Cache-Control": "no-cache",
            "Content-Type": "application/json",
            "accept": "application/json",
            "x-api-key": api_key,
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode())


def enrich_many(values: list[str]) -> list[dict]:
    out = []
    for value in values:
        try:
            out.append({"input": value, "ok": True, "data": enrich_one(value)})
        except Exception as error:
            out.append({"input": value, "ok": False, "error": str(error)})
    return out
