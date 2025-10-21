import pytest

from app.engine.actions import ActionFormatter
from app.models.actions import Action
from app.models.nodes import Choice
from tests_v2.conftest_services import engine_fixture


@pytest.fixture
def formatter(engine_fixture) -> ActionFormatter:
    return ActionFormatter(engine_fixture)


def test_formatter_returns_item_use_text(formatter):
    engine = formatter.engine
    engine.inventory.item_defs["coffee"].use_text = "Enjoy a warm coffee."
    result = formatter.format("use", None, None, None, "coffee")
    assert result == "Enjoy a warm coffee."


def test_formatter_choice_lookup(formatter):
    engine = formatter.engine
    node = engine._get_current_node()
    node.choices.append(Choice(id="wave", prompt="Wave hello"))

    result = formatter.format("choice", None, None, "wave", None)
    assert result == "Player chooses to: 'Wave hello'"


def test_formatter_unlocked_action_fallback(formatter):
    engine = formatter.engine
    state = engine.state_manager.state

    action = Action(id="smile", prompt="Smile warmly")
    engine.game_def.actions.append(action)
    engine.actions_map[action.id] = action
    state.unlocked_actions.append(action.id)

    result = formatter.format("choice", None, None, "smile", None)
    assert result == "Player chooses to: 'Smile warmly'"
