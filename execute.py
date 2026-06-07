import os
import pathlib
import shlex
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

DEFAULT_CODEX_CMD = os.environ.get("CODEX_SUBAGENT_CMD", "codex exec")


@dataclass
class Result:
    ok: bool
    stdout: str
    stderr: str
    returncode: int


def run_codex(instruction: str, workspace: str = ".", timeout: int = 1800) -> Result:
    """Hand a natural-language brief to the autonomous coding agent and let it work."""
    workspace_path = pathlib.Path(workspace).expanduser().resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)
    cmd = shlex.split(DEFAULT_CODEX_CMD) + [instruction]
    result = subprocess.run(
        cmd,
        cwd=str(workspace_path),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return Result(result.returncode == 0, result.stdout, result.stderr, result.returncode)


def plan_to_brief(
    plan: Dict[str, Any],
    instruction: str,
    rules: Optional[Dict[str, Any]] = None,
) -> str:
    """Flatten the council's direction into ONE natural-language brief.

    The council gives high-level prose direction, not commands to dispatch.
    The agent reads the whole brief and decides how to carry it out with its
    own tools — we don't run each step as a rigid function call.
    """
    parts: List[str] = [f"TASK:\n{instruction}"]

    if plan.get("guidance"):
        parts.append(
            "DIRECTION (from your planning council — high-level, adapt as you see fit):\n"
            + plan["guidance"]
        )
    elif plan.get("summary"):
        parts.append(f"APPROACH (from your planning council):\n{plan['summary']}")

    if rules:
        must = rules.get("must") or []
        never = rules.get("never") or []
        if must or never:
            guard = ["GUARDRAILS (the principal's standing rules — always honor these):"]
            guard += [f"  MUST: {r}" for r in must]
            guard += [f"  NEVER: {r}" for r in never]
            parts.append("\n".join(guard))

    return "\n\n".join(parts)


def execute_plan(
    plan: Dict[str, Any],
    instruction: str,
    workspace: str = ".",
    rules: Optional[Dict[str, Any]] = None,
    timeout: int = 1800,
) -> Dict[str, Any]:
    """Compose the plan into one brief and delegate the whole thing to the agent."""
    brief = plan_to_brief(plan, instruction, rules)
    result = run_codex(brief, workspace, timeout)
    return {
        "ok": result.ok,
        "returncode": result.returncode,
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-1000:],
        "brief": brief,
    }
