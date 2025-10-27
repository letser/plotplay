"""Tests for flag visibility filtering in state summary."""
import pytest

from tests_v2.conftest_services import engine_fixture  # noqa: F401
from app.models.flags import BoolFlag


def test_only_visible_flags_in_summary(engine_fixture):
    """Test that only visible flags appear in state summary."""
    engine = engine_fixture
    state = engine.state_manager.state

    # Add flag definitions to game
    engine.game_def.flags = {
        "visible_flag": BoolFlag(type="bool", default=False, visible=True, label="Visible Flag"),
        "hidden_flag": BoolFlag(type="bool", default=False, visible=False, label="Hidden Flag"),
        "no_reveal_when": BoolFlag(type="bool", default=False, visible=False, label="Hidden No Reveal"),
    }

    # Set all flags to True in state
    state.flags["visible_flag"] = True
    state.flags["hidden_flag"] = True
    state.flags["no_reveal_when"] = True

    # Build summary
    summary = engine.state_summary.build()

    # Only visible_flag should appear
    assert "visible_flag" in summary["flags"], "Visible flag should be in summary"
    assert "hidden_flag" not in summary["flags"], "Hidden flag should NOT be in summary"
    assert "no_reveal_when" not in summary["flags"], "Hidden flag without reveal_when should NOT be in summary"

    # Verify the visible flag has correct data
    assert summary["flags"]["visible_flag"]["value"] is True
    assert summary["flags"]["visible_flag"]["label"] == "Visible Flag"


def test_reveal_when_makes_flag_visible(engine_fixture):
    """Test that reveal_when condition can make a hidden flag visible."""
    engine = engine_fixture
    state = engine.state_manager.state

    # Add flag with reveal_when condition
    engine.game_def.flags = {
        "secret_flag": BoolFlag(
            type="bool",
            default=False,
            visible=False,
            label="Secret Flag",
            reveal_when="flags.trigger_flag == true"
        ),
        "trigger_flag": BoolFlag(type="bool", default=False, visible=False),
    }

    state.flags["secret_flag"] = True
    state.flags["trigger_flag"] = False

    # Build summary - secret_flag should NOT be visible yet
    summary = engine.state_summary.build()
    assert "secret_flag" not in summary["flags"], "Secret flag should not be visible when reveal_when is false"

    # Now set trigger_flag to True
    state.flags["trigger_flag"] = True

    # Build summary again - secret_flag SHOULD now be visible
    summary = engine.state_summary.build()
    assert "secret_flag" in summary["flags"], "Secret flag should be visible when reveal_when is true"


def test_empty_flags_dict_when_no_visible_flags(engine_fixture):
    """Test that flags dict is empty when no flags are visible."""
    engine = engine_fixture
    state = engine.state_manager.state

    # Add only hidden flags
    engine.game_def.flags = {
        "hidden1": BoolFlag(type="bool", default=False, visible=False),
        "hidden2": BoolFlag(type="bool", default=False, visible=False),
    }

    state.flags["hidden1"] = True
    state.flags["hidden2"] = True

    # Build summary
    summary = engine.state_summary.build()

    # Flags dict should be empty
    assert summary["flags"] == {}, "Flags dict should be empty when no flags are visible"
