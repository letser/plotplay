"""Test StateManager initialization and game definition indexing."""

from app.core.loader import GameLoader
from app.core.state import StateManager
from app.models.locations import LocationPrivacy


def load_reference_game() -> StateManager:
    loader = GameLoader()
    game_def = loader.load_game("coffeeshop_date")
    return StateManager(game_def)


def test_game_definition_index_maps_entities():
    """Test that game definition index correctly maps all entity types."""
    loader = GameLoader()
    game_def = loader.load_game("coffeeshop_date")

    index = game_def.index
    assert "outside_cafe" in index.nodes
    assert "cafe_patio" in index.locations
    assert index.location_to_zone["cafe_patio"] == "downtown"
    assert "player_date_casual" in index.outfits


def test_state_initialization_sets_time_and_location():
    """Test that StateManager initializes state with correct time and location."""
    manager = load_reference_game()
    state = manager.state

    # Check node and location initialization
    assert state.current_node == manager.game_def.start.node
    assert state.current_location == manager.game_def.start.location
    assert state.current_zone == "downtown"
    assert state.current_privacy == LocationPrivacy.MEDIUM

    # Check time initialization
    assert state.time.day == manager.game_def.start.day
    assert state.time.slot == "afternoon"  # Inferred from start time "13:00"


def test_state_initializes_characters_and_inventory():
    """Test that StateManager initializes character states with meters and inventory."""
    manager = load_reference_game()
    state = manager.state

    # Check player character exists
    assert "player" in state.characters

    # Check meters are initialized
    assert "confidence" in state.characters["player"].meters
    assert state.characters["player"].meters["confidence"] == 55  # default value from game

    # Check inventory is initialized
    assert "phone" in state.characters["player"].inventory.items
    assert state.characters["player"].inventory.items["phone"] == 1

    # Check clothing is initialized
    assert state.characters["player"].clothing.outfit == "player_date_casual"


def test_state_tracks_discovery_and_history():
    """Test that StateManager tracks discovered locations and visited nodes."""
    manager = load_reference_game()
    state = manager.state

    # Check starting location is discovered
    assert manager.game_def.start.location in state.discovered_locations

    # Check starting node is in history
    assert manager.game_def.start.node in state.nodes_history

    # Check cooldowns are initialized empty
    assert state.cooldowns == {}
