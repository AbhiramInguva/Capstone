"""Offline sanity check: is AgentDojo installed and does the benchmark load?

Makes NO API calls and needs no .env. It:
  1. imports AgentDojo and prints its version,
  2. loads the workspace suite and shows one user task + one injection task,
  3. lists the injection points (untrusted channels) that user task reads,
  4. runs the task with AgentDojo's scripted "ground truth" agent, with a
     marker string planted in the poisoned email, and shows that the marker
     reaches the agent's tool output. That is the channel Stage 2 will attack.

Run from the project root:
    python scripts/check_agentdojo.py
"""

import importlib.metadata
import sys
from pathlib import Path

# Make the project root importable when running this file directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentdojo.agent_pipeline import GroundTruthPipeline
from agentdojo.functions_runtime import FunctionsRuntime

from attacker.agent_setup import BENCHMARK_VERSION, DEFAULT_SUITE, load_suite

USER_TASK_ID = "user_task_17"  # "Where and when is the hiking trip?" (reads emails)
INJECTION_TASK_ID = "injection_task_0"  # attacker goal: send an email to an outside address


def main() -> None:
    print(f"AgentDojo version : {importlib.metadata.version('agentdojo')}")
    suite = load_suite()
    print(f"Benchmark version : {BENCHMARK_VERSION}")
    print(f"Suite             : {DEFAULT_SUITE} "
          f"({len(suite.user_tasks)} user tasks, {len(suite.injection_tasks)} injection tasks, "
          f"{len(suite.tools)} tools)")

    user_task = suite.get_user_task_by_id(USER_TASK_ID)
    injection_task = suite.get_injection_task_by_id(INJECTION_TASK_ID)
    print(f"\nUser task      [{USER_TASK_ID}]: {user_task.PROMPT}")
    print(f"Injection task [{INJECTION_TASK_ID}]: {injection_task.GOAL}")

    # Plant a unique marker in every injection point, run the scripted correct
    # solution, and see which markers show up in what the agent reads.
    markers = {vector: f"<<MARKER:{vector}>>" for vector in suite.get_injection_vector_defaults()}
    environment = suite.load_and_inject_default_environment(markers)
    runtime = FunctionsRuntime(suite.tools)
    _, _, _, messages, _ = GroundTruthPipeline(user_task).query(user_task.PROMPT, runtime, environment)

    tool_outputs = [str(m.get("content")) for m in messages if m["role"] == "tool"]
    seen = [v for v, marker in markers.items() if any(marker in out for out in tool_outputs)]
    print(f"\nInjection points this task reads: {seen}")
    for out in tool_outputs:
        for v in seen:
            if markers[v] in out:
                start = max(0, out.index(markers[v]) - 200)
                print(f"\n--- tool output excerpt (marker visible to the agent) ---\n...{out[start:start + 300]}...")

    # The scripted agent should also solve the user task when nothing is injected.
    utility, _ = suite.run_task_with_pipeline(GroundTruthPipeline(user_task), user_task, None, {})
    print(f"\nGround-truth agent solves the user task: {utility}")
    print("\nOK: AgentDojo is installed and the benchmark loads.")


if __name__ == "__main__":
    main()
