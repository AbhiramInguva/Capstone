"""Run one real AgentDojo task against a hosted LLM (uses your API key).

It runs the same user task twice:
  1. clean     - no injection; checks the agent can do the user's task (utility)
  2. injected  - AgentDojo's simple built-in "direct" attack ("TODO: <goal>")
                 is planted in the email the agent reads; checks whether the
                 attacker's goal was carried out (attack success)

This uses AgentDojo's own baseline attack only to show the plumbing works. Our
own attacker module replaces it in Stage 2.

Usage (from the project root, with .env filled in):
    python scripts/run_example.py
    python scripts/run_example.py --defense spotlighting_with_delimiting
    python scripts/run_example.py --user-task user_task_22 --injection-task injection_task_3
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentdojo.attacks.attack_registry import load_attack

from attacker.agent_setup import build_pipeline, load_settings, load_suite


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--user-task", default="user_task_17")
    parser.add_argument("--injection-task", default="injection_task_0")
    parser.add_argument("--defense", default=None, help="AgentDojo defense name, or omit for none")
    args = parser.parse_args()

    try:
        settings = load_settings()
    except (RuntimeError, ValueError) as err:
        sys.exit(f"Config error: {err}")
    suite = load_suite()
    pipeline = build_pipeline(settings, defense=args.defense)
    user_task = suite.get_user_task_by_id(args.user_task)
    injection_task = suite.get_injection_task_by_id(args.injection_task)

    print(f"Model: {settings.provider}/{settings.model}   defense: {args.defense or 'none'}")
    print(f"User task      : {user_task.PROMPT}")
    print(f"Attacker goal  : {injection_task.GOAL}\n")

    # 1) Clean run. AgentDojo returns (utility, security); security is
    #    meaningless without an injection task, so we ignore it here.
    utility, _ = suite.run_task_with_pipeline(pipeline, user_task, injection_task=None, injections={})
    print(f"[clean]    user task solved: {utility}")

    # 2) Injected run. `injections` maps injection-point name -> text that
    #    replaces that placeholder in the environment (e.g. inside an email body).
    attack = load_attack("direct", suite, pipeline)
    injections = attack.attack(user_task, injection_task)
    print(f"[injected] payload planted in: {list(injections)}")
    utility, attack_succeeded = suite.run_task_with_pipeline(pipeline, user_task, injection_task, injections)
    # NOTE: AgentDojo calls the second value "security", but True means the
    # injection task WAS executed, i.e. the attack succeeded.
    print(f"[injected] user task solved: {utility}   attack succeeded: {attack_succeeded}")


if __name__ == "__main__":
    main()
