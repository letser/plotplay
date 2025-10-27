import logging

from app.core.game_loader import GameLoader
from app.core.game_engine import GameEngine
from app.models.actions import Action
from app.models.locations import Location, LocationConnection
from app.models.nodes import Choice
from tests_v2.conftest import minimal_game


def make_engine(tmp_path, monkeypatch, mock_ai_service) -> GameEngine:
    def fake_logger(session_id: str) -> logging.Logger:
        logger = logging.getLogger(f"choice-test-{session_id}")
        logger.handlers.clear()
        logger.setLevel(logging.DEBUG)
        logger.addHandler(logging.NullHandler())
        return logger

    monkeypatch.setattr("app.engine.runtime.setup_session_logger", fake_logger)

    game_path = minimal_game(tmp_path)
    loader = GameLoader(games_dir=game_path.parent)
    game_def = loader.load_game(game_path.name)
    return GameEngine(game_def, session_id="choice-session", ai_service=mock_ai_service)


def test_choice_service_combines_sources(tmp_path, monkeypatch, mock_ai_service):
    engine = make_engine(tmp_path, monkeypatch, mock_ai_service)
    state = engine.state_manager.state
    node = engine._get_current_node()

    node.choices.append(Choice(id="wave", prompt="Wave hello", when="always"))
    node.dynamic_choices.append(Choice(id="hug", prompt="Offer a hug", when="flags.met_friend"))
    state.flags["met_friend"] = True

    event_choice = Choice(id="event_option", prompt="Spur-of-the-moment", when="always")

    action = Action(id="smile", prompt="Smile warmly", when="always")
    engine.game_def.actions.append(action)
    engine.actions_map[action.id] = action
    state.unlocked_actions.append(action.id)

    new_location = Location(id="library", name="Campus Library")
    new_location.access.locked = True
    new_location.access.unlocked_when = "flags.has_key"
    engine.game_def.zones[0].locations.append(new_location)
    engine.locations_map[new_location.id] = new_location

    current_location = engine._get_location(state.location_current)
    current_location.connections.append(
        LocationConnection(to=new_location.id, direction="north")
    )
    state.discovered_locations.append(new_location.id)

    choices = engine.choices.build(node, [event_choice])
    choice_ids = {c["id"] for c in choices}

    assert {"event_option", "hug", "smile", "move_library"} <= choice_ids
    assert "wave" not in choice_ids

    move_choice = next(c for c in choices if c["id"] == "move_library")
    assert move_choice["disabled"] is True

    state.flags["has_key"] = True
    refreshed = engine.choices.build(node, [])
    refreshed_ids = {c["id"] for c in refreshed}
    assert "wave" in refreshed_ids
    move_choice_refreshed = next(c for c in refreshed if c["id"] == "move_library")
    assert move_choice_refreshed["disabled"] is False

    state.flags["met_friend"] = False
    choices_without_friend = engine.choices.build(node, [])
    assert "hug" not in {c["id"] for c in choices_without_friend}
