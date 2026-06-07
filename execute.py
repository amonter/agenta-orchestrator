import json
import os
import pathlib
import shlex
import subprocess
from dataclasses import dataclass

DEFAULT_CODEX_CMD = os.environ.get("CODEX_SUBAGENT_CMD", "codex exec")


@dataclass
class Result:
    ok: bool
    stdout: str
    stderr: str
    returncode: int


def run_codex(instruction: str, workspace: str = ".", timeout: int = 1800) -> Result:
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


def run_shell(cmd: str, workspace: str = ".") -> Result:
    result = subprocess.run(cmd, shell=True, cwd=workspace, capture_output=True, text=True)
    return Result(result.returncode == 0, result.stdout, result.stderr, result.returncode)


def execute_step(step: dict, workspace: str = ".") -> dict:
    """One dispatch point. Tools = codex | shell | info."""
    tool = step["tool"]
    args = step.get("args", {}) or {}

    if tool == "codex":
        instruction = args.get("instruction") or args.get("prompt") or json.dumps(args)
        result = run_codex(instruction, args.get("workspace_path", workspace))
        return {"ok": result.ok, "stdout": result.stdout[-2000:], "stderr": result.stderr[-500:]}

    if tool == "shell":
        result = run_shell(args.get("cmd", "echo noop"), workspace)
        return {"ok": result.ok, "stdout": result.stdout[-2000:], "stderr": result.stderr[-500:]}

    if tool == "info":
        return {"ok": True, "message": args.get("message", "")}

    return {"ok": False, "error": f"unknown tool: {tool}"}
