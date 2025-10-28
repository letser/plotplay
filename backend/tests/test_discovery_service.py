import pytest

from types import SimpleNamespace

from app.engine.discovery import DiscoveryService
from tests.conftest_services import engine_fixture


@pytest.fixture
def discovery(engine_fixture) -> DiscoveryService:
    return DiscoveryService(engine_fixture)


def test_discovery_adds_location(discovery):
    engine = discovery.engine
    state = engine.state_manager.state
    zone = engine.game_def.zones[0]

    new_location = SimpleNamespace(
        id="library",
        name="Library",
        discovery_conditions=["flags.met_friend"],
        access=SimpleNamespace(locked=False, unlocked_when=None),
    )
    zone.locations.append(new_location)
    engine.locations_map[new_location.id] = new_location

    state.discovered_locations = []
    engine.state_manager.state.flags["met_friend"] = True

    discovery.refresh()

    assert "library" in state.discovered_locations


def test_zone_discovery_unlocks_locations(discovery):
    engine = discovery.engine
    state = engine.state_manager.state

    new_zone = SimpleNamespace(
        id="downtown",
        discovery_conditions=["flags.has_map"],
        locations=[
            SimpleNamespace(
                id="downtown_square",
                name="Downtown Square",
                discovery_conditions=["true"],
                access=SimpleNamespace(locked=False, unlocked_when=None),
            )
        ],
    )
    engine.game_def.zones.append(new_zone)
    engine.zones_map[new_zone.id] = new_zone
    for loc in new_zone.locations:
        engine.locations_map[loc.id] = loc

    state.discovered_zones = []
    state.discovered_locations = []
    state.flags["has_map"] = True

    discovery.refresh()

    assert "downtown" in state.discovered_zones
    for loc in new_zone.locations:
        assert loc.id in state.discovered_locations
