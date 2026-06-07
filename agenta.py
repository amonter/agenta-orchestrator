import argparse
import json
import pathlib
import time

from context import load_pack, to_council_prompt
from council import consult
from execute import execute_plan, plan_to_brief
from enrich import enrich_many
from learn import distill

RUNS = pathlib.Path("runs.jsonl")
G, Y, R, B, D, X = "\033[92m", "\033[93m", "\033[91m", "\033[94m", "\033[2m", "\033[0m"


def log(entry: dict) -> None:
    with RUNS.open("a") as file:
        file.write(json.dumps(entry) + "\n")


def run(pack_id: str, instruction: str, auto: bool = False, dry: bool = False) -> None:
    print(f"\n{B}[{pack_id}]{X} {instruction}")

    ctx = load_pack(pack_id, instruction)
    if ctx.get("error"):
        print(f"{R}\u2717 {ctx['error']}{X}")
        return

    workspace = ctx["profile"].get("tools", {}).get("workspace_path", f"packs/{pack_id}/output")
    print(f"{D}context: profile + rules + {len(ctx['examples'])} examples + skills{X}")

    prompt = to_council_prompt(ctx, instruction)
    result = consult(prompt, planner=ctx["profile"].get("planner", "council-planner"))
    plan = result["plan"]

    print(f"\n{B}\u2550\u2550\u2550 {plan.get('summary', 'direction')} \u2550\u2550\u2550{X}")
    if plan.get("guidance"):
        print(f"{D}{plan['guidance']}{X}")

    if not result["policy_review"].get("approved", True):
        print(f"{R}\u2717 rejected by policy{X}")
        if result["policy_review"].get("notes"):
            print(f"{D}{result['policy_review']['notes']}{X}")
        log({"ts": time.time(), "pack_id": pack_id, "status": "rejected", **result})
        return

    if dry:
        print(f"\n{D}\u2500\u2500\u2500 brief (dry, not sent to agent) \u2500\u2500\u2500{X}")
        print(plan_to_brief(plan, instruction, ctx.get("rules")))
        return

    if not auto and input(f"{Y}execute? [y/N]: {X}").lower() != "y":
        return

    outcome = execute_plan(plan, instruction, workspace=workspace, rules=ctx.get("rules"))
    icon = G + "\u2713" + X if outcome.get("ok") else R + "\u2717" + X
    print(f"  {icon} agent finished (rc={outcome.get('returncode')})")
    if outcome.get("stdout"):
        print(outcome["stdout"])

    log(
        {
            "ts": time.time(),
            "pack_id": pack_id,
            "instruction": instruction,
            "plan": plan,
            "outcomes": [{"result": outcome}],
            "status": "executed",
        }
    )
    print(f"{G}\u2713 done. output in {workspace}/{X}\n")


def enrich_and_consult(pack_id: str, values: list[str]) -> None:
    ctx = load_pack(pack_id, "Apollo enrichment review")
    if ctx.get("error"):
        print(f"{R}\u2717 {ctx['error']}{X}")
        return

    apollo = enrich_many(values)

    instruction = "Review Apollo person-match data and produce further enrichment guidance."
    prompt = to_council_prompt(ctx, instruction) + "\n\nAPOLLO_JSON:\n" + json.dumps(apollo, indent=2)
    result = consult(prompt, planner=ctx["profile"].get("planner", "council-planner"))

    print(json.dumps(result, indent=2))
    log(
        {
            "ts": time.time(),
            "pack_id": pack_id,
            "status": "enrich_consult",
            "inputs": values,
            "apollo": apollo,
            "council": result,
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="agenta")
    subparsers = parser.add_subparsers(dest="cmd")

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("pack")
    run_parser.add_argument("instruction", nargs="+")
    run_parser.add_argument("--auto", action="store_true")
    run_parser.add_argument("--dry", action="store_true")

    learn_parser = subparsers.add_parser("learn")
    learn_parser.add_argument("pack")

    enrich_parser = subparsers.add_parser("enrich")
    enrich_parser.add_argument("pack")
    enrich_parser.add_argument("values", nargs="+")

    args = parser.parse_args()
    if args.cmd == "run":
        run(args.pack, " ".join(args.instruction), auto=args.auto, dry=args.dry)
    elif args.cmd == "learn":
        distill(args.pack)
    elif args.cmd == "enrich":
        enrich_and_consult(args.pack, args.values)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
