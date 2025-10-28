"""Regression tests for the PromptBuilder writer/checker prompts."""

import json

from tests.conftest_services import engine_fixture  # noqa: F401


def test_writer_prompt_includes_new_sections(engine_fixture):
    engine = engine_fixture
    state = engine.state_manager.state
    state.present_chars = ["player"]
    node = engine.get_current_node()

    prompt = engine.prompt_builder.build_writer_prompt(
        state,
        player_action="Wave at the crowd.",
        node=node,
        recent_history=[],
    )

    assert "**Scene Beats (Internal Only):**" in prompt
    assert "**Movement Options (FOR REFERENCE ONLY - DO NOT NARRATE):**" in prompt
    assert "**Merchants & Shops (FOR REFERENCE ONLY):**" in prompt
    assert "Wardrobe State:" in prompt
    # Verify new strict constraints are present
    assert "DO NOT change locations" in prompt
    assert "MAXIMUM:" in prompt


def test_checker_prompt_contract_shape(engine_fixture):
    engine = engine_fixture
    state = engine.state_manager.state

    payload = json.loads(
        engine.prompt_builder.build_checker_prompt(
            narrative="The player looks around the quad.",
            player_action="Look around",
            state=state,
        )
    )

    assert set(payload.keys()) == {"player_action", "narrative", "pre_state", "constraints", "response_contract"}

    pre_state = payload["pre_state"]
    assert "time" in pre_state
    assert "location" in pre_state
    assert "meters" in pre_state
    assert "inventory" in pre_state

    constraints = payload["constraints"]
    assert "meters" in constraints
    assert "inventory" in constraints
    assert "clothing" in constraints
    assert "movement" in constraints
    assert "currency" in constraints

    contract = payload["response_contract"]
    assert set(contract["required_keys"]) == {
        "meters",
        "inventory",
        "clothing",
        "movement",
        "discoveries",
        "modifiers",
        "flags",
        "memory",
    }
    assert "schema" in contract and "notes" in contract


def test_action_summary_formats_action(engine_fixture):
    engine = engine_fixture

    # Test with action description
    summary = engine.state_summary.build_action_summary("Player action: waves hello")
    assert summary == "Player action: waves hello"

    # Test with None
    summary_none = engine.state_summary.build_action_summary(None)
    assert summary_none == "Action taken"

    # Test with empty string
    summary_empty = engine.state_summary.build_action_summary("")
    assert summary_empty == "Action taken"
