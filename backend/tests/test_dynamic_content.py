"""
Tests for dynamic content systems in PlotPlay v3.
"""
import pytest
from app.core.game_engine import GameEngine
from app.core.event_manager import EventManager
from app.core.arc_manager import ArcManager
from app.models.events import Event, EventTrigger
from app.models.node import Choice
from app.models.arc import Arc, Stage
from app.models.flags import Flag
from app.models.effects import FlagSetEffect, MeterChangeEffect

class TestEventManager:
    """Tests for the event system."""

    def test_event_trigger_conditions(self, minimal_game_def):
        """Test that events trigger when conditions are met."""
        test_event = Event(
            id="test_event",
            title="Test Event",
            trigger=EventTrigger(
                conditional=[{"when": "meters.player.health < 50"}]
            ),
            narrative="You feel weak...",
            choices=[
                Choice(
                    id="rest",
                    prompt="Rest",
                    effects=[
                        MeterChangeEffect(type="meter_change", target="player", meter="health", op="add", value=20)
                    ]
                )
            ]
        )
        minimal_game_def.events.append(test_event)

        engine = GameEngine(minimal_game_def, "test_events")
        manager = EventManager(minimal_game_def)
        state = engine.state_manager.state

        # Conditions not met
        state.meters["player"]["health"] = 60
        triggered = manager.get_triggered_events(state)
        assert len(triggered) == 0

        # Conditions met
        state.meters["player"]["health"] = 40
        triggered = manager.get_triggered_events(state)
        assert len(triggered) == 1
        assert triggered[0].id == "test_event"

    def test_event_cooldown(self, minimal_game_def):
        """Test that event cooldowns work correctly."""
        test_event = Event(
            id="cooldown_event",
            title="Cooldown Event",
            trigger=EventTrigger(conditional=[{"when": "true"}]),
            cooldown={"turns": 3},
            narrative="Event triggered"
        )
        minimal_game_def.events.append(test_event)

        engine = GameEngine(minimal_game_def, "test_cooldown")
        manager = EventManager(minimal_game_def)
        state = engine.state_manager.state

        # First trigger, which will set the cooldown
        triggered = manager.get_triggered_events(state)
        assert len(triggered) == 1
        assert "cooldown_event" in state.cooldowns
        assert state.cooldowns["cooldown_event"] == 3

        # Should not trigger while on cooldown
        triggered = manager.get_triggered_events(state)
        assert len(triggered) == 0

        # Manually decrement cooldown to test expiration
        state.cooldowns["cooldown_event"] = 1
        manager.decrement_cooldowns(state)

        # Assert that the cooldown is now gone because it reached 0 and was cleaned up
        assert "cooldown_event" not in state.cooldowns

        # Should trigger again now that the cooldown is expired
        triggered = manager.get_triggered_events(state)
        assert len(triggered) == 1

    def test_location_scope_events(self, minimal_game_def):
        """Test events that are scoped to a specific location."""
        scoped_event = Event(
            id="scoped_event",
            title="Scoped Event",
            scope="location",
            location="test_location",
            trigger=EventTrigger(conditional=[{"when": "true"}]),
            narrative="A location-specific event"
        )
        minimal_game_def.events.append(scoped_event)

        engine = GameEngine(minimal_game_def, "test_privacy")
        manager = EventManager(minimal_game_def)
        state = engine.state_manager.state

        # Should trigger in the correct location
        state.location_current = "test_location"
        triggered = manager.get_triggered_events(state)
        assert len(triggered) == 1
        assert triggered[0].id == "scoped_event"

        # Should NOT trigger in a different location
        state.location_current = "another_location"
        triggered = manager.get_triggered_events(state)
        assert len(triggered) == 0


class TestArcManager:
    """Tests for the story arc system."""

    def test_stage_progression(self, minimal_game_def):
        """Test that stages advance when conditions are met."""
        test_arc = Arc(
            id="test_arc",
            name="Test Arc",
            stages=[
                Stage(id="start", name="Start", advance_when="meters.player.health > 50"),
                Stage(id="middle", name="Middle", advance_when="meters.player.health > 75"),
                Stage(id="end", name="End", advance_when="meters.player.health == 100"),
            ]
        )
        minimal_game_def.arcs.append(test_arc)

        engine = GameEngine(minimal_game_def, "test_arcs")
        manager = ArcManager(minimal_game_def)
        state = engine.state_manager.state

        # Initial state, no progression
        state.meters["player"]["health"] = 50
        entered, exited = manager.check_and_advance_arcs(state)
        assert not entered
        assert not exited

        # Advance to 'start'
        state.meters["player"]["health"] = 60
        entered, exited = manager.check_and_advance_arcs(state)
        assert len(entered) == 1
        assert entered[0].id == "start"
        assert state.active_arcs["test_arc"] == "start"
        assert "start" in state.completed_milestones

        # Advance to 'middle', exiting 'start'
        state.meters["player"]["health"] = 80
        entered, exited = manager.check_and_advance_arcs(state)
        assert len(entered) == 1
        assert len(exited) == 1
        assert entered[0].id == "middle"
        assert exited[0].id == "start"
        assert state.active_arcs["test_arc"] == "middle"

    def test_arc_effects_on_advance(self, minimal_game_def):
        """Test that effects are applied when a stage advances."""
        test_arc = Arc(
            id="effect_arc",
            name="Effect Arc",
            stages=[
                Stage(
                    id="trigger_effect",
                    name="Trigger Effect",
                    advance_when="meters.player.health > 90",
                    effects_on_enter=[FlagSetEffect(type="flag_set", key="arc_started", value=True)],
                    effects_on_advance=[FlagSetEffect(type="flag_set", key="arc_advanced", value=True)]
                )
            ]
        )
        minimal_game_def.arcs.append(test_arc)
        # Use the Flag model to add flags, not a dictionary
        minimal_game_def.flags["arc_started"] = Flag(type="bool", default=False)
        minimal_game_def.flags["arc_advanced"] = Flag(type="bool", default=False)

        engine = GameEngine(minimal_game_def, "test_arc_effects")
        state = engine.state_manager.state

        state.meters["player"]["health"] = 95
        entered_stages, _ = engine.arc_manager.check_and_advance_arcs(state)

        # Apply the effects from the newly entered stages
        for stage in entered_stages:
            engine.apply_effects(stage.effects_on_enter)
            engine.apply_effects(stage.effects_on_advance)

        assert state.flags.get("arc_started") is True
        assert state.flags.get("arc_advanced") is True


class TestDynamicChoices:
    """Tests for dynamic choice generation."""

    def test_conditional_choices(self, minimal_game_def):
        """Test that choices appear/hide based on conditions."""
        from app.models.node import Node, NodeType

        test_node = Node(
            id="conditional_node",
            type=NodeType.SCENE,
            title="Conditional Choices",
            choices=[
                Choice(id="always", prompt="Always visible"),
                Choice(id="high_health", prompt="High health only", conditions="meters.player.health > 75"),
                Choice(id="has_key", prompt="Need key", conditions="has('key')")
            ]
        )
        minimal_game_def.nodes.append(test_node)

        engine = GameEngine(minimal_game_def, "test_choices")
        state = engine.state_manager.state

        # Low health, no key
        state.meters["player"]["health"] = 50
        state.inventory["player"] = {}
        choices = engine._generate_choices(test_node, [])
        choice_ids = {c["id"] for c in choices}
        assert choice_ids == {"always"}

        # High health, has key
        state.meters["player"]["health"] = 80
        if not state.inventory.get("player"):
            state.inventory["player"] = {}
        state.inventory["player"]["key"] = 1
        choices = engine._generate_choices(test_node, [])
        choice_ids = {c["id"] for c in choices}
        assert choice_ids == {"always", "high_health", "has_key"}

    def test_event_choices_merge(self, minimal_game_def):
        """Test that event choices merge with node choices."""
        from app.models.node import Node, NodeType

        test_node = Node(
            id="merge_node", type=NodeType.SCENE, title="Merge",
            choices=[Choice(id="node_choice", prompt="From node")]
        )
        event_choices = [Choice(id="event_choice", prompt="From event")]

        engine = GameEngine(minimal_game_def, "test_merge")
        choices = engine._generate_choices(test_node, event_choices)
        choice_ids = {c["id"] for c in choices}

        # When event choices are present, they should REPLACE node choices
        assert choice_ids == {"event_choice"}