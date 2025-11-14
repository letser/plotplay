"""Integration tests for MovementService (movement system mechanics).

Tests verify:
1. Local movement between locations in same zone
2. Zone travel between different zones
3. Time consumption for movement
4. NPC companion willingness checks
5. Movement restrictions (if applicable)
"""
import pytest
from app.core.game_engine import GameEngine
from app.models.game import GameDefinition, MetaConfig, GameStart
from app.models.time import Time
from app.models.locations import (
    Zone, Location, LocationConnection, LocalDirection,
    Movement
)
from app.models.characters import Character
from app.models.locations import MovementWillingness, LocationMovementWillingness
from app.models.meters import MetersTemplate, Meter
from app.models.nodes import Node


@pytest.fixture
def game_with_movement() -> GameDefinition:
    """Create a game with multiple locations and zones for movement testing."""
    game = GameDefinition(
        meta=MetaConfig(
            id="movement_test",
            title="Movement Test Game",
            version="1.0.0"
        ),
        start=GameStart(
            node="start",
            location="room_a",
            day=1,
            slot="morning"
        ),
        time=Time(
            mode="hybrid",
            slots=["morning", "afternoon", "evening"],
            minutes_per_action=10,
            actions_per_slot=3,
            slot_windows={
                "morning": {"start": "06:00", "end": "12:00"},
                "afternoon": {"start": "12:00", "end": "18:00"},
                "evening": {"start": "18:00", "end": "23:00"}
            }
        ),
        meters=MetersTemplate(
            player={
                "energy": Meter(min=0, max=100, default=100, visible=True)
            }
        ),
        movement=Movement(
            base_time=5  # 5 minutes for local movement
        ),
        characters=[
            Character(
                id="player",
                name="You",
                age=20,
                gender="unspecified"
            ),
            Character(
                id="friend",
                name="Friend",
                age=20,
                gender="unspecified",
                movement=MovementWillingness(
                    willing_locations=[
                        LocationMovementWillingness(
                            location="room_b",
                            when="always"
                        )
                    ]
                )
            )
        ],
        zones=[
            Zone(
                id="zone1",
                name="Building A",
                locations=[
                    Location(
                        id="room_a",
                        name="Room A",
                        description="The starting room.",
                        connections=[
                            LocationConnection(
                                to="room_b",
                                direction=LocalDirection.N,
                                description="North to Room B"
                            )
                        ]
                    ),
                    Location(
                        id="room_b",
                        name="Room B",
                        description="Another room.",
                        connections=[
                            LocationConnection(
                                to="room_a",
                                direction=LocalDirection.S,
                                description="South to Room A"
                            )
                        ]
                    )
                ]
            ),
            Zone(
                id="zone2",
                name="Building B",
                locations=[
                    Location(
                        id="room_c",
                        name="Room C",
                        description="A room in another building."
                    )
                ]
            )
        ],
        nodes=[
            Node(id="start", type="scene", title="Start")
        ]
    )
    return game


class TestLocalMovement:
    """Test local movement within a zone."""

    @pytest.mark.asyncio
    async def test_local_movement_changes_location(self, game_with_movement, mock_ai_service):
        """Test that local movement updates current location."""
        engine = GameEngine(game_with_movement, session_id="test-local-move", ai_service=mock_ai_service)
        state = engine.state_manager.state

        # Discover room_b (movement requires it)
        if "room_b" not in state.discovered_locations:
            state.discovered_locations.append("room_b")

        # Initial location
        assert state.location_current == "room_a"

        # Move to room_b via choice
        result = await engine.movement.handle_choice("move_room_b")

        # Verify location changed
        assert state.location_current == "room_b"
        assert state.location_previous == "room_a"
        assert "Room B" in result["narrative"]

    @pytest.mark.asyncio
    async def test_local_movement_consumes_time(self, game_with_movement, mock_ai_service):
        """Test that local movement consumes time based on base_time."""
        engine = GameEngine(game_with_movement, session_id="test-local-time", ai_service=mock_ai_service)
        state = engine.state_manager.state

        # Discover room_b (movement requires it)
        if "room_b" not in state.discovered_locations:
            state.discovered_locations.append("room_b")

        # Record initial time
        initial_time = state.time_hhmm
        initial_hh, initial_mm = map(int, initial_time.split(':'))

        # Move (should consume 5 minutes based on movement.base_time)
        await engine.movement.handle_choice("move_room_b")

        # Verify time advanced
        new_time = state.time_hhmm
        new_hh, new_mm = map(int, new_time.split(':'))
        total_initial_minutes = initial_hh * 60 + initial_mm
        total_new_minutes = new_hh * 60 + new_mm

        # Should have advanced by base_time (5 minutes)
        assert total_new_minutes == total_initial_minutes + 5

    @pytest.mark.asyncio
    async def test_movement_to_undiscovered_location_fails(self, game_with_movement, mock_ai_service):
        """Test that movement to undiscovered locations is blocked."""
        engine = GameEngine(game_with_movement, session_id="test-undiscovered", ai_service=mock_ai_service)
        state = engine.state_manager.state

        # Remove room_b from discovered locations
        state.discovered_locations = [loc for loc in state.discovered_locations if loc != "room_b"]

        # Try to move
        result = await engine.movement.handle_choice("move_room_b")

        # Should remain in room_a
        assert state.location_current == "room_a"


class TestNPCCompanions:
    """Test NPC companion movement willingness."""

    @pytest.mark.asyncio
    async def test_willing_npc_follows_player(self, game_with_movement, mock_ai_service):
        """Test that willing NPCs follow the player."""
        engine = GameEngine(game_with_movement, session_id="test-willing-npc", ai_service=mock_ai_service)
        state = engine.state_manager.state

        # Discover room_b (movement requires it)
        if "room_b" not in state.discovered_locations:
            state.discovered_locations.append("room_b")

        # Add friend to current location
        state.present_chars = ["player", "friend"]

        # Move to room_b (friend is willing to go there)
        result = await engine.movement.handle_choice("move_room_b")

        # Verify friend moved with player
        assert "friend" in state.present_chars
        assert state.location_current == "room_b"

    @pytest.mark.asyncio
    async def test_unwilling_npc_blocks_movement(self, game_with_movement, mock_ai_service):
        """Test that unwilling NPCs block movement."""
        engine = GameEngine(game_with_movement, session_id="test-unwilling-npc", ai_service=mock_ai_service)
        state = engine.state_manager.state

        # Add friend to current location
        state.present_chars = ["player", "friend"]

        # Try to move to room_a (friend has no willingness rule for room_a from room_b)
        # First move to room_b
        state.location_current = "room_b"
        if "room_a" not in state.discovered_locations:
            state.discovered_locations.append("room_a")

        # Now try to move back to room_a (no willingness rule)
        result = await engine.movement.handle_choice("move_room_a")

        # Should be blocked and remain in room_b
        assert state.location_current == "room_b"
        assert "hesitant" in result["narrative"] or "don't want" in result["narrative"]


class TestFreeformMovement:
    """Test freeform text-based movement."""

    @pytest.mark.asyncio
    async def test_freeform_movement_with_location_name(self, game_with_movement, mock_ai_service):
        """Test that freeform text containing location name triggers movement."""
        engine = GameEngine(game_with_movement, session_id="test-freeform", ai_service=mock_ai_service)
        state = engine.state_manager.state

        # Discover room_b (movement requires it)
        if "room_b" not in state.discovered_locations:
            state.discovered_locations.append("room_b")

        # Try freeform movement
        result = await engine.movement.handle_freeform("go to room_b")

        # Should move to room_b
        assert state.location_current == "room_b"

    @pytest.mark.asyncio
    async def test_freeform_detects_movement_keywords(self):
        """Test that movement service detects movement keywords."""
        from app.engine.movement import MovementService

        # Positive cases
        assert MovementService.is_movement_action("go north")
        assert MovementService.is_movement_action("walk to the library")
        assert MovementService.is_movement_action("run away")
        assert MovementService.is_movement_action("head downtown")
        assert MovementService.is_movement_action("travel to paris")
        assert MovementService.is_movement_action("enter the room")
        assert MovementService.is_movement_action("exit quickly")
        assert MovementService.is_movement_action("leave now")

        # Negative cases
        assert not MovementService.is_movement_action("talk to friend")
        assert not MovementService.is_movement_action("examine the painting")
        assert not MovementService.is_movement_action("pick up the key")


class TestMovementEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_movement_with_no_connections(self, game_with_movement, mock_ai_service):
        """Test movement when location has no connections."""
        engine = GameEngine(game_with_movement, session_id="test-no-connections", ai_service=mock_ai_service)
        state = engine.state_manager.state

        # Move to room_c which has no connections
        state.location_current = "room_c"
        state.zone_current = "zone2"

        # Try freeform movement
        result = await engine.movement.handle_freeform("go somewhere")

        # Should fail gracefully
        assert "nowhere to go" in result["narrative"].lower()
        assert state.location_current == "room_c"

    @pytest.mark.asyncio
    async def test_invalid_movement_choice(self, game_with_movement, mock_ai_service):
        """Test handling of invalid movement choice."""
        engine = GameEngine(game_with_movement, session_id="test-invalid", ai_service=mock_ai_service)

        # Try invalid choice
        result = await engine.movement.handle_choice("move_nonexistent")

        # Should fail gracefully
        assert "can't seem to go that way" in result["narrative"].lower()


@pytest.fixture
def game_with_zone_travel() -> GameDefinition:
    """Create a game with multiple zones and transport connections for zone travel testing."""
    from app.models.locations import ZoneConnection

    game = GameDefinition(
        meta=MetaConfig(
            id="zone_travel_test",
            title="Zone Travel Test Game",
            version="1.0.0"
        ),
        start=GameStart(
            node="start",
            location="downtown_plaza",
            day=1,
            slot="morning"
        ),
        time=Time(
            mode="hybrid",
            slots=["morning", "afternoon", "evening"],
            minutes_per_action=10,
            actions_per_slot=3,
            slot_windows={
                "morning": {"start": "06:00", "end": "12:00"},
                "afternoon": {"start": "12:00", "end": "18:00"},
                "evening": {"start": "18:00", "end": "23:00"}
            }
        ),
        meters=MetersTemplate(
            player={
                "energy": Meter(min=0, max=100, default=100, visible=True)
            }
        ),
        movement=Movement(
            base_time=5,
            methods=[
                {"walk": 10},
                {"bus": 5}
            ]
        ),
        characters=[
            Character(
                id="player",
                name="You",
                age=20,
                gender="unspecified"
            )
        ],
        zones=[
            Zone(
                id="downtown",
                name="Downtown",
                locations=[
                    Location(
                        id="downtown_plaza",
                        name="Downtown Plaza",
                        description="The central plaza downtown."
                    )
                ],
                connections=[
                    ZoneConnection(
                        to=["campus"],
                        methods=["walk", "bus"],
                        distance=2.0,
                        description="To the university campus"
                    )
                ]
            ),
            Zone(
                id="campus",
                name="University Campus",
                locations=[
                    Location(
                        id="campus_quad",
                        name="Campus Quad",
                        description="The main quad at the university."
                    )
                ],
                connections=[
                    ZoneConnection(
                        to=["downtown"],
                        methods=["walk", "bus"],
                        distance=2.0,
                        description="Back to downtown"
                    )
                ]
            )
        ],
        nodes=[
            Node(id="start", type="scene", title="Start")
        ]
    )
    return game


class TestZoneTravel:
    """Test zone travel between different zones."""

    @pytest.mark.asyncio
    async def test_zone_travel_changes_zone_and_location(self, game_with_zone_travel, mock_ai_service):
        """Test that zone travel updates both zone and location."""
        engine = GameEngine(game_with_zone_travel, session_id="test-zone-travel", ai_service=mock_ai_service)
        state = engine.state_manager.state

        # Initial state
        assert state.zone_current == "downtown"
        assert state.location_current == "downtown_plaza"

        # Travel to campus zone
        result = await engine.movement.handle_choice("travel_campus")

        # Should have changed zone and location
        assert state.zone_current == "campus"
        assert state.location_current == "campus_quad"
        assert "Campus" in result["narrative"] or "campus" in result["narrative"].lower()

    @pytest.mark.asyncio
    async def test_zone_travel_consumes_time_based_on_distance(self, game_with_zone_travel, mock_ai_service):
        """Test that zone travel time is calculated as base_time * distance."""
        engine = GameEngine(game_with_zone_travel, session_id="test-zone-time", ai_service=mock_ai_service)
        state = engine.state_manager.state

        # Record initial time
        initial_time = state.time_hhmm
        initial_hh, initial_mm = map(int, initial_time.split(':'))

        # Travel to campus (distance=2.0, first method base_time=10, so 10 * 2 = 20 minutes)
        await engine.movement.handle_choice("travel_campus")

        # Verify time advanced by 20 minutes
        new_time = state.time_hhmm
        new_hh, new_mm = map(int, new_time.split(':'))
        total_initial = initial_hh * 60 + initial_mm
        total_new = new_hh * 60 + new_mm

        # Should have advanced by base_time * distance = 10 * 2 = 20 minutes
        assert total_new == total_initial + 20

    @pytest.mark.asyncio
    async def test_zone_travel_to_nonexistent_zone(self, game_with_zone_travel, mock_ai_service):
        """Test that traveling to nonexistent zone fails gracefully."""
        engine = GameEngine(game_with_zone_travel, session_id="test-bad-zone", ai_service=mock_ai_service)
        state = engine.state_manager.state

        # Try to travel to non-existent zone
        result = await engine.movement.handle_choice("travel_nonexistent")

        # Should remain in original zone
        assert state.zone_current == "downtown"
        assert "can't seem to go that way" in result["narrative"].lower()

    @pytest.mark.asyncio
    async def test_zone_travel_updates_previous_location(self, game_with_zone_travel, mock_ai_service):
        """Test that zone travel tracks previous location."""
        engine = GameEngine(game_with_zone_travel, session_id="test-zone-prev", ai_service=mock_ai_service)
        state = engine.state_manager.state

        initial_location = state.location_current

        # Travel to campus
        await engine.movement.handle_choice("travel_campus")

        # Previous location should be set
        assert state.location_previous == initial_location
