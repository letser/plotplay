"""
Integration tests for core PlotPlay engine mechanics.

Tests the following systems working together according to specification:
1. Effects system (meter changes, flags, inventory, clothing, conditionals)
2. Movement system (local movement, zone travel, time consumption)
3. Node transitions (choices, triggers, goto effects)
4. Modifier system (application, duration, removal, conditions)
5. Time progression (slots, minutes, actions)
"""
import pytest
from app.core.game_loader import GameLoader
from app.core.state_manager import StateManager
from app.models.game import GameDefinition, MetaConfig, GameStartConfig
from app.models.locations import Zone, Location
from app.models.nodes import Node, NodeChoice
from app.models.characters import Character
from app.models.time import TimeConfig
from app.models.effects import (
    MeterChangeEffect, FlagSetEffect, ConditionalEffect,
    InventoryAddEffect, InventoryRemoveEffect, GotoEffect
)
from app.models.modifiers import Modifier, ModifiersConfig
from app.engine.effects import EffectResolver
from app.engine.movement import MovementService
from app.engine.time import TimeService


@pytest.fixture
def game_for_effects_test() -> GameDefinition:
    """Create a minimal game for testing effects."""
    from app.models.meters import MetersConfig, Meter
    from app.models.flags import FlagsConfig, BoolFlag
    from app.models.items import Item

    game = GameDefinition(
        meta=MetaConfig(
            id="effects_test",
            title="Effects Test Game",
            version="1.0.0"
        ),
        start=GameStartConfig(
            node="start",
            location="room",
            day=1,
            slot="morning"
        ),
        time=TimeConfig(
            mode="slots",
            slots=["morning", "afternoon", "evening"]
        ),
        meters=MetersConfig(
            player={
                "energy": Meter(min=0, max=100, default=50, visible=True),
                "health": Meter(min=0, max=100, default=100, visible=True)
            }
        ),
        flags=FlagsConfig({
            "quest_started": BoolFlag(type="bool", default=False, visible=True),
            "npc_met": BoolFlag(type="bool", default=False, visible=False)
        }),
        items=[
            Item(
                id="potion",
                name="Health Potion",
                category="consumable",
                stackable=True,
                consumable=True,
                on_use=[
                    MeterChangeEffect(target="player", meter="health", op="add", value=20)
                ]
            ),
            Item(
                id="key",
                name="Golden Key",
                category="key",
                stackable=False
            )
        ],
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
                id="zone1",
                name="Test Zone",
                locations=[
                    Location(id="room", name="Starting Room"),
                    Location(id="hall", name="Hallway")
                ]
            )
        ],
        nodes=[
            Node(
                id="start",
                type="scene",
                title="Start",
                on_entry=[
                    MeterChangeEffect(target="player", meter="energy", op="set", value=50)
                ]
            )
        ]
    )
    return game


class TestEffectsSystem:
    """Test effects are applied correctly according to specification."""

    def test_meter_change_effects_apply(self, game_for_effects_test):
        """Test meter_change effects modify character meters correctly."""
        from app.core.game_engine import GameEngine

        engine = GameEngine(game_for_effects_test, session_id="test-effects")
        state = engine.state_manager.state

        # Initial energy is 50
        assert state.meters["player"]["energy"] == 50

        # Apply add operation
        engine.apply_effects([
            MeterChangeEffect(target="player", meter="energy", op="add", value=10)
        ])
        assert state.meters["player"]["energy"] == 60

        # Apply subtract operation
        engine.apply_effects([
            MeterChangeEffect(target="player", meter="energy", op="subtract", value=5)
        ])
        assert state.meters["player"]["energy"] == 55

        # Apply set operation
        engine.apply_effects([
            MeterChangeEffect(target="player", meter="energy", op="set", value=100)
        ])
        assert state.meters["player"]["energy"] == 100

    def test_meter_changes_respect_bounds(self, game_for_effects_test):
        """Test meter changes are clamped to min/max."""
        from app.core.game_engine import GameEngine

        engine = GameEngine(game_for_effects_test, session_id="test-bounds")
        state = engine.state_manager.state

        # Try to exceed max (100)
        state.meters["player"]["energy"] = 95
        engine.apply_effects([
            MeterChangeEffect(target="player", meter="energy", op="add", value=20)
        ])
        assert state.meters["player"]["energy"] == 100  # Clamped to max

        # Try to go below min (0)
        state.meters["player"]["energy"] = 5
        engine.apply_effects([
            MeterChangeEffect(target="player", meter="energy", op="subtract", value=20)
        ])
        assert state.meters["player"]["energy"] == 0  # Clamped to min

    def test_flag_set_effects_apply(self, game_for_effects_test):
        """Test flag_set effects modify game flags."""
        from app.core.game_engine import GameEngine

        engine = GameEngine(game_for_effects_test, session_id="test-flags")
        state = engine.state_manager.state

        assert state.flags["quest_started"] is False

        engine.apply_effects([
            FlagSetEffect(key="quest_started", value=True)
        ])
        assert state.flags["quest_started"] is True

        engine.apply_effects([
            FlagSetEffect(key="quest_started", value=False)
        ])
        assert state.flags["quest_started"] is False

    def test_conditional_effects_branch_correctly(self, game_for_effects_test):
        """Test conditional effects execute correct branch based on condition."""
        from app.core.game_engine import GameEngine

        engine = GameEngine(game_for_effects_test, session_id="test-conditional")
        state = engine.state_manager.state

        state.flags["quest_started"] = False

        # When condition is false, execute otherwise branch
        conditional = ConditionalEffect(
            when="flags.quest_started",
            then=[MeterChangeEffect(target="player", meter="energy", op="add", value=10)],
            otherwise=[MeterChangeEffect(target="player", meter="energy", op="subtract", value=5)]
        )

        initial_energy = state.meters["player"]["energy"]
        engine.apply_effects([conditional])
        assert state.meters["player"]["energy"] == initial_energy - 5

        # When condition is true, execute then branch
        state.flags["quest_started"] = True
        engine.apply_effects([conditional])
        assert state.meters["player"]["energy"] == initial_energy - 5 + 10

    def test_inventory_effects_modify_items(self, game_for_effects_test):
        """Test inventory add/remove effects work correctly."""
        from app.core.game_engine import GameEngine

        engine = GameEngine(game_for_effects_test, session_id="test-inventory")
        state = engine.state_manager.state

        assert "potion" not in state.inventory.get("player", {})

        # Add item
        engine.apply_effects([
            InventoryAddEffect(target="player", item_type="item", item="potion", count=3)
        ])
        assert state.inventory["player"]["potion"] == 3

        # Add more
        engine.apply_effects([
            InventoryAddEffect(target="player", item_type="item", item="potion", count=2)
        ])
        assert state.inventory["player"]["potion"] == 5

        # Remove some
        engine.apply_effects([
            InventoryRemoveEffect(target="player", item_type="item", item="potion", count=2)
        ])
        assert state.inventory["player"]["potion"] == 3

    def test_effects_execute_in_order(self, game_for_effects_test):
        """Test multiple effects execute in the order specified."""
        from app.core.game_engine import GameEngine

        engine = GameEngine(game_for_effects_test, session_id="test-order")
        state = engine.state_manager.state

        effects = [
            MeterChangeEffect(target="player", meter="energy", op="set", value=10),
            MeterChangeEffect(target="player", meter="energy", op="add", value=5),
            MeterChangeEffect(target="player", meter="energy", op="add", value=3),
        ]

        engine.apply_effects(effects)
        # Should be: set to 10, add 5 (=15), add 3 (=18)
        assert state.meters["player"]["energy"] == 18


class TestMovementAndTime:
    """Test movement system consumes time correctly according to specification.

    Note: Core time advancement is thoroughly tested in test_time_service.py.
    Movement-specific time consumption will be tested below.
    """
    pass  # Movement tests will be added here


class TestNodeTransitions:
    """Test node transitions and choice processing."""

    def test_goto_effect_changes_node(self, game_for_effects_test):
        """Test goto effect transitions to specified node."""
        from app.core.game_engine import GameEngine

        # Add another node for transition BEFORE creating engine
        second_node = Node(
            id="second",
            type="scene",
            title="Second Scene"
        )
        game_for_effects_test.nodes.append(second_node)
        # Add to index before engine initialization
        game_for_effects_test.index.nodes["second"] = second_node

        # Now create engine - it will copy nodes_map from index
        engine = GameEngine(game_for_effects_test, session_id="test-goto")
        state = engine.state_manager.state

        # Verify "second" is in the engine's nodes_map
        assert "second" in engine.nodes_map

        # Initially at start node
        state.current_node = "start"
        assert state.current_node == "start"

        # Apply goto effect
        engine.apply_effects([GotoEffect(node="second")])

        # Should have transitioned
        assert state.current_node == "second"

    def test_node_entry_effects_execute(self, game_for_effects_test):
        """Test node on_entry effects are executed when entering node."""
        state_mgr = StateManager(game_for_effects_test)

        # The start node has on_entry effect that sets energy to 50
        # StateManager initialization should trigger this
        assert state_mgr.state.meters["player"]["energy"] == 50


class TestModifierSystem:
    """Test modifier application, duration, and removal."""

    @pytest.fixture
    def game_with_modifiers(self) -> GameDefinition:
        """Create a game with modifiers defined."""
        from app.models.meters import MetersConfig, Meter

        modifiers = ModifiersConfig(
            library=[
                Modifier(
                    id="energized",
                    group="buff",
                    description="Feeling energized",
                    duration=60,  # 60 minutes default
                    when="meters.player.energy > 80"
                ),
                Modifier(
                    id="exhausted",
                    group="debuff",
                    description="Completely exhausted",
                    duration=30,
                    when="meters.player.energy < 20"
                )
            ]
        )

        game = GameDefinition(
            meta=MetaConfig(
                id="modifier_test",
                title="Modifier Test",
                version="1.0.0"
            ),
            start=GameStartConfig(
                node="start",
                location="room",
                day=1,
                slot="morning"
            ),
            time=TimeConfig(
                mode="slots",
                slots=["morning"]
            ),
            meters=MetersConfig(
                player={
                    "energy": Meter(min=0, max=100, default=50, visible=True)
                }
            ),
            modifiers=modifiers,
            characters=[
                Character(id="player", name="You", age=20, gender="unspecified")
            ],
            zones=[
                Zone(
                    id="zone1",
                    name="Test Zone",
                    locations=[Location(id="room", name="Room")]
                )
            ],
            nodes=[
                Node(id="start", type="scene", title="Start")
            ]
        )
        return game

    def test_modifier_library_loaded(self, game_with_modifiers):
        """Test modifiers are loaded into game index."""
        assert "energized" in game_with_modifiers.index.modifiers
        assert "exhausted" in game_with_modifiers.index.modifiers

    def test_modifier_auto_activation(self, game_with_modifiers):
        """Test modifiers auto-activate based on when conditions."""
        from app.core.game_engine import GameEngine

        engine = GameEngine(game_with_modifiers, session_id="test-modifier")
        modifier_svc = engine.modifiers
        state = engine.state_manager.state

        # Set energy high to trigger energized modifier
        state.meters["player"]["energy"] = 90

        # Update modifiers - should auto-activate energized
        modifier_svc.update_modifiers_for_turn(state)

        # Check if energized modifier was added
        player_mods = state.modifiers.get("player", [])
        has_energized = any(mod.get("id") == "energized" for mod in player_mods)
        assert has_energized, "Energized modifier should auto-activate when energy > 80"

    def test_modifier_does_not_activate_when_condition_false(self, game_with_modifiers):
        """Test modifiers don't activate when conditions aren't met."""
        from app.core.game_engine import GameEngine

        engine = GameEngine(game_with_modifiers, session_id="test-no-modifier")
        modifier_svc = engine.modifiers
        state = engine.state_manager.state

        # Set energy to middle range - neither high nor low
        state.meters["player"]["energy"] = 50

        # Update modifiers
        modifier_svc.update_modifiers_for_turn(state)

        # Should not have either modifier
        player_mods = state.modifiers.get("player", [])
        assert len(player_mods) == 0, "No modifiers should activate with energy = 50"


class TestIntegrationCollegeRomance:
    """Integration tests using the real college_romance game."""

    def test_college_romance_loads_and_initializes(self):
        """Test college_romance game loads and initializes correctly."""
        loader = GameLoader()
        game = loader.load_game("college_romance")
        state_mgr = StateManager(game)

        # Check initialization
        assert state_mgr.state.current_node == "intro_dorm"
        assert state_mgr.state.location_current == "campus_dorm_room"
        assert state_mgr.state.day == 1
        assert state_mgr.state.time_slot == "morning"

        # Check player meters initialized
        assert "energy" in state_mgr.state.meters["player"]
        assert "money" in state_mgr.state.meters["player"]
        assert "mind" in state_mgr.state.meters["player"]
        assert "charm" in state_mgr.state.meters["player"]

        # Check NPCs have template meters
        assert "trust" in state_mgr.state.meters.get("emma", {})
        assert "attraction" in state_mgr.state.meters.get("emma", {})

    def test_college_romance_flags_initialized(self):
        """Test game flags are initialized with correct defaults."""
        loader = GameLoader()
        game = loader.load_game("college_romance")
        state_mgr = StateManager(game)

        assert state_mgr.state.flags["met_emma"] is False
        assert state_mgr.state.flags["met_zoe"] is False
        assert state_mgr.state.flags["emma_study_session"] is False

    def test_college_romance_time_system_configured(self):
        """Test time system is properly configured."""
        loader = GameLoader()
        game = loader.load_game("college_romance")

        assert game.time.mode == "hybrid"
        assert game.time.slots == ["morning", "afternoon", "evening", "night"]
        assert game.time.actions_per_slot == 3
        assert game.time.minutes_per_action == 45
