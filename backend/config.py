"""Centralized model configuration for every Campus Customs agent.

Every agent in this project MUST go through `get_model()` below. This is the
single place that names the model and reads the API key, so it is trivial
to audit that no agent silently uses a different model or provider.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

REQUIRED_MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

# Load the course-level .env (one directory above "MGT 409 AI/Homework 5"'s
# siblings -- the .env lives at "MGT 409 AI/.env").
_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_ENV_PATH)


def get_model() -> OpenAIChatModel:
    """Return the one and only model every agent must use.

    Raises if PORTKEY_API_KEY is missing, rather than silently falling back
    to some other provider or model.
    """
    api_key = os.environ.get("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError(
            "PORTKEY_API_KEY is not set. Every Campus Customs agent requires it; "
            "refusing to start rather than silently using a different provider."
        )
    return OpenAIChatModel(
        REQUIRED_MODEL_NAME,
        provider=OpenAIProvider(base_url=PORTKEY_BASE_URL, api_key=api_key),
        # gpt-6-luna rejects function/tool calls on /v1/chat/completions unless
        # reasoning_effort is explicitly "none" -- required for MCP tool use.
        settings={"openai_reasoning_effort": "none"},
    )


def assert_model_is_compliant(model: OpenAIChatModel) -> None:
    """Fail loudly if some code path ever constructs a non-compliant model."""
    if model.model_name != REQUIRED_MODEL_NAME:
        raise RuntimeError(
            f"Model compliance violation: expected '{REQUIRED_MODEL_NAME}', "
            f"got '{model.model_name}'."
        )
