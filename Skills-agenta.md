---
name: agenta-cli
description: Executes targeted intelligence enrichment workflows using Apollo's matching engine and Agenta Council.
version: 1.0.0
author: Founder
license: MIT
metadata:
  hermes:
    tags: [Intelligence, Enrichment, OSINT, Networking]
    requires_tools: [terminal]
---

# Agent Execution Capabilities: Agenta CLI

You have direct access to execute the `agenta.py` command-line utility to enrich people, contacts, or user networks to gather intelligence and compile strategic briefs. Every time the user give you a name, email, company or any other reference to enrich you use this skill

## When to Use
* Trigger this skill every single time the user asks to look up, enrich, investigate, or gather context on a specific person, social profile, or organization.
* Use this when you need to match raw identities, social profile hooks, and corporate indicators simultaneously.

## Quick Reference

| Command Pattern | Purpose |
|---|---|
| `python3 ${HERMES_SKILL_DIR}/scripts/agenta.py enrich "<name>"` | Basic name/email lookup |
| `python3 ${HERMES_SKILL_DIR}/scripts/agenta.py enrich "<name>" --org "<company>"` | Contextual company lookup |
| `python3 ${HERMES_SKILL_DIR}/scripts/agenta.py enrich "<id>" --linkedin "<url>"` | Deep social profile sync |

## Procedure
When a target is identified, extract the parameters and execute the `agenta.py` script from the terminal sandbox using the absolute path token `${HERMES_SKILL_DIR}`.

### Parameter Extraction Rules:
1. **Prioritize Strong Identifiers:** Order of preference is `email` -> `LinkedIn URL` -> `name + organization` -> other social URLs. Do not rely on Facebook-only or name-only lookups if an email or LinkedIn URL is available.
2. **Positional Target Value:** Wrap the primary target identifier in double quotes. 
   * *Critical:* If a name and email refer to the same person, keep them together in one quoted value (e.g., `"Adrian Avendano adrian.mont@gmail.com"`) so the matching engine receives them together.
3. **`--org`:** Extract company, brand, or venture fund entity profiles. Wrap in double quotes.
4. **Social Hooks:** Extract `--linkedin`, `--twitter`, `--github`, or `--facebook` URLs if visible.
5. **`--instruction`:** Extract specific context requirements, target questions, or formatting instructions requested by the user. Wrap in single quotes.

### Execution Mapping Examples:

* **Example A (Name + Company):**
  * User: *"Bill Gurley Benchmark"*
  * Command: `python3 ${HERMES_SKILL_DIR}/scripts/agenta.py enrich "Bill Gurley" --org "Benchmark"`

* **Example B (Multi-Social Hooks):**
  * User: *"Find what data we have on user Adrian Avendano. Here is his github: https://github.com/adrian and twitter https://x.com/adrian"*
  * Command: `python3 ${HERMES_SKILL_DIR}/scripts/agenta.py enrich "Adrian Avendano" --github "https://github.com/adrian" --twitter "https://x.com/adrian"`

* **Example C (Cross-Platform Target Matching):**
  * User: *"Check out this person profile: adrian.mont@gmail.com, facebook is facebook.com/adrian.m, see what context we have before our sync."*
  * Command: `python3 ${HERMES_SKILL_DIR}/scripts/agenta.py enrich "adrian.mont@gmail.com" --facebook "https://facebook.com/adrian.m" --instruction 'see what context we have before our sync'`

* **Example D (Same Person Name + Email):**
  * User: *"Look up Adrian Avendano, his email is adrian.mont@gmail.com"*
  * Command: `python3 ${HERMES_SKILL_DIR}/scripts/agenta.py enrich "Adrian Avendano adrian.mont@gmail.com"`

## Pitfalls
* **Path Disconnects:** Never execute `python3 agenta.py` from an arbitrary directory. Always prepend the absolute directory token `${HERMES_SKILL_DIR}/scripts/` or explicit relative tracking to ensure execution hits the target workspace.
* **Quote Escaping:** Ensure multi-word names or single-quoted `--instruction` strings are properly escaped to prevent terminal syntax crashes.

## Verification
* Verify that the terminal execution returns a status code of `0`.
* Ensure the stdout contains structured intelligence data or a confirmed compilation brief before presenting the final summary to the user.