import pytest

from app.engine.presence import PresenceService
from tests.conftest_services import engine_fixture


@pytest.fixture
def presence(engine_fixture) -> PresenceService:
    return PresenceService(engine_fixture)


def test_presence_adds_scheduled_npc(presence):
    engine = presence.engine
    state = engine.state_manager.state

    # set up schedule for test NPC
    npc = engine.characters_map.get("friend")
    npc.schedule = [{"location": state.location_current, "when": "true"}]

    assert "friend" not in state.present_chars
    presence.refresh()
    assert "friend" in state.present_chars
