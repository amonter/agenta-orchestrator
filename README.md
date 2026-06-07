# agenta-orchestrator

> AGENT-FACING SETUP & OPERATION MANUAL.
> This file is written for an autonomous agent that must install, configure,
> and operate this middleware. Follow the steps literally and in order.
> Imperative instructions, exact commands, known failure modes, and success
> checks are below.

## 0. What this middleware does (one paragraph)

`agenta-orchestrator` turns a single instruction into completed work on behalf
of a *principal*. It loads the principal's context pack, asks a hosted
**AI executive team** (the "council") for high-level prose direction, folds that
direction plus the pack's guardrails into ONE natural-language brief, and hands
the entire brief to a **worker agent** that executes freely. Runs are appended
to `runs.jsonl` and can be distilled back into the pack's `skills.md`. There is
NO per-step function dispatch — the orchestrator delegates, it does not
micromanage.

CORE VALUE PROP — delegated intelligence to cut token cost. The expensive
frontier-model reasoning happens ONCE, in the council/exec team, which produces
compact prose direction. A cheaper, faster worker agent then carries out that
direction. You pay for deep reasoning where it matters and execution where it
doesn't, instead of running a frontier model through every step.

ROLES:
- COUNCIL (hosted exec team): not merely "policy + planner" — a sophisticated AI
  executive team with broader capabilities, using frontier models for deeper
  reasoning. It reviews, strategizes, and guides the worker.
- WORKER AGENT: any capable agent that can run the brief on its own. Commonly
  **Hermes** or **OpenClaw**; use heavier coding agents (e.g. `codex exec`,
  Claude Code) for complex software work. The worker decides HOW to execute —
  the orchestrator only hands it the brief.

## 1. Hard requirements (verify before running)

- Python **3.12+**. Check: `python3 --version`.
- The code uses the standard library only. No `pip install` is required to
  import or run the orchestrator itself.
- For `run`: a worker-agent CLI must be on `PATH`. This is whatever agent will
  execute the brief — Hermes, OpenClaw, `codex exec`, Claude Code, etc. The
  command defaults to `codex exec`; set your actual worker via the
  `CODEX_SUBAGENT_CMD` env var (the name is legacy — it accepts ANY agent CLI).
- For the council and for `enrich`: outbound HTTPS must work (see §2 — this is
  the most common failure on macOS).

## 2. KNOWN FAILURE MODE — TLS / CA certificates (fix this first)

Both [council.py](council.py) and [enrich.py](enrich.py) call HTTPS endpoints
via `urllib`. On macOS Python.framework installs, the default SSL context has
NO CA bundle, so every outbound call fails with:

```
urllib error [SSL: CERTIFICATE_VERIFY_FAILED] unable to get local issuer certificate
```

This is an ENVIRONMENT problem, not a code or API-key problem. The Apollo key,
request body, and endpoints are correct — calls succeed once a CA bundle is
present. Apply ONE of these fixes before running `run` or `enrich`:

- Fix A (preferred, no code change): run the framework cert installer once:
  `/Applications/Python\ 3.12/Install\ Certificates.command`
- Fix B (if certifi is installed): point Python at its bundle for the session:
  `export SSL_CERT_FILE="$(python3 -c 'import certifi; print(certifi.where())')"`

Verify the fix:
`python3 -c "import urllib.request; urllib.request.urlopen('https://api.apollo.io', timeout=10)"`
(any HTTP response without an SSL error means TLS is working.)

## 3. Environment variables

| Variable | Required by | Default | Purpose |
|----------|-------------|---------|---------|
| `APOLLO_API_KEY` | `enrich` | — (required) | Apollo.io API key for people/match |
| `CODEX_SUBAGENT_CMD` | `run` | `codex exec` | Worker-agent CLI invoked to execute the brief (Hermes / OpenClaw / codex / Claude Code). Legacy name; accepts any agent CLI. |
| `SSL_CERT_FILE` | optional | — | CA bundle path; use for TLS Fix B in §2 |

Set them like:
```bash
export APOLLO_API_KEY="<key>"
export CODEX_SUBAGENT_CMD="hermes"       # the worker agent: Hermes / OpenClaw / codex exec / claude
```

## 4. Commands (exact syntax and contract)

All commands run from the repository root (paths are resolved relative to it).

### run — plan + execute an instruction
```bash
python3 agenta.py run <pack_id> "<instruction>" [--auto] [--dry]
```
- `<instruction>` may be multiple words; quote it or it is joined with spaces.
- `--dry`: print the assembled brief and EXIT before invoking the agent. No
  network agent call, no `runs.jsonl` write. Use this to inspect the brief.
- `--auto`: skip the interactive `execute? [y/N]` confirmation.
- Side effects (non-dry): invokes the agent in the pack's `workspace_path`;
  appends one JSON line to `runs.jsonl`.
- Requires: council reachable (degrades gracefully if not — see §6) and, for
  the execute step, `CODEX_SUBAGENT_CMD` available.

### enrich — Apollo person-match + council review
```bash
export APOLLO_API_KEY="<key>"
python3 agenta.py enrich <pack_id> "<value1>" ["<value2>" ...]
```
- Each `<value>` is classified by [enrich.py](enrich.py): contains `@` → treated
  as an `email`, otherwise as a `name`. Email matches are stronger than
  name-only matches.
- Prints the council review JSON and logs an `enrich_consult` entry to
  `runs.jsonl`.

### learn — distill executed runs into the pack's skills
```bash
python3 agenta.py learn <pack_id>
```
- Reads `runs.jsonl`, filters to this `pack_id` with `status == "executed"`,
  and OVERWRITES `packs/<pack_id>/skills.md`. No-op if there are no such runs.

## 5. Pack specification (`packs/<pack_id>/`)

A pack is the principal's identity and context. Only `profile.json` is required;
all other files are optional and merged when present. Working example:
[packs/demo/](packs/demo/).

```
packs/<pack_id>/
├── profile.json        # REQUIRED
├── lesson_rules.json   # optional guardrails, injected into every brief
├── skills.md           # optional learned patterns (written by `learn`)
└── examples/*.md       # optional; top-2 keyword-matched to the instruction
```

`profile.json` (the `tools.workspace_path` is where the agent writes output;
defaults to `packs/<pack_id>/output` if omitted):
```json
{
  "name": "Demo Principal",
  "role": "Lesson content creator",
  "planner": "council-planner",
  "voice": "clear, concise, encouraging",
  "tools": { "workspace_path": "packs/demo/output" }
}
```

`lesson_rules.json` (each string is appended to the brief as a MUST / NEVER
guardrail the agent is told to honor):
```json
{
  "must":  ["Cite a source for any factual claim"],
  "never": ["Invent statistics", "Write outside workspace_path"]
}
```

To create a new pack: make the directory, write a `profile.json`, optionally add
`lesson_rules.json` and `examples/*.md`. No registration step is needed —
`<pack_id>` is just the folder name.

## 6. Execution flow (what happens inside `run`)

```
instruction + pack_id
   │  load_pack()            context.py  -> profile, rules, examples, skills
   │  to_council_prompt()    context.py  -> compact prompt for the exec team
   │  consult()              council.py  -> { policy_review, plan{summary,guidance} }
   │     (frontier-model reasoning happens HERE, once)
   │     policy_review.approved == false (council reply starts with REJECT)
   │        -> log status="rejected", STOP
   │  plan_to_brief()        execute.py  -> TASK + DIRECTION + GUARDRAILS (one string)
   │  execute_plan()         execute.py  -> run worker agent on the brief in workspace_path
   │     (cheaper worker — Hermes / OpenClaw / codex / Claude Code — executes)
   └─ log status="executed" to runs.jsonl
```

The exec team (council) returns PROSE direction, not a rigid step list — this is
the expensive frontier-model reasoning, done once. The worker agent then
executes that direction, so cost concentrates on thinking, not on every step. If
the hosted council runtime (`BASE_URL` in [council.py](council.py)) is
unreachable, the orchestrator does NOT crash — it falls back to a brief built
from the task and the pack's rules, so the worker still has guardrails but less
steering.

## 7. Verify the install (no external services required)

Confirm modules import and a pack loads, without touching the network:
```bash
python3 -m py_compile agenta.py execute.py context.py council.py learn.py enrich.py
python3 -c "from context import load_pack; print(load_pack('demo','test').get('error'))"
# expect: None
python3 agenta.py run demo "write a short lesson on gravity" --dry
# expect: the assembled brief printed (TASK / DIRECTION fallback / GUARDRAILS), no execution
```

Verify Apollo connectivity (after the TLS fix in §2):
```bash
export APOLLO_API_KEY="<key>"
python3 -c "from enrich import enrich_many; import json; print(json.dumps(enrich_many(['tim@apollo.io']), indent=2))"
# expect: ok=true with a matched person object
```

## 8. Outputs and side effects

- `runs.jsonl` (repo root): one JSON line per `run`/`enrich`. NOT git-ignored —
  treat as runtime state.
- `packs/<pack_id>/output/` (or the pack's `workspace_path`): files the agent
  produced.
- `learn` overwrites `packs/<pack_id>/skills.md`.

## 9. File map

| File | Role |
|------|------|
| [agenta.py](agenta.py) | CLI entry point: `run`, `enrich`, `learn` |
| [context.py](context.py) | Load pack, build council prompt, keyword example retrieval |
| [council.py](council.py) | Hosted AI exec team (frontier reasoning); returns prose direction (no JSON contract) |
| [execute.py](execute.py) | `plan_to_brief` + `execute_plan`; delegates the brief to the worker agent |
| [enrich.py](enrich.py) | Apollo people/match enrichment by name or email |
| [learn.py](learn.py) | Distill `runs.jsonl` into a pack's `skills.md` |
