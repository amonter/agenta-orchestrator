# agenta-orchestrator

A lightweight **agent orchestrator** that lets a capable coding agent act on
behalf of a *principal* — without micromanaging it.

The idea: don't hard-code workflows as rigid function calls. Instead, load the
principal's context (who they are, their rules, examples of their good work),
ask a planning **council** for high-level direction, fold that into a single
natural-language **brief**, and hand the whole thing to an autonomous coding
agent that decides how to execute. Every run is logged and can be **distilled**
back into reusable skills.

```
instruction
    │
    ▼
load_pack ──► profile + rules + examples + learned skills   (context.py)
    │
    ▼
council ────► policy review (safe? on-policy?)               (council.py)
              planner (high-level prose direction)
    │
    ▼
plan_to_brief ─► one natural-language brief + guardrails      (execute.py)
    │
    ▼
agent (codex) ─► executes freely with its own tools           (execute.py)
    │
    ▼
runs.jsonl ───► distilled into packs/<id>/skills.md           (learn.py)
```

## Design principles

- **Direction, not dispatch.** The council returns *prose guidance*, not a rigid
  step list. The orchestrator never runs steps as hard-coded functions — it
  delegates the whole task to the agent in one brief.
- **Context packs as identity.** Everything that makes the agent act like a
  specific principal lives in `packs/<id>/`.
- **Guardrails travel with the work.** A pack's `must` / `never` rules are
  appended to every brief.
- **Learn from history.** Executed runs are distilled into `skills.md`, which
  feeds back into future context.

## Files

| File | Role |
|------|------|
| [agenta.py](agenta.py) | CLI entry point: `run`, `enrich`, `learn` |
| [context.py](context.py) | Loads a pack and builds the council prompt; keyword example retrieval |
| [council.py](council.py) | Policy review + planner; returns high-level prose direction |
| [execute.py](execute.py) | Composes the brief and delegates the task to the coding agent |
| [enrich.py](enrich.py) | Apollo person-match enrichment (by name or email) |
| [learn.py](learn.py) | Distills `runs.jsonl` into a pack's `skills.md` |

## Packs

A pack is a folder under `packs/<id>/` describing one principal:

```
packs/demo/
├── profile.json        # name, role, voice, planner, tools.workspace_path
├── lesson_rules.json   # { "must": [...], "never": [...] } guardrails
├── skills.md           # learned patterns (written by `learn`)
└── examples/           # *.md samples of good work (keyword-retrieved)
```

Only `profile.json` is required; everything else is optional and merged in when
present. See [packs/demo/](packs/demo/) for a working example.

## Commands

```bash
# Preview the brief the agent would receive — no execution:
python3 agenta.py run demo "write a short lesson on gravity" --dry

# Full run: council plans, agent executes the brief autonomously.
# Drop --auto to get a [y/N] confirmation before executing.
python3 agenta.py run demo "write a short lesson on gravity" --auto

# Apollo enrichment + council review of the results:
export APOLLO_API_KEY="your_key"
python3 agenta.py enrich demo "John Doe" "jane@acme.com"

# Distill executed runs for a pack into packs/demo/skills.md:
python3 agenta.py learn demo
```

## Requirements

- **Python 3.12+** (standard library only — no pip dependencies).
- An autonomous coding agent on your PATH for the execute step. Defaults to
  `codex exec`; override with `CODEX_SUBAGENT_CMD`.
- The council calls a hosted runtime (`BASE_URL` in [council.py](council.py));
  if it's unreachable the orchestrator degrades gracefully and still produces a
  brief from the task and rules.

## Environment variables

| Variable | Used by | Purpose |
|----------|---------|---------|
| `APOLLO_API_KEY` | `enrich` | Apollo.io API key for person-match |
| `CODEX_SUBAGENT_CMD` | `run` | Command used to invoke the coding agent (default `codex exec`) |

## Output

- Executed runs are appended to `runs.jsonl` in the working directory.
- Agent output lands in the pack's `tools.workspace_path` (e.g.
  `packs/demo/output/`).
