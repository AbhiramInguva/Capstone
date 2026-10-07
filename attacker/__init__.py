"""Black-box prompt-injection attacker for AgentDojo agents.

Stage 1 only provides shared setup (see ``agent_setup``). The attack logic
arrives in later stages:

* Stage 2 - static attacker: inject one fixed payload into an untrusted channel.
* Stage 3 - adaptive attacker: inject -> observe -> classify -> refine, in a loop.
* Stage 4 - runner that compares defense OFF / ON+static / ON+adaptive.

The attacker is strictly black-box: it only controls text that ends up in
untrusted data the agent reads (emails, files, calendar entries) and only
observes the agent's outputs and actions. It never touches model weights,
gradients, or internals.
"""
