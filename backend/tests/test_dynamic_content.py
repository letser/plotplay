"""
Tests for dynamic content systems in PlotPlay v3.
"""
import pytest
from app.core.game_engine import GameEngine
from app.core.event_manager import EventManager
from app.core.arc_manager import ArcManager
from app.models.event import Event, EventChoice
from app.models.arc import Arc, Milestone
from app.models.location import LocationPrivacy
from app.models.effects import *


class TestEventManager:
    """Tests for the event system."""

    def test_event_trigger_conditions(self, minimal_game_def):
        """Test that events trigger when conditions are met."""
        # Add test event
        test_event = Event(
            id="test_event",
            name="Test Event",
            description="A test event",
            trigger={
                "conditions": ["meters.player.health < 50"],
                "locations": ["test_location"],
                "chars_present": ["emma"]
            },
            on_trigger="You feel weak...",
            choices=[
                EventChoice(
                    id="rest",
                    text="Rest",
                    effects=[
                        MeterChangeEffect(
                            target="player",
                            meter="health",
                            op="add",
                            value=20
                        )
                    ]
                )
            ]
        )

        minimal_game_def.events = {"test_event": test_event}

        engine = GameEngine(minimal_game_def, "test_events")
        manager = EventManager(minimal_game_def)

        # Setup triggering conditions
        state = engine.state_manager.state
        state.meters["player"]["health"] = 40
        state.location_current = "test_location"
        state.present_chars = ["emma"]

        # Check for events
        triggered = manager.check_events(state)

        assert len(triggered) == 1
        assert triggered[0].id == "test_event"

    def test_event_cooldown(self, minimal_game_def):
        """Test that event cooldowns work correctly."""
        test_event = Event(
            id="cooldown_event",
            name="Cooldown Event",
            trigger={"conditions": ["true"]},
            cooldown=3,
            on_trigger="Event triggered",
            choices=[]
        )

        minimal_game_def.events = {"cooldown_event": test_event}

        engine = GameEngine(minimal_game_def, "test_cooldown")
        manager = EventManager(minimal_game_def)
        state = engine.state_manager.state

        # First trigger
        triggered = manager.check_events(state)
        assert len(triggered) == 1

        # Mark as triggered
        state.event_cooldowns["cooldown_event"] = 3

        # Should not trigger while on cooldown
        state.event_cooldowns["cooldown_event"] = 2
        triggered = manager.check_events(state)
        assert len(triggered) == 0

        # Should trigger again after cooldown
        state.event_cooldowns["cooldown_event"] = 0
        triggered = manager.check_events(state)
        assert len(triggered) == 1

    def test_event_priority(self, minimal_game_def):
        """Test that higher priority events trigger first."""
        high_priority = Event(
            id="high",
            priority=10,
            trigger={"conditions": ["true"]},
            on_trigger="High priority",
            choices=[]
        )

        low_priority = Event(
            id="low",
            priority=1,
            trigger={"conditions": ["true"]},
            on_trigger="Low priority",
            choices=[]
        )

        minimal_game_def.events = {
            "high": high_priority,
            "low": low_priority
        }

        manager = EventManager(minimal_game_def)
        state = engine.state_manager.state

        triggered = manager.check_events(state)

        # High priority should be first
        assert triggered[0].id == "high"
        assert triggered[1].id == "low"

    def test_location_privacy_events(self, minimal_game_def):
        """Test events that depend on location privacy."""
        private_event = Event(
            id="private_event",
            trigger={
                "conditions": ["true"],
                "privacy": LocationPrivacy.HIGH
            },
            on_trigger="Private moment",
            choices=[]
        )

        minimal_game_def.events = {"private_event": private_event}

        engine = GameEngine(minimal_game_def, "test_privacy")
        manager = EventManager(minimal_game_def)
        state = engine.state_manager.state

        # Should not trigger in low privacy
        state.location_privacy = LocationPrivacy.LOW
        triggered = manager.check_events(state)
        assert len(triggered) == 0

        # Should trigger in high privacy
        state.location_privacy = LocationPrivacy.HIGH
        triggered = manager.check_events(state)
        assert len(triggered) == 1


class TestArcManager:
    """Tests for the story arc system."""

    def test_milestone_progression(self, minimal_game_def):
        """Test that milestones advance when conditions are met."""
        test_arc = Arc(
            id="test_arc",
            name="Test Arc",
            description="A test story arc",
            milestones=[
                Milestone(
                    id="start",
                    name="Start",
                    condition="meters.player.health > 50",
                    effects=[
                        FlagSetEffect(key="arc_started", value=True)
                    ]
                ),
                Milestone(
                    id="middle",
                    name="Middle",
                    condition="flags.arc_started == true and meters.player.health > 75",
                    effects=[
                        FlagSetEffect(key="arc_middle", value=True)
                    ]
                ),
                Milestone(
                    id="end",
                    name="End",
                    condition="flags.arc_middle == true",
                    effects=[
                        FlagSetEffect(key="arc_complete", value=True)
                    ]
                )
            ]
        )

        minimal_game_def.arcs = {"test_arc": test_arc}

        engine = GameEngine(minimal_game_def, "test_arcs")
        manager = ArcManager(minimal_game_def)
        state = engine.state_manager.state

        # Start with health > 50
        state.meters["player"]["health"] = 60
        completed = manager.check_milestones(state)

        assert "start" in completed
        assert state.flags.get("arc_started") is True
        assert "start" in state.completed_milestones

        # Increase health for middle milestone
        state.meters["player"]["health"] = 80
        completed = manager.check_milestones(state)

        assert "middle" in completed
        assert state.flags.get("arc_middle") is True

        # End should complete automatically
        completed = manager.check_milestones(state)

        assert "end" in completed
        assert state.flags.get("arc_complete") is True

    def test_arc_completion_tracking(self, minimal_game_def):
        """Test that completed milestones are properly tracked."""
        test_arc = Arc(
            id="track_arc",
            name="Track Arc",
            milestones=[
                Milestone(
                    id="m1",
                    name="M1",
                    condition="true",
                    effects=[]
                ),
                Milestone(
                    id="m2",
                    name="M2",
                    condition="true",
                    effects=[]
                )
            ]
        )

        minimal_game_def.arcs = {"track_arc": test_arc}

        engine = GameEngine(minimal_game_def, "test_tracking")
        manager = ArcManager(minimal_game_def)
        state = engine.state_manager.state

        # Complete first milestone
        completed = manager.check_milestones(state)
        assert "m1" in completed
        assert "m1" in state.completed_milestones

        # Should not re-complete
        completed = manager.check_milestones(state)
        assert "m1" not in completed

        # But m2 should complete
        assert "m2" in completed


class TestDynamicChoices:
    """Tests for dynamic choice generation."""

    def test_conditional_choices(self, minimal_game_def):
        """Test that choices appear/hide based on conditions."""
        from app.models.node import Node, Choice

        test_node = Node(
            id="conditional_node",
            type="choice",
            choices=[
                Choice(
                    id="always",
                    text="Always visible",
                    to="start_node"
                ),
                Choice(
                    id="high_health",
                    text="High health only",
                    condition="meters.player.health > 75",
                    to="start_node"
                ),
                Choice(
                    id="has_key",
                    text="Need key",
                    condition="has('key')",
                    to="start_node"
                )
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

        assert "always" in choice_ids
        assert "high_health" not in choice_ids
        assert "has_key" not in choice_ids

        # High health, has key
        state.meters["player"]["health"] = 80
        state.inventory["player"]["key"] = 1

        choices = engine._generate_choices(test_node, [])
        choice_ids = {c["id"] for c in choices}

        assert "always" in choice_ids
        assert "high_health" in choice_ids
        assert "has_key" in choice_ids

    def test_event_choices_merge(self, minimal_game_def):
        """Test that event choices merge with node choices."""
        from app.models.node import Node, Choice

        node_choice = Choice(
            id="node_choice",
            text="From node",
            to="start_node"
        )

        test_node = Node(
            id="merge_node",
            type="choice",
            choices=[node_choice]
        )

        event_choice = EventChoice(
            id="event_choice",
            text="From event",
            effects=[]
        )

        triggered_events = [
            Event(
                id="test",
                on_trigger="Test",
                choices=[event_choice]
            )
        ]

        engine = GameEngine(minimal_game_def, "test_merge")
        choices = engine._generate_choices(test_node, triggered_events)

        choice_ids = {c["id"] for c in choices}
        assert "node_choice" in choice_ids
        assert "event_choice" in choice_ids
        assert len(choices) == 2


class TestEffectProcessing:
    """Tests for complex effect processing."""

    def test_conditional_effects(self, minimal_game_def):
        """Test conditional effect branching."""
        engine = GameEngine(minimal_game_def, "test_conditional")
        state = engine.state_manager.state

        # Create nested conditional
        effect = ConditionalEffect(
            when="meters.player.health > 50",
            then=[
                ConditionalEffect(
                    when="has('key')",
                    then=[
                        FlagSetEffect(key="both_true", value=True)
                    ],
                    else_effects=[
                        FlagSetEffect(key="only_health", value=True)
                    ]
                )
            ],
            else_effects=[
                FlagSetEffect(key="low_health", value=True)
            ]
        )

        # Test with high health and key
        state.meters["player"]["health"] = 75
        state.inventory["player"]["key"] = 1
        engine._apply_conditional_effect(effect)

        assert state.flags.get("both_true") is True
        assert state.flags.get("only_health") is None
        assert state.flags.get("low_health") is None

        # Reset and test with high health, no key
        state.flags = {}
        state.inventory["player"] = {}
        engine._apply_conditional_effect(effect)

        assert state.flags.get("both_true") is None
        assert state.flags.get("only_health") is True
        assert state.flags.get("low_health") is None

    def test_random_effects(self, minimal_game_def):
        """Test random effect selection."""
        engine = GameEngine(minimal_game_def, "test_random_123")  # Fixed seed
        state = engine.state_manager.state

        effect = RandomEffect(
            choices=[
                RandomChoice(
                    weight=50,
                    effects=[FlagSetEffect(key="outcome_a", value=True)]
                ),
                RandomChoice(
                    weight=50,
                    effects=[FlagSetEffect(key="outcome_b", value=True)]
                )
            ]
        )

        # With fixed seed, should be deterministic
        engine._apply_random_effect(effect)

        # One and only one outcome should be selected
        has_a = state.flags.get("outcome_a") is True
        has_b = state.flags.get("outcome_b") is True
        assert has_a != has_b  # XOR - exactly one is true

    def test_complex_meter_operations(self, minimal_game_def):
        """Test multiply, divide, and set operations."""
        minimal_game_def.meters = {
            "player": {
                "health": {"min": 0, "max": 100, "default": 50}
            }
        }

        engine = GameEngine(minimal_game_def, "test_ops")
        state = engine.state_manager.state

        # Test multiply
        state.meters["player"]["health"] = 40
        engine._apply_meter_change(MeterChangeEffect(
            target="player", meter="health", op="multiply", value=2
        ))
        assert state.meters["player"]["health"] == 80

        # Test divide
        engine._apply_meter_change(MeterChangeEffect(
            target="player", meter="health", op="divide", value=4
        ))
        assert state.meters["player"]["health"] == 20

        # Test set
        engine._apply_meter_change(MeterChangeEffect(
            target="player", meter="health", op="set", value=100
        ))
        assert state.meters["player"]["health"] == 100

        # Test clamping on overflow
        engine._apply_meter_change(MeterChangeEffect(
            target="player", meter="health", op="add", value=50
        ))
        assert state.meters["player"]["health"] == 100  # Clamped to max


if __name__ == "__main__":
    pytest.main([__file__, "-v"])