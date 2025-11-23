"""
Tests for movement validation logic (exit/entry checks, compass directions, NPC willingness).
"""

import pytest
from unittest.mock import Mock, MagicMock
from app.engine.movement import MovementService
from app.runtime.services.actions import ActionService
from app.runtime.types import PlayerAction


class TestCompassDirections:
    """Test compass direction mapping and movement."""

    @pytest.fixture
    def movement_service(self):
        """Create movement service with mocked engine."""
        engine = Mock()
        engine.logger = Mock()
        engine.state_manager = Mock()
        engine.get_location = Mock()

        service = MovementService(engine)
        return service

    def test_direction_normalization(self, movement_service):
        """Test that various direction formats are normalized correctly."""
        # Setup mock location with north connection
        mock_location = Mock()
        mock_connection = Mock()
        # Mock direction with both value (short form) and name (full form)
        # Configure name to properly return "north" when lower() is called
        mock_direction = Mock()
        mock_direction.value = "n"
        mock_direction.name = Mock()
        mock_direction.name.lower = Mock(return_value="north")
        mock_connection.direction = mock_direction
        mock_connection.to = "target_location"
        mock_location.connections = [mock_connection]

        # Setup state with discovered location
        state = Mock()
        state.current_location = "start"
        state.discovered_locations = ["target_location"]
        movement_service.engine.state_manager.state = state

        movement_service.engine.get_location.return_value = mock_location
        movement_service._execute_local_movement = Mock(return_value={"action_summary": "moved"})

        # Test various formats
        for direction in ["n", "N", "north", "North", "NORTH"]:
            result = movement_service.move_by_direction(direction)
            assert result is True, f"Failed for direction: {direction}"

    def test_all_compass_directions(self, movement_service):
        """Test all supported compass directions."""
        directions = {
            "n": "n", "s": "s", "e": "e", "w": "w",
            "ne": "ne", "se": "se", "sw": "sw", "nw": "nw",
            "u": "u", "d": "d"
        }

        for input_dir, expected_dir in directions.items():
            mock_location = Mock()
            mock_connection = Mock()
            mock_connection.direction = Mock(value=expected_dir)
            mock_connection.to = "destination"
            mock_location.connections = [mock_connection]

            # Setup state with discovered location
            state = Mock()
            state.current_location = "start"
            state.discovered_locations = ["destination"]
            movement_service.engine.state_manager.state = state

            movement_service.engine.get_location.return_value = mock_location
            movement_service._execute_local_movement = Mock(return_value={"action_summary": "moved"})

            result = movement_service.move_by_direction(input_dir)
            assert result is True, f"Direction {input_dir} should work"

    def test_invalid_direction(self, movement_service):
        """Test that invalid directions return False."""
        mock_location = Mock()
        mock_location.connections = []

        movement_service.engine.get_location.return_value = mock_location

        result = movement_service.move_by_direction("invalid")
        assert result is False

    def test_no_connection_in_direction(self, movement_service):
        """Test movement when no connection exists in that direction."""
        mock_location = Mock()
        # Connection exists but in different direction
        mock_connection = Mock()
        mock_connection.direction = Mock(value="s")
        mock_connection.to = "south_location"
        mock_location.connections = [mock_connection]

        movement_service.engine.get_location.return_value = mock_location

        # Try to move north (no connection)
        result = movement_service.move_by_direction("n")
        assert result is False


class TestExitEntryValidation:
    """Test zone exit/entry validation for travel."""

    @pytest.fixture
    def movement_service(self):
        """Create movement service with mocked engine."""
        engine = Mock()
        engine.logger = Mock()
        engine.state_manager = Mock()
        engine.zones_map = {}
        engine.get_location = Mock(return_value=Mock())
        engine.game_def = Mock()
        engine._get_location_privacy = Mock(return_value="medium")
        engine.check_and_apply_node_transitions = Mock()
        engine._category_to_minutes = Mock(return_value=10)  # Mock time calculation

        # Mock time defaults
        time_defaults = Mock()
        time_defaults.movement = "moderate"
        engine.game_def.time = Mock()
        engine.game_def.time.defaults = time_defaults

        service = MovementService(engine)
        service._sync_presence_after_move = Mock()
        return service

    def test_exit_validation_success(self, movement_service):
        """Test successful exit from valid exit location."""
        # Setup zones
        origin_zone = Mock()
        origin_zone.exits = ["exit_location"]
        origin_zone.connections = []

        target_zone = Mock()
        target_zone.locations = [Mock(id="target_location")]
        target_zone.entrances = ["target_location"]

        movement_service.engine.zones_map = {
            "origin": origin_zone,
            "target": target_zone
        }

        # Setup state at valid exit
        state = Mock()
        state.current_zone = "origin"
        state.current_location = "exit_location"
        movement_service.engine.state_manager.state = state

        # Setup movement rules
        move_rules = Mock(use_entry_exit=True, methods=[])
        movement_service.engine.game_def.movement = move_rules

        # Should succeed
        result = movement_service.travel_to_zone(zone_id="target")
        assert result is True

    def test_exit_validation_failure(self, movement_service):
        """Test blocked exit from non-exit location."""
        # Setup zones
        origin_zone = Mock()
        origin_zone.exits = ["exit_location"]  # Only this location is valid exit
        origin_zone.connections = []

        target_zone = Mock()
        target_zone.locations = [Mock(id="target_location")]
        target_zone.entrances = ["target_location"]

        movement_service.engine.zones_map = {
            "origin": origin_zone,
            "target": target_zone
        }

        # Setup state at NON-EXIT location
        state = Mock()
        state.current_zone = "origin"
        state.current_location = "not_an_exit"  # Invalid!
        movement_service.engine.state_manager.state = state

        # Setup movement rules
        move_rules = Mock(use_entry_exit=True, methods=[])
        movement_service.engine.game_def.movement = move_rules

        # Should fail
        result = movement_service.travel_to_zone(zone_id="target")
        assert result is False

        # Verify warning was logged
        movement_service.engine.logger.warning.assert_called()

    def test_entry_validation_success(self, movement_service):
        """Test successful entry at valid entrance location."""
        # Setup zones
        origin_zone = Mock()
        origin_zone.exits = ["origin_location"]
        origin_zone.connections = []

        target_zone = Mock()
        target_zone.locations = [Mock(id="entrance_location")]
        target_zone.entrances = ["entrance_location", "another_entrance"]

        movement_service.engine.zones_map = {
            "origin": origin_zone,
            "target": target_zone
        }

        state = Mock()
        state.current_zone = "origin"
        state.current_location = "origin_location"
        movement_service.engine.state_manager.state = state

        move_rules = Mock(use_entry_exit=True, methods=[])
        movement_service.engine.game_def.movement = move_rules

        # Specify valid entrance
        result = movement_service.travel_to_zone(
            zone_id="target",
            entry_location_id="entrance_location"
        )
        assert result is True

    def test_entry_validation_failure(self, movement_service):
        """Test blocked entry at non-entrance location."""
        # Setup zones
        origin_zone = Mock()
        origin_zone.exits = ["origin_location"]
        origin_zone.connections = []

        target_zone = Mock()
        target_zone.locations = [Mock(id="back_door")]
        target_zone.entrances = ["front_door"]  # Only front door is valid

        movement_service.engine.zones_map = {
            "origin": origin_zone,
            "target": target_zone
        }

        state = Mock()
        state.current_zone = "origin"
        state.current_location = "origin_location"
        movement_service.engine.state_manager.state = state

        move_rules = Mock(use_entry_exit=True, methods=[])
        movement_service.engine.game_def.movement = move_rules

        # Try to enter via back door (not an entrance)
        result = movement_service.travel_to_zone(
            zone_id="target",
            entry_location_id="back_door"
        )
        assert result is False

        # Verify warning was logged
        movement_service.engine.logger.warning.assert_called()

    def test_no_validation_when_disabled(self, movement_service):
        """Test that validation is skipped when use_entry_exit=false."""
        # Setup zones without entry/exit restrictions
        origin_zone = Mock()
        origin_zone.connections = []

        target_zone = Mock()
        target_zone.locations = [Mock(id="any_location")]
        target_zone.entrances = None  # No entrance restrictions

        movement_service.engine.zones_map = {
            "origin": origin_zone,
            "target": target_zone
        }

        state = Mock()
        state.current_zone = "origin"
        state.current_location = "any_location_origin"
        movement_service.engine.state_manager.state = state

        # Disable entry/exit validation
        move_rules = Mock(use_entry_exit=False, methods=[])
        movement_service.engine.game_def.movement = move_rules

        # Should succeed from any location
        result = movement_service.travel_to_zone(zone_id="target")
        assert result is True


class TestNPCWillingnessValidation:
    """Test NPC willingness checks for movement with companions."""

    @pytest.fixture
    def action_service(self):
        """Create action service with mocked runtime."""
        runtime = Mock()
        runtime.state_manager = Mock()
        runtime.effect_resolver = Mock()
        runtime.inventory_service = Mock()

        service = ActionService(runtime)
        return service

    def test_companion_not_present(self, action_service):
        """Test error when companion is not present."""
        state = Mock()
        state.present_characters = ["player"]  # Alex not present
        state.characters = {}
        action_service.runtime.state_manager.state = state

        with pytest.raises(ValueError, match="character not present"):
            action_service._validate_companion_willingness(["alex"], "move")

    def test_companion_unwilling_generic(self, action_service):
        """Test error when companion has follow_player=false."""
        state = Mock()
        state.present_characters = ["player", "alex"]

        alex_state = Mock()
        alex_state.gates = {"follow_player": False}  # Unwilling!
        state.characters = {"alex": alex_state}

        action_service.runtime.state_manager.state = state

        with pytest.raises(ValueError, match="unwilling to follow"):
            action_service._validate_companion_willingness(["alex"], "move")

    def test_companion_unwilling_specific(self, action_service):
        """Test error when companion has action-specific unwillingness."""
        state = Mock()
        state.present_characters = ["player", "alex"]

        alex_state = Mock()
        alex_state.gates = {
            "follow_player": True,  # Generally willing
            "follow_player_travel": False  # But not for travel!
        }
        state.characters = {"alex": alex_state}

        action_service.runtime.state_manager.state = state

        # Should fail for travel
        with pytest.raises(ValueError, match="unwilling"):
            action_service._validate_companion_willingness(["alex"], "travel")

    def test_companion_willing(self, action_service):
        """Test success when companion is willing."""
        state = Mock()
        state.present_characters = ["player", "alex"]

        alex_state = Mock()
        alex_state.gates = {"follow_player": True}
        state.characters = {"alex": alex_state}

        action_service.runtime.state_manager.state = state

        # Should not raise
        action_service._validate_companion_willingness(["alex"], "move")

    def test_multiple_companions(self, action_service):
        """Test validation with multiple companions."""
        state = Mock()
        state.present_characters = ["player", "alex", "emma"]

        alex_state = Mock()
        alex_state.gates = {"follow_player": True}

        emma_state = Mock()
        emma_state.gates = {"follow_player": False}  # Emma unwilling!

        state.characters = {"alex": alex_state, "emma": emma_state}
        action_service.runtime.state_manager.state = state

        # Should fail because Emma is unwilling
        with pytest.raises(ValueError, match="emma.*unwilling"):
            action_service._validate_companion_willingness(["alex", "emma"], "move")

    def test_player_in_companions_skipped(self, action_service):
        """Test that 'player' in companions list is skipped."""
        state = Mock()
        state.present_characters = ["player"]
        state.characters = {}
        action_service.runtime.state_manager.state = state

        # Should not raise even though only player is present
        action_service._validate_companion_willingness(["player"], "move")


class TestMovementActionHandlers:
    """Test action service handlers for movement actions."""

    @pytest.fixture
    def action_service(self):
        """Create action service with mocked runtime."""
        runtime = Mock()
        runtime.state_manager = Mock()
        runtime.effect_resolver = Mock()
        runtime.movement_service = Mock()

        service = ActionService(runtime)
        return service

    def test_move_direction_success(self, action_service):
        """Test successful move by direction."""
        action_service.runtime.movement_service.move_by_direction = Mock(
            return_value={"action_summary": "You move north."}
        )

        # Should not raise
        action_service._handle_move_direction("n", None)

        action_service.runtime.movement_service.move_by_direction.assert_called_once_with("n", None)

    def test_move_direction_failure(self, action_service):
        """Test failed move (no connection)."""
        action_service.runtime.movement_service.move_by_direction = Mock(return_value=None)

        with pytest.raises(ValueError, match="Cannot move in direction"):
            action_service._handle_move_direction("n", None)

    def test_goto_location_success(self, action_service):
        """Test successful goto location."""
        action_service.runtime.movement_service.move_local = Mock(return_value=True)

        # Should not raise
        action_service._handle_goto_location("park", None)

        action_service.runtime.movement_service.move_local.assert_called_once_with("park", None)

    def test_goto_location_failure(self, action_service):
        """Test failed goto (location not reachable)."""
        action_service.runtime.movement_service.move_local = Mock(return_value=False)

        with pytest.raises(ValueError, match="Cannot move to location"):
            action_service._handle_goto_location("park", None)

    def test_travel_success(self, action_service):
        """Test successful travel."""
        action_service.runtime.movement_service.travel_to_zone = Mock(return_value=True)

        # Should not raise
        action_service._handle_travel("downtown", None)

        action_service.runtime.movement_service.travel_to_zone.assert_called_once_with(
            location_id="downtown",
            with_characters=None
        )

    def test_travel_failure(self, action_service):
        """Test failed travel."""
        action_service.runtime.movement_service.travel_to_zone = Mock(return_value=False)

        with pytest.raises(ValueError, match="Cannot travel to location"):
            action_service._handle_travel("downtown", None)

    def test_move_with_companions(self, action_service):
        """Test movement with companions checks willingness."""
        state = Mock()
        state.present_characters = ["player", "alex"]
        alex_state = Mock()
        alex_state.gates = {"follow_player": True}
        state.characters = {"alex": alex_state}
        action_service.runtime.state_manager.state = state

        action_service.runtime.movement_service.move_by_direction = Mock(
            return_value={"action_summary": "moved"}
        )

        # Should validate willingness and succeed
        action_service._handle_move_direction("n", ["alex"])

        action_service.runtime.movement_service.move_by_direction.assert_called_once_with("n", ["alex"])

    def test_movement_service_not_available(self, action_service):
        """Test error when movement service not available."""
        action_service.runtime.movement_service = None

        with pytest.raises(RuntimeError, match="Movement service not available"):
            action_service._handle_move_direction("n", None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
