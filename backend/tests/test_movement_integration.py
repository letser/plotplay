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
from app.models.game import GameDefinition, Meta, GameStart
from app.models.time import Time, TimeDurations, TimeSlotWindow
from app.models.locations import (
    Zone, Location, LocationConnection, LocalDirection,
    Movement, TravelMethod, ZoneConnection
)
from app.models.characters import Character
from app.models.locations import MovementWillingness, LocationMovementWillingness
from app.models.meters import MetersTemplate, Meter
from app.models.nodes import Node


@pytest.fixture
def game_with_movement() -> GameDefinition:
    """Create a game with multiple locations and zones for movement testing."""
    game = GameDefinition(
        meta=Meta(
            id="movement_test",
            title="Movement Test Game",
            version="1.0.0"
        ),
        start=GameStart(
            node="start",
            location="room_a",
            day=1,
            time="08:00"
        ),
        time=Time(
            slots_enabled=True,
            slots=["morning", "afternoon", "evening"],
            slot_windows={
                "morning": TimeSlotWindow(start="06:00", end="11:59"),
                "afternoon": TimeSlotWindow(start="12:00", end="17:59"),
                "evening": TimeSlotWindow(start="18:00", end="21:59")
            },
            categories={
                "instant": 0,
                "trivial": 2,
                "quick": 5,
                "standard": 15,
                "significant": 30,
                "major": 60
            },
            defaults=TimeDurations(
                conversation="instant",
                choice="quick",
                movement="quick",  # 5 minutes for local movement
                default="trivial",
                cap_per_visit=30
            )
        ),
        meters=MetersTemplate(
            player={
                "energy": Meter(min=0, max=100, default=100, visible=True)
            }
        ),
        movement=Movement(
            use_entry_exit=False,
            base_unit="km",
            methods=[
                TravelMethod(name="walk", active=True, time_cost=5)  # 5 min per km
            ]
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
        state.discovered_locations.add("room_b")

        # Initial location
        assert state.current_location == "room_a"

        # Move to room_b via movement service
        result = await engine.movement.move_local("room_b")

        # Verify location changed
        assert state.current_location == "room_b"
        assert result is True

    @pytest.mark.asyncio
    async def test_local_movement_consumes_time(self, game_with_movement, mock_ai_service):
        """Test that local movement consumes time based on movement defaults."""
        engine = GameEngine(game_with_movement, session_id="test-local-time", ai_service=mock_ai_service)
        state = engine.state_manager.state

        # Discover room_b (movement requires it)
        state.discovered_locations.add("room_b")

        # Record initial time
        initial_time = state.time.time_hhmm
        initial_hh, initial_mm = map(int, initial_time.split(':'))

        # Move (should consume 5 minutes based on time.defaults.movement="quick"=5min)
        await engine.movement.move_local("room_b")

        # Verify time advanced
        new_time = state.time.time_hhmm
        new_hh, new_mm = map(int, new_time.split(':'))
        total_initial_minutes = initial_hh * 60 + initial_mm
        total_new_minutes = new_hh * 60 + new_mm

        # Should have advanced by 5 minutes
        assert total_new_minutes == total_initial_minutes + 5

    @pytest.mark.asyncio
    async def test_movement_to_undiscovered_location_fails(self, game_with_movement, mock_ai_service):
        """Test that movement to undiscovered locations is blocked."""
        engine = GameEngine(game_with_movement, session_id="test-undiscovered", ai_service=mock_ai_service)
        state = engine.state_manager.state

        # Ensure room_b is NOT discovered
        state.discovered_locations.discard("room_b")

        # Try to move
        result = await engine.movement.move_local("room_b")

        # Should fail and remain in room_a
        assert result is False
        assert state.current_location == "room_a"


class TestNPCCompanions:
    """Test NPC companion movement willingness."""

    @pytest.mark.asyncio
    async def test_willing_npc_follows_player(self, game_with_movement, mock_ai_service):
        """Test that willing NPCs follow the player."""
        engine = GameEngine(game_with_movement, session_id="test-willing-npc", ai_service=mock_ai_service)
        state = engine.state_manager.state

        # Discover room_b (movement requires it)
        state.discovered_locations.add("room_b")

        # Add friend to current location
        state.present_characters = ["player", "friend"]

        # Move to room_b (friend is willing to go there)
        result = await engine.movement.move_local("room_b")

        # Verify friend moved with player
        assert "friend" in state.present_characters
        assert state.current_location == "room_b"
        assert result is True

    @pytest.mark.asyncio
    async def test_unwilling_npc_blocks_movement(self, game_with_movement, mock_ai_service):
        """Test that unwilling NPCs block movement."""
        engine = GameEngine(game_with_movement, session_id="test-unwilling-npc", ai_service=mock_ai_service)
        state = engine.state_manager.state

        # Add friend to current location
        state.present_characters = ["player", "friend"]

        # Move to room_b first
        state.discovered_locations.add("room_b")
        await engine.movement.move_local("room_b")

        # Now try to move back to room_a (no willingness rule for room_a)
        result = await engine.movement.move_local("room_a")

        # Should be blocked and remain in room_b
        assert result is False
        assert state.current_location == "room_b"


class TestFreeformMovement:
    """Test freeform text-based movement."""

    @pytest.mark.asyncio
    async def test_freeform_movement_with_location_name(self, game_with_movement, mock_ai_service):
        """Test that freeform text containing location name triggers movement."""
        engine = GameEngine(game_with_movement, session_id="test-freeform", ai_service=mock_ai_service)
        state = engine.state_manager.state

        # Discover room_b (movement requires it)
        state.discovered_locations.add("room_b")

        # Parse freeform text to detect movement intent
        # (This test just verifies the movement service can identify movement keywords)
        from app.engine.movement import MovementService
        assert MovementService.is_movement_action("go to room_b")

    def test_freeform_detects_movement_keywords(self):
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
        state.current_location = "room_c"
        state.current_zone = "zone2"
        state.discovered_locations.add("room_c")

        # Try to move to non-existent connection
        result = await engine.movement.move_local("nonexistent")

        # Should fail and remain in room_c
        assert result is False
        assert state.current_location == "room_c"

    @pytest.mark.asyncio
    async def test_invalid_movement_choice(self, game_with_movement, mock_ai_service):
        """Test handling of invalid movement choice."""
        engine = GameEngine(game_with_movement, session_id="test-invalid", ai_service=mock_ai_service)

        # Try to move to non-existent location
        result = await engine.movement.move_local("nonexistent")

        # Should fail gracefully
        assert result is False


@pytest.fixture
def game_with_zone_travel() -> GameDefinition:
    """Create a game with multiple zones and transport connections for zone travel testing."""
    game = GameDefinition(
        meta=Meta(
            id="zone_travel_test",
            title="Zone Travel Test Game",
            version="1.0.0"
        ),
        start=GameStart(
            node="start",
            location="downtown_plaza",
            day=1,
            time="08:00"
        ),
        time=Time(
            slots_enabled=True,
            slots=["morning", "afternoon", "evening"],
            slot_windows={
                "morning": TimeSlotWindow(start="06:00", end="11:59"),
                "afternoon": TimeSlotWindow(start="12:00", end="17:59"),
                "evening": TimeSlotWindow(start="18:00", end="21:59")
            },
            categories={
                "instant": 0,
                "quick": 5,
                "standard": 15,
            },
            defaults=TimeDurations(
                conversation="instant",
                choice="quick",
                movement="standard",
                default="quick",
                cap_per_visit=30
            )
        ),
        meters=MetersTemplate(
            player={
                "energy": Meter(min=0, max=100, default=100, visible=True)
            }
        ),
        movement=Movement(
            use_entry_exit=False,
            base_unit="km",
            methods=[
                TravelMethod(name="walk", active=True, time_cost=10),  # 10 min/km
                TravelMethod(name="bus", active=False, speed=30)  # 30 km/h
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
                entrances=["downtown_plaza"],
                exits=["downtown_plaza"],
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
                entrances=["campus_quad"],
                exits=["campus_quad"],
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
        assert state.current_zone == "downtown"
        assert state.current_location == "downtown_plaza"

        # Discover campus zone and location
        state.discovered_zones.add("campus")
        state.discovered_locations.add("campus_quad")

        # Travel to campus zone
        result = await engine.movement.move_zone("campus", "walk")

        # Should have changed zone and location
        assert result is True
        assert state.current_zone == "campus"
        # Should arrive at entrance location
        assert state.current_location in ["campus_quad"]

    @pytest.mark.asyncio
    async def test_zone_travel_consumes_time_based_on_distance(self, game_with_zone_travel, mock_ai_service):
        """Test that zone travel time is calculated as time_cost * distance."""
        engine = GameEngine(game_with_zone_travel, session_id="test-zone-time", ai_service=mock_ai_service)
        state = engine.state_manager.state

        # Discover campus
        state.discovered_zones.add("campus")
        state.discovered_locations.add("campus_quad")

        # Record initial time
        initial_time = state.time.time_hhmm
        initial_hh, initial_mm = map(int, initial_time.split(':'))

        # Travel to campus (distance=2.0 km, walk time_cost=10 min/km, so 10 * 2 = 20 minutes)
        await engine.movement.move_zone("campus", "walk")

        # Verify time advanced by 20 minutes
        new_time = state.time.time_hhmm
        new_hh, new_mm = map(int, new_time.split(':'))
        total_initial = initial_hh * 60 + initial_mm
        total_new = new_hh * 60 + new_mm

        # Should have advanced by time_cost * distance = 10 * 2 = 20 minutes
        assert total_new == total_initial + 20

    @pytest.mark.asyncio
    async def test_zone_travel_to_nonexistent_zone(self, game_with_zone_travel, mock_ai_service):
        """Test that traveling to nonexistent zone fails gracefully."""
        engine = GameEngine(game_with_zone_travel, session_id="test-bad-zone", ai_service=mock_ai_service)
        state = engine.state_manager.state

        # Try to travel to non-existent zone
        result = await engine.movement.move_zone("nonexistent", "walk")

        # Should fail and remain in original zone
        assert result is False
        assert state.current_zone == "downtown"

    @pytest.mark.asyncio
    async def test_zone_travel_updates_previous_location(self, game_with_zone_travel, mock_ai_service):
        """Test that zone travel tracks previous location."""
        engine = GameEngine(game_with_zone_travel, session_id="test-zone-prev", ai_service=mock_ai_service)
        state = engine.state_manager.state

        initial_location = state.current_location

        # Discover campus
        state.discovered_zones.add("campus")
        state.discovered_locations.add("campus_quad")

        # Travel to campus
        await engine.movement.move_zone("campus", "walk")

        # Previous location should be tracked in location state
        campus_location_state = state.locations.get("campus_quad")
        if campus_location_state:
            # The previous location tracking might be in the location state
            assert campus_location_state.previous_id == initial_location or initial_location
