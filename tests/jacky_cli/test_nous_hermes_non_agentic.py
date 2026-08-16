"""Tests for the Nous-Hermes-3/4 non-agentic warning detector.

Prior to this check, the warning fired on any model whose name contained
``"jacky"`` anywhere (case-insensitive). That false-positived on unrelated
local Modelfiles such as ``jacky-brain:qwen3-14b-ctx16k`` — a tool-capable
Qwen3 wrapper that happens to live under the "jacky" tag namespace.

``is_nous_hermes_non_agentic`` should only match the actual Nous Research
Hermes-3 / Hermes-4 chat family.
"""

from __future__ import annotations

import pytest

from jacky_cli.model_switch import (
    _JACKY_MODEL_WARNING,
    _check_jacky_model_warning,
    is_nous_hermes_non_agentic,
)


@pytest.mark.parametrize(
    "model_name",
    [
        "NousResearch/Hermes-3-Llama-3.1-70B",
        "NousResearch/Hermes-3-Llama-3.1-405B",
        "hermes-3",
        "Hermes-3",
        "hermes-4",
        "hermes-4-405b",
        "hermes_4_70b",
        "openrouter/hermes3:70b",
        "openrouter/nousresearch/hermes-4-405b",
        "NousResearch/Hermes3",
        "hermes-3.1",
    ],
)
def test_matches_real_nous_hermes_chat_models(model_name: str) -> None:
    assert is_nous_hermes_non_agentic(model_name), (
        f"expected {model_name!r} to be flagged as Nous Hermes 3/4"
    )
    assert _check_jacky_model_warning(model_name) == _JACKY_MODEL_WARNING


@pytest.mark.parametrize(
    "model_name",
    [
        # Kyle's local Modelfile — qwen3:14b under a custom tag
        "jacky-brain:qwen3-14b-ctx16k",
        "jacky-brain:qwen3-14b-ctx32k",
        "jacky-honcho:qwen3-8b-ctx8k",
        # Plain unrelated models
        "qwen3:14b",
        "qwen3-coder:30b",
        "qwen2.5:14b",
        "claude-opus-4-6",
        "anthropic/claude-sonnet-4.5",
        "gpt-5",
        "openai/gpt-4o",
        "google/gemini-2.5-flash",
        "deepseek-chat",
        # Non-chat Jacky models we don't warn about
        "jacky-llm-2",
        "jacky2-pro",
        "nous-hermes-2-mistral",
        # Edge cases
        "",
        "hermes",  # bare "hermes" isn't the 3/4 family
        "hermes-brain",
        "brain-hermes-3-impostor",  # "3" not preceded by /: boundary
    ],
)
def test_does_not_match_unrelated_models(model_name: str) -> None:
    assert not is_nous_hermes_non_agentic(model_name), (
        f"expected {model_name!r} NOT to be flagged as Nous Hermes 3/4"
    )
    assert _check_jacky_model_warning(model_name) == ""


def test_none_like_inputs_are_safe() -> None:
    assert is_nous_hermes_non_agentic("") is False
    # Defensive: the helper shouldn't crash on None-ish falsy input either.
    assert _check_jacky_model_warning("") == ""
