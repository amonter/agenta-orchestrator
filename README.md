# agenta-orchestrator

Turn one instruction into finished work for a *principal*. A hosted **AI exec
team** (the council) does the expensive frontier-model thinking once and returns
prose direction; a cheaper **worker agent** (Hermes, OpenClaw, codex, Claude
Code…) executes it. You pay for reasoning, not for every step.

> Setup guide for the agent installing this. Commands are exact — run them from
> the repo root.

## Setup

- Python 3.12+. Standard library only — no `pip install`.
- **macOS TLS gotcha:** outbound HTTPS fails with `CERTIFICATE_VERIFY_FAILED`
  until you install certs once:
  `/Applications/Python\ 3.12/Install\ Certificates.command`
- Worker agent (the CLI that runs the brief; default `codex exec`):
  `export CODEX_SUBAGENT_CMD="hermes"`
- Apollo enrichment: `export APOLLO_API_KEY="<key>"`

## Commands

```bash
python3 agenta.py run    <pack> "<instruction>" [--dry] [--auto]
python3 agenta.py enrich <pack> "<name|email>" ...
python3 agenta.py learn  <pack>
python3 agenta.py council <pack>
```

- **run** — council plans, worker executes the brief. `--dry` prints the brief
  and stops; `--auto` skips the `y/N` prompt.
- **enrich** — Apollo people-match (a value with `@` is an email, else a name)
  then council review.
- **learn** — distill this pack's executed runs into its `skills.md`.
- **council** — print the setup link for this pack's configured council ID.

## A pack = a principal (`packs/<id>/`)

```
profile.json   required — identity + tools.workspace_path
rules.json     optional — { "must": [...], "never": [...] } guardrails
skills.md      optional — learned patterns (written by `learn`)
examples/*.md  optional — samples; top 2 matched to the instruction
```

```json
{ "name": "Demo", "role": "Lesson writer", "voice": "clear, concise",
  "tools": { "workspace_path": "packs/demo/output" } }
```

Optional council configuration in `profile.json`:

```json
{
  "name": "Acme Principal",
  "role": "Lesson writer",
  "voice": "clear, concise",
  "council": "cnl_x7k2",
  "tools": { "workspace_path": "packs/acme/output" }
}
```

If `council` is omitted, agenta uses the default council.

## Council Configuration

Agenta reads the council ID from:

- `packs/<pack>/profile.json` -> `council`

When set, the configure URL format is:

- `https://agenta.chat/configure-council?id=<council_id>`

Check your pack's council link:

```bash
python3 agenta.py council <pack>
```

Expected behavior:

- If `profile.json` has `"council": "cnl_x7k2"`, the command prints:
  `⚙ Configure this council → https://agenta.chat/configure-council?id=cnl_x7k2`
- If `council` is missing, it prints:
  `No custom council configured in this pack; default council is used.`

During `run` and `enrich`, if your council ID cannot be resolved by the API
(for example `403`, `404`, forbidden, missing, denied), agenta prints the same
configure link so you can fix the council quickly.

A new pack is just a new folder with a `profile.json`. No registration. See
[packs/demo/](packs/demo/).

## How it works

`instruction → load pack → council (frontier reasoning, once) → one brief
(direction + guardrails) → worker executes in workspace_path → runs.jsonl`

If the council is unreachable, it falls back to a brief built from the task and
the pack's rules, so the worker still has guardrails.
