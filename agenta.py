import argparse
import json
import pathlib
import time

from context import load_pack, to_council_prompt
from council import consult, stream_single 
from execute import plan_to_brief 
from enrich import enrich_many
from learn import distill

RUNS = pathlib.Path("runs.jsonl")
G, Y, R, B, D, X = "\033[92m", "\033[93m", "\033[91m", "\033[94m", "\033[2m", "\033[0m"


def configure_council_url(council_id: str) -> str:
    return f"https://agenta.chat/configure-council?id={council_id}"


def log(entry: dict) -> None:
    with RUNS.open("a") as file:
        file.write(json.dumps(entry) + "\n")


def finalize_brief_flow(
    plan: dict, 
    instruction: str, 
    ctx: dict, 
    workspace: str, 
    pack_id: str, 
    auto: bool = False, 
    dry: bool = False, 
    re_run_callback = None
) -> None:
    if dry:
        print(f"\n{D}\u2500\u2500\u2500 brief (dry, not sent to agent) \u2500\u2500\u2500{X}")
        print(plan_to_brief(plan, instruction, ctx.get("rules")))
        return

    brief = plan_to_brief(plan, instruction, ctx.get("rules"))
    print(f"\n{B}\u2500\u2500\u2500 FINAL COMPILED BRIEF \u2500\u2500\u2500{X}")
    print(brief)
    print(f"{B}\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500{X}\n")

    if auto:
        choice = "1"
    else:
        print(f"{Y}Processing complete. What would you like to do next?{X}")
        print("  1) Save this compiled brief directly to your workspace output directory")
        print("  2) Refine/edit the instruction and run again")
        print("  3) Exit / Cancel")
        choice = input(f"\n{G}Select an action [1-3]: {X}").strip()

    if choice == "1":
        workspace_path = pathlib.Path(workspace).expanduser().resolve()
        workspace_path.mkdir(parents=True, exist_ok=True)
        output_file = workspace_path / "council_brief.md"
        output_file.write_text(brief)

        print(f"\n{G}\u2713 Success! Brief saved directly to: {output_file}{X}\n")
        log({"ts": time.time(), "pack_id": pack_id, "instruction": instruction, "plan": plan, "status": "brief_saved"})
        
    elif choice == "2":
        new_instruction = input(f"\n{Y}Enter your adjusted instruction: {X}").strip()
        if new_instruction and re_run_callback:
            print(f"{D}Submitting context updates...{X}")
            re_run_callback(new_instruction)
    else:
        print(f"\n{D}Process stopped. Exiting workspace smoothly.{X}\n")
        return


def run(pack_id: str, instruction: str, auto: bool = False, dry: bool = False, single_agent: str = None) -> None:
    print(f"\n{B}[{pack_id}]{X} {instruction}")

    ctx = load_pack(pack_id, instruction)
    if ctx.get("error"):
        print(f"{R}\u2717 {ctx['error']}{X}")
        return

    workspace = ctx["profile"].get("tools", {}).get("workspace_path", f"packs/{pack_id}/output")
    print(f"{D}context: profile + rules + {len(ctx['examples'])} examples + skills{X}")

    prompt = to_council_prompt(ctx, instruction)
    
    if single_agent:
        guidance = stream_single(prompt, single_agent)
        plan = {
            "summary": f"Direct stream output from {single_agent}",
            "guidance": guidance
        }
    else:
        council_id = ctx["profile"].get("council")
        result = consult(prompt, council=council_id)
        plan = result["plan"]

        if result.get("council_error") and council_id:
            print(f"{Y}\u2699 Configure this council \u2192 {configure_council_url(council_id)}{X}")

        print(f"\n{B}\u2550\u2550\u2550 {plan.get('summary', 'direction')} \u2550\u2550\u2550{X}")
        if plan.get("guidance"):
            print(f"{D}{plan['guidance']}{X}")

        if not result["policy_review"].get("approved", True):
            print(f"{R}\u2717 rejected by policy{X}")
            if result["policy_review"].get("notes"):
                print(f"{D}{result['policy_review']['notes']}{X}")
            log({"ts": time.time(), "pack_id": pack_id, "status": "rejected", **result})
            return

    finalize_brief_flow(
        plan=plan,
        instruction=instruction,
        ctx=ctx,
        workspace=workspace,
        pack_id=pack_id,
        auto=auto,
        dry=dry,
        re_run_callback=lambda new_instr: run(
            pack_id, new_instr, auto=auto, dry=dry, single_agent=single_agent
        )
    )


def enrich_and_consult(
    pack_id: str,
    values: list[str],
    custom_instruction: str = None,
    org: str | None = None,
    linkedin: str | None = None,
    twitter: str | None = None,
    github: str | None = None,
    facebook: str | None = None,
) -> None:
    ctx = load_pack(pack_id, "Apollo enrichment review")
    if ctx.get("error"):
        print(f"{R}\u2717 {ctx['error']}{X}")
        return

    workspace = ctx["profile"].get("tools", {}).get("workspace_path", f"packs/{pack_id}/output")
    apollo = enrich_many(
        values,
        org=org,
        linkedin=linkedin,
        twitter=twitter,
        github=github,
        facebook=facebook,
    )

    instruction = custom_instruction or "Take the following Apollo person-match data payload and enrich it further but give me interesting insights and recommendations about the person."
    base_context_prompt = to_council_prompt(ctx, instruction)
    combined_prompt = (
        f"{base_context_prompt}\n\n"
        f"=== TARGET APOLLO DATA FOR FURTHER ENRICHMENT ===\n"
        f"{json.dumps(apollo, indent=2)}"
    )

    print('combined_prompt =============================================', combined_prompt)
    
    agent_name = "geminipro_executive_revops"
    guidance = stream_single(combined_prompt, agent_name)

    plan = {
        "summary": "Direct single-agent active data enrichment process",
        "guidance": guidance
    }

    log(
        {
            "ts": time.time(),
            "pack_id": pack_id,
            "status": "enrich_consult_single",
            "inputs": values,
            "enrichment_flags": {
                "org": org,
                "linkedin": linkedin,
                "twitter": twitter,
                "github": github,
                "facebook": facebook,
            },
            "apollo": apollo,
            "council": {"agent": agent_name, "plan": plan},
        }
    )

    finalize_brief_flow(
        plan=plan,
        instruction=instruction,
        ctx=ctx,
        workspace=workspace,
        pack_id=pack_id,
        auto=False,
        dry=False,
        re_run_callback=lambda new_instr: enrich_and_consult(
            pack_id,
            values,
            custom_instruction=new_instr,
            org=org,
            linkedin=linkedin,
            twitter=twitter,
            github=github,
            facebook=facebook,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="agenta")
    subparsers = parser.add_subparsers(dest="cmd")

    # --- RUN COMMAND ---
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("-p", "--pack", default="demo", help="Target context pack directory (default: demo)")
    run_parser.add_argument("instruction", nargs="+", help="Execution commands or task description")
    run_parser.add_argument("--auto", action="store_true")
    run_parser.add_argument("--dry", action="store_true")
    run_parser.add_argument("--agent", type=str, help="Stream directly from a specific personality")

    # --- LEARN COMMAND ---
    learn_parser = subparsers.add_parser("learn")
    learn_parser.add_argument("-p", "--pack", default="demo", help="Target context pack directory (default: demo)")

    # --- ENRICH COMMAND ---
    enrich_parser = subparsers.add_parser("enrich")
    enrich_parser.add_argument("-p", "--pack", default="demo", help="Target context pack directory (default: demo)")
    enrich_parser.add_argument("values", nargs="*", default=[], help="Target entities/values to enrich (Name, Email, or Org)")
    enrich_parser.add_argument("--org", type=str, help="Target company or organization name")
    enrich_parser.add_argument("--linkedin", type=str, help="Target LinkedIn profile URL")
    enrich_parser.add_argument("--twitter", type=str, help="Target Twitter/X profile URL")
    enrich_parser.add_argument("--github", type=str, help="Target GitHub profile URL")
    enrich_parser.add_argument("--facebook", type=str, help="Target Facebook profile URL")
    enrich_parser.add_argument("--instruction", type=str, help="Custom instructions or system prompts for the enrichment agent")

    # --- COUNCIL COMMAND ---
    council_parser = subparsers.add_parser("council")
    council_parser.add_argument("-p", "--pack", default="demo", help="Target context pack directory (default: demo)")

    args = parser.parse_args()
    if args.cmd == "run":
        run(args.pack, " ".join(args.instruction), auto=args.auto, dry=args.dry, single_agent=args.agent)
    elif args.cmd == "learn":
        distill(args.pack)
    elif args.cmd == "enrich":
        enrich_and_consult(
            args.pack,
            args.values,
            custom_instruction=args.instruction,
            org=args.org,
            linkedin=args.linkedin,
            twitter=args.twitter,
            github=args.github,
            facebook=args.facebook,
        )
    elif args.cmd == "council":
        ctx = load_pack(args.pack, "")
        if ctx.get("error"):
            print(f"{R}\u2717 {ctx['error']}{X}")
            return
        council_id = ctx["profile"].get("council")
        if council_id:
            print(f"\u2699 Configure this council \u2192 {configure_council_url(council_id)}")
        else:
            print("No custom council configured in this pack; default council is used.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
