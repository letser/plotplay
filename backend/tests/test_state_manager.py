from app.core.loader import GameLoader
from app.core.state import StateManager
from app.models.locations import LocationPrivacy


def load_reference_game() -> StateManager:
    loader = GameLoader()
    game_def = loader.load_game("coffeeshop_date")
    return StateManager(game_def)


def test_game_definition_index_maps_entities():
    loader = GameLoader()
    game_def = loader.load_game("coffeeshop_date")

    index = game_def.index
    assert "outside_cafe" in index.nodes
    assert "cafe_patio" in index.locations
    assert index.location_to_zone["cafe_patio"] == "downtown"
    assert "player_date_casual" in index.outfits


def test_state_initialization_sets_time_and_location():
    manager = load_reference_game()
    state = manager.state

    assert state.current_node == manager.game_def.start.node
    assert state.location_current == manager.game_def.start.location
    assert state.zone_current == "downtown"
    assert state.location_privacy == LocationPrivacy.MEDIUM
    assert state.day == manager.game_def.start.day
    assert state.present_chars == ["player"]


def test_state_initializes_characters_and_inventory():
    manager = load_reference_game()
    state = manager.state

    assert "player" in state.meters
    assert "player" in state.inventory
    assert state.inventory["player"]["phone"] == 1
    assert state.outfits_equipped["player"] == "player_date_casual"
    assert state.clothing_states["player"]


def test_state_tracks_discovery_and_history():
    manager = load_reference_game()
    state = manager.state

    assert manager.game_def.start.location in state.discovered_locations
    assert manager.game_def.start.node in state.visited_nodes
    assert state.cooldowns == {}
