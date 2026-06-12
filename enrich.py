import json
import os
import re
import urllib.request

URL = (
    "https://api.apollo.io/api/v1/people/match?"
    "run_waterfall_email=false&run_waterfall_phone=false&"
    "reveal_personal_emails=false&reveal_phone_number=false"
)

# Pure Python .env loader - no external libraries needed
if os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                # Clean up whitespace and quotes around the token
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                os.environ[key] = val


EMAIL_RE = re.compile(r"[\w.!#$%&'*+/=?^`{|}~-]+@[\w.-]+\.[A-Za-z]{2,}")


def _name_fields(name: str) -> dict:
    normalized = " ".join(name.split())
    fields = {"name": normalized}
    parts = normalized.split()
    if len(parts) >= 2:
        fields["first_name"] = parts[0]
        fields["last_name"] = parts[-1]
    return fields


def _target_fields(value: str) -> dict:
    cleaned = value.strip()
    email_match = EMAIL_RE.search(cleaned)
    if not email_match:
        return _name_fields(cleaned)

    email = email_match.group(0)
    name = (cleaned[: email_match.start()] + cleaned[email_match.end() :]).strip()
    body = {"email": email}
    if name:
        body.update(_name_fields(name))
    return body


def enrich_one(
    value: str | None = None,
    *,
    org: str | None = None,
    linkedin: str | None = None,
    twitter: str | None = None,
    github: str | None = None,
    facebook: str | None = None,
) -> dict:
    api_key = os.environ.get("APOLLO_API_KEY")
    if not api_key:
        raise RuntimeError("Missing APOLLO_API_KEY")

    body = {}
    if value and value.strip():
        body.update(_target_fields(value))
    if org:
        body["organization_name"] = org
    if linkedin:
        body["linkedin_url"] = linkedin
    if twitter:
        body["twitter_url"] = twitter
    if github:
        body["github_url"] = github
    if facebook:
        body["facebook_url"] = facebook

    if not body:
        raise ValueError("At least one enrichment target value or profile flag is required")

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


def enrich_many(
    values: list[str],
    *,
    org: str | None = None,
    linkedin: str | None = None,
    twitter: str | None = None,
    github: str | None = None,
    facebook: str | None = None,
) -> list[dict]:
    values = values or [None]
    out = []
    for value in values:
        try:
            out.append(
                {
                    "input": value,
                    "ok": True,
                    "data": enrich_one(
                        value,
                        org=org,
                        linkedin=linkedin,
                        twitter=twitter,
                        github=github,
                        facebook=facebook,
                    ),
                }
            )
        except Exception as error:
            out.append({"input": value, "ok": False, "error": str(error)})
    return out
