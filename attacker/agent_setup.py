"""Shared setup: load settings from .env and build the target agent pipeline.

Everything that talks to AgentDojo's configuration lives here so the attacker
modules (Stages 2-4) can stay focused on attack logic.
"""

import os
from dataclasses import dataclass

import anthropic
import openai
from dotenv import load_dotenv

from agentdojo.agent_pipeline import AgentPipeline, AnthropicLLM, OpenAILLM, PipelineConfig
from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.task_suite.load_suites import get_suite
from agentdojo.task_suite.task_suite import TaskSuite

# AgentDojo ships several versions of its benchmark data; we pin one so results
# are comparable across teammates and over time.
BENCHMARK_VERSION = "v1.2.2"

# The "workspace" suite = an office assistant with email, calendar and cloud
# drive tools. Its injection points are mostly emails and documents, which is
# exactly the indirect-injection setting we study.
DEFAULT_SUITE = "workspace"


@dataclass
class Settings:
    """Values read from .env (see .env.example)."""

    provider: str  # "openai" or "anthropic"
    model: str  # model name passed to the provider's API


def load_settings() -> Settings:
    """Read LLM settings from the project's .env file.

    API keys are not returned here: the OpenAI / Anthropic SDKs read
    OPENAI_API_KEY / ANTHROPIC_API_KEY from the environment themselves, so the
    key never has to pass through our code.
    """
    load_dotenv()
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    model = os.getenv("LLM_MODEL", "gpt-4o-mini-2024-07-18").strip()

    key_var = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}.get(provider)
    if key_var is None:
        raise ValueError(f"Unsupported LLM_PROVIDER={provider!r}; use 'openai' or 'anthropic'.")
    if not os.getenv(key_var):
        raise RuntimeError(f"{key_var} is not set. Copy .env.example to .env and add your key.")
    return Settings(provider=provider, model=model)


def build_llm(settings: Settings) -> BasePipelineElement:
    """Create the AgentDojo LLM element for the configured hosted model.

    We build the element ourselves (instead of passing a model name string to
    AgentDojo) so we can use any model the provider offers, not only the ones
    listed in AgentDojo's built-in ModelsEnum.
    """
    if settings.provider == "openai":
        llm = OpenAILLM(openai.OpenAI(), settings.model)
    else:
        llm = AnthropicLLM(anthropic.Anthropic(), settings.model)
    llm.name = settings.model  # used by AgentDojo for logging / pipeline naming
    return llm


def build_pipeline(settings: Settings, defense: str | None = None) -> AgentPipeline:
    """Build the target agent: system prompt -> user query -> LLM <-> tools loop.

    ``defense`` is one of AgentDojo's built-in defenses, or None for no defense.
    API-only options: "spotlighting_with_delimiting", "repeat_user_prompt",
    and "tool_filter" (OpenAI models only).
    """
    config = PipelineConfig(
        llm=build_llm(settings),
        model_id=None,
        defense=defense,
        system_message_name=None,  # AgentDojo's default system prompt
        system_message=None,
    )
    return AgentPipeline.from_config(config)


def load_suite(name: str = DEFAULT_SUITE) -> TaskSuite:
    """Load an AgentDojo task suite at our pinned benchmark version."""
    return get_suite(BENCHMARK_VERSION, name)
