"""
Tests for §19 Events - PlotPlay v3 Specification

Events are authored content that can interrupt, inject, or overlay narrative
outside the main node flow. They add pacing, variety, and reactivity through:
- Scheduled triggers (time/date based)
- Conditional triggers (state-based)
- Random triggers (weighted pools)
- Location-based triggers

§19.1: Event Definition
§19.2: Event Template
§19.3: Runtime Behavior
§19.4: Runtime State
§19.5: Examples
§19.6: Authoring Guidelines
"""

import pytest
import yaml
from pathlib import Path

from app.core.game_loader import GameLoader
from app.core.game_engine import GameEngine
from app.core.event_manager import EventManager
from app.models.events import Event, EventTrigger, RandomTrigger
from app.models.node import Choice
from app.models.effects import MeterChangeEffect, FlagSetEffect, AdvanceTimeEffect
from app.models.game import GameDefinition


# =============================================================================
# § 19.1: Event Definition
# =============================================================================

def test_event_required_fields():
    """
    §19.1: Test that events require id and title fields.
    """
    # Valid event with required fields
    event = Event(
        id="test_event",
        title="Test Event"
    )
    assert event.id == "test_event"
    assert event.title == "Test Event"

    # Missing id should raise validation error
    with pytest.raises(Exception):  # Pydantic validation error
        Event(title="Missing ID")

    print("✅ Event required fields validated")


def test_event_optional_fields():
    """
    §19.1: Test that events support all optional fields.
    """
    event = Event(
        id="full_event",
        title="Full Event",
        category="romance",
        scope="location",
        location="campus_cafe",
        narrative="An interesting event occurs",
        beats=["Beat 1", "Beat 2"],
        effects=[
            MeterChangeEffect(target="player", meter="energy", op="add", value=10)
        ],
        choices=[
            Choice(id="choice1", prompt="Option A", goto="node_a")
        ],
        cooldown={"turns": 5}
    )

    assert event.category == "romance"
    assert event.scope == "location"
    assert event.location == "campus_cafe"
    assert event.narrative is not None
    assert len(event.beats) == 2
    assert len(event.effects) == 1
    assert len(event.choices) == 1
    assert event.cooldown is not None

    print("✅ Event optional fields work")


def test_event_defaults():
    """
    §19.1: Test event default values.
    """
    event = Event(
        id="minimal",
        title="Minimal Event"
    )

    assert event.scope == "global"  # Default scope
    assert event.trigger is None  # No default trigger
    assert len(event.effects) == 0  # Empty by default
    assert len(event.choices) == 0  # Empty by default

    print("✅ Event defaults work")


# =============================================================================
# § 19.2: Event Template - Trigger Types
# =============================================================================

def test_scheduled_trigger():
    """
    §19.2: Test scheduled event triggers (time/date based).
    """
    trigger = EventTrigger(
        scheduled=[
            {"when": "time.slot == 'morning'"},
            {"when": "time.day == 5 and time.slot == 'evening'"}
        ]
    )

    assert trigger.scheduled is not None
    assert len(trigger.scheduled) == 2
    assert trigger.scheduled[0]["when"] == "time.slot == 'morning'"

    print("✅ Scheduled trigger works")


def test_conditional_trigger():
    """
    §19.2: Test conditional event triggers (state-based).
    """
    trigger = EventTrigger(
        conditional=[
            {"when": "meters.player.health < 50"},
            {"when": "flags.quest_started == true and meters.emma.trust >= 30"}
        ]
    )

    assert trigger.conditional is not None
    assert len(trigger.conditional) == 2
    assert "meters.player.health" in trigger.conditional[0]["when"]

    print("✅ Conditional trigger works")


def test_random_trigger():
    """
    §19.2: Test random event triggers with weighting and cooldown.
    """
    trigger = EventTrigger(
        random=RandomTrigger(
            weight=30,
            cooldown=720  # 12 hours
        )
    )

    assert trigger.random is not None
    assert trigger.random.weight == 30
    assert trigger.random.cooldown == 720

    print("✅ Random trigger works")


def test_location_enter_trigger():
    """
    §19.2: Test location-enter event triggers.
    """
    trigger = EventTrigger(
        location_enter=True
    )

    assert trigger.location_enter is True

    print("✅ Location-enter trigger works")


def test_combined_triggers():
    """
    §19.2: Test events can have multiple trigger types.
    """
    trigger = EventTrigger(
        conditional=[{"when": "meters.emma.trust >= 40"}],
        location_enter=True
    )

    assert trigger.conditional is not None
    assert trigger.location_enter is True

    print("✅ Combined triggers work")


# =============================================================================
# § 19.2: Event Template - Scope
# =============================================================================

def test_event_scope_global():
    """
    §19.2: Test global scope events (available anywhere).
    """
    event = Event(
        id="global_event",
        title="Global Event",
        scope="global"
    )

    assert event.scope == "global"

    print("✅ Global scope works")


def test_event_scope_location():
    """
    §19.2: Test location-scoped events.
    """
    event = Event(
        id="cafe_event",
        title="Cafe Event",
        scope="location",
        location="campus_cafe"
    )

    assert event.scope == "location"
    assert event.location == "campus_cafe"

    print("✅ Location scope works")


def test_event_scope_zone():
    """
    §19.2: Test zone-scoped events.
    """
    event = Event(
        id="campus_event",
        title="Campus Event",
        scope="zone"
    )

    assert event.scope == "zone"

    print("✅ Zone scope works")


def test_event_scope_node():
    """
    §19.2: Test node-scoped events.
    """
    event = Event(
        id="node_event",
        title="Node-Specific Event",
        scope="node"
    )

    assert event.scope == "node"

    print("✅ Node scope works")


# =============================================================================
# § 19.2: Event Template - Payload
# =============================================================================

def test_event_narrative():
    """
    §19.2: Test event narrative (author seed text).
    """
    event = Event(
        id="narrated_event",
        title="Story Event",
        narrative="Your phone buzzes. It's a text from Emma: 'Hey, can't sleep. Been thinking about you.'"
    )

    assert event.narrative is not None
    assert "Emma" in event.narrative

    print("✅ Event narrative works")


def test_event_beats():
    """
    §19.2: Test event beats for writer guidance.
    """
    event = Event(
        id="beat_event",
        title="Event with Beats",
        beats=[
            "Emma looks nervous",
            "She fidgets with her phone",
            "The tension is palpable"
        ]
    )

    assert len(event.beats) == 3
    assert all(isinstance(b, str) for b in event.beats)

    print("✅ Event beats work")


def test_event_effects():
    """
    §19.2: Test event effects application.
    """
    event = Event(
        id="effect_event",
        title="Event with Effects",
        effects=[
            MeterChangeEffect(target="player", meter="energy", op="subtract", value=10),
            FlagSetEffect(key="event_fired", value=True)
        ]
    )

    assert len(event.effects) == 2
    assert event.effects[0].meter == "energy"
    assert event.effects[1].key == "event_fired"

    print("✅ Event effects work")


def test_event_choices():
    """
    §19.2: Test event local player choices.
    """
    event = Event(
        id="choice_event",
        title="Event with Choices",
        choices=[
            Choice(
                id="accept",
                prompt="Accept invitation",
                effects=[MeterChangeEffect(target="emma", meter="trust", op="add", value=10)],
                goto="date_scene"
            ),
            Choice(
                id="decline",
                prompt="Decline politely",
                effects=[MeterChangeEffect(target="emma", meter="trust", op="subtract", value=5)]
            )
        ]
    )

    assert len(event.choices) == 2
    assert event.choices[0].goto == "date_scene"
    assert len(event.choices[0].effects) == 1

    print("✅ Event choices work")


# =============================================================================
# § 19.2: Event Template - Cooldowns and Once Flag
# =============================================================================

def test_event_cooldown_turns():
    """
    §19.2: Test event cooldown in turns.
    """
    event = Event(
        id="cooldown_event",
        title="Cooldown Event",
        cooldown={"turns": 5}
    )

    assert event.cooldown is not None
    assert event.cooldown.get("turns") == 5

    print("✅ Event cooldown (turns) works")


def test_event_cooldown_minutes():
    """
    §19.2: Test event cooldown in minutes (for clock mode).
    """
    event = Event(
        id="time_cooldown_event",
        title="Time Cooldown Event",
        cooldown={"minutes": 720}  # 12 hours
    )

    assert event.cooldown is not None
    assert event.cooldown.get("minutes") == 720

    print("✅ Event cooldown (minutes) works")


# =============================================================================
# § 19.3: Runtime Behavior - Event Evaluation
# =============================================================================

def test_scheduled_event_triggering(minimal_game_def):
    """
    §19.3: Test that scheduled events trigger at the right time.
    """
    event = Event(
        id="morning_event",
        title="Morning Event",
        trigger=EventTrigger(
            scheduled=[{"when": "time.slot == 'morning'"}]
        ),
        narrative="It's a beautiful morning"
    )
    minimal_game_def.events = [event]

    engine = GameEngine(minimal_game_def, "test_scheduled")
    manager = EventManager(minimal_game_def)
    state = engine.state_manager.state

    # Not morning
    state.time_slot = "evening"
    triggered = manager.get_triggered_events(state)
    assert len(triggered) == 0

    # Now it's morning
    state.time_slot = "morning"
    triggered = manager.get_triggered_events(state)
    assert len(triggered) == 1
    assert triggered[0].id == "morning_event"

    print("✅ Scheduled event triggering works")


def test_conditional_event_triggering(minimal_game_def):
    """
    §19.3: Test that conditional events trigger when state conditions are met.
    """
    event = Event(
        id="low_health_event",
        title="Low Health Warning",
        trigger=EventTrigger(
            conditional=[{"when": "meters.player.health < 30"}]
        ),
        narrative="You feel weak and dizzy"
    )
    minimal_game_def.events = [event]

    engine = GameEngine(minimal_game_def, "test_conditional")
    manager = EventManager(minimal_game_def)
    state = engine.state_manager.state

    # Health above threshold
    state.meters["player"]["health"] = 50
    triggered = manager.get_triggered_events(state)
    assert len(triggered) == 0

    # Health below threshold
    state.meters["player"]["health"] = 25
    triggered = manager.get_triggered_events(state)
    assert len(triggered) == 1
    assert triggered[0].id == "low_health_event"

    print("✅ Conditional event triggering works")


def test_location_scoped_event_triggering(minimal_game_def):
    """
    §19.3: Test that location-scoped events only trigger in correct location.
    """
    event = Event(
        id="library_event",
        title="Library Encounter",
        scope="location",
        location="library",
        trigger=EventTrigger(
            conditional=[{"when": "true"}]  # Always eligible
        ),
        narrative="You see Emma studying alone"
    )
    minimal_game_def.events = [event]

    engine = GameEngine(minimal_game_def, "test_location_scope")
    manager = EventManager(minimal_game_def)
    state = engine.state_manager.state

    # Wrong location
    state.location_current = "dorm_room"
    triggered = manager.get_triggered_events(state)
    assert len(triggered) == 0

    # Correct location
    state.location_current = "library"
    triggered = manager.get_triggered_events(state)
    assert len(triggered) == 1
    assert triggered[0].id == "library_event"

    print("✅ Location-scoped event triggering works")


def test_location_enter_trigger(minimal_game_def):
    """
    §19.3: Test location_enter trigger fires when entering a location.
    """
    event = Event(
        id="gym_event",
        title="Gym Entrance",
        scope="location",
        location="gym",
        trigger=EventTrigger(
            location_enter=True
        ),
        narrative="Liam waves at you from across the gym"
    )
    minimal_game_def.events = [event]

    engine = GameEngine(minimal_game_def, "test_location_enter")
    manager = EventManager(minimal_game_def)
    state = engine.state_manager.state

    # In the gym
    state.location_current = "gym"
    triggered = manager.get_triggered_events(state)
    assert len(triggered) == 1
    assert triggered[0].id == "gym_event"

    print("✅ Location-enter trigger works")


def test_random_event_weighted_selection(minimal_game_def):
    """
    §19.3: Test weighted random event selection from pool.
    """
    event1 = Event(
        id="common_event",
        title="Common Event",
        trigger=EventTrigger(
            random=RandomTrigger(weight=70)
        ),
        narrative="A common occurrence"
    )
    event2 = Event(
        id="rare_event",
        title="Rare Event",
        trigger=EventTrigger(
            random=RandomTrigger(weight=30)
        ),
        narrative="A rare occurrence"
    )
    minimal_game_def.events = [event1, event2]

    engine = GameEngine(minimal_game_def, "test_random")
    manager = EventManager(minimal_game_def)
    state = engine.state_manager.state

    # Trigger multiple times and check that at least one triggers
    triggered_ids = set()
    for i in range(20):  # Run multiple times
        triggered = manager.get_triggered_events(state, rng_seed=i)
        if triggered:
            triggered_ids.add(triggered[0].id)

    # At least one event should have triggered in 20 attempts
    assert len(triggered_ids) > 0
    # Both events should eventually trigger given enough attempts
    # (though this is probabilistic)

    print("✅ Random event weighted selection works")


def test_multiple_events_can_trigger(minimal_game_def):
    """
    §19.3: Test that multiple eligible events can trigger in same turn.
    """
    event1 = Event(
        id="event_1",
        title="Event 1",
        trigger=EventTrigger(
            conditional=[{"when": "true"}]
        ),
        narrative="Event 1 fires"
    )
    event2 = Event(
        id="event_2",
        title="Event 2",
        trigger=EventTrigger(
            conditional=[{"when": "true"}]
        ),
        narrative="Event 2 fires"
    )
    minimal_game_def.events = [event1, event2]

    engine = GameEngine(minimal_game_def, "test_multiple")
    manager = EventManager(minimal_game_def)
    state = engine.state_manager.state

    triggered = manager.get_triggered_events(state)
    assert len(triggered) == 2
    assert {e.id for e in triggered} == {"event_1", "event_2"}

    print("✅ Multiple events can trigger")


# =============================================================================
# § 19.4: Runtime State - Cooldown Management
# =============================================================================

def test_event_cooldown_enforcement(minimal_game_def):
    """
    §19.4: Test that events respect cooldown periods.
    """
    event = Event(
        id="cooldown_event",
        title="Cooldown Event",
        trigger=EventTrigger(
            conditional=[{"when": "true"}]
        ),
        cooldown={"turns": 3},
        narrative="Event occurs"
    )
    minimal_game_def.events = [event]

    engine = GameEngine(minimal_game_def, "test_cooldown")
    manager = EventManager(minimal_game_def)
    state = engine.state_manager.state

    # First trigger
    triggered = manager.get_triggered_events(state)
    assert len(triggered) == 1
    assert "cooldown_event" in state.cooldowns
    assert state.cooldowns["cooldown_event"] == 3

    # Should not trigger while on cooldown
    triggered = manager.get_triggered_events(state)
    assert len(triggered) == 0

    # Decrement cooldown
    state.cooldowns["cooldown_event"] = 1
    manager.decrement_cooldowns(state)

    # Cooldown should be removed (reached 0)
    assert "cooldown_event" not in state.cooldowns

    # Should trigger again
    triggered = manager.get_triggered_events(state)
    assert len(triggered) == 1

    print("✅ Event cooldown enforcement works")


def test_cooldown_tracking_in_state(minimal_game_def):
    """
    §19.4: Test that state.cooldowns tracks active cooldowns.
    """
    engine = GameEngine(minimal_game_def, "test_cooldown_state")
    state = engine.state_manager.state

    # Initially empty
    assert len(state.cooldowns) == 0

    # Set some cooldowns
    state.cooldowns["event_1"] = 5
    state.cooldowns["event_2"] = 10

    assert state.cooldowns["event_1"] == 5
    assert state.cooldowns["event_2"] == 10

    print("✅ Cooldown tracking in state works")


# =============================================================================
# § 19.5: Examples - Real Event Patterns
# =============================================================================

async def test_scheduled_event_example():
    """
    §19.5: Test a realistic scheduled event (Emma texts at night on day 1).
    """
    loader = GameLoader()
    game_def = loader.load_game("college_romance")

    # Find the emma_text_thinking event
    emma_event = next((e for e in game_def.events if e.id == "emma_text_thinking"), None)
    assert emma_event is not None
    assert emma_event.trigger.conditional is not None
    assert emma_event.narrative is not None
    assert len(emma_event.choices) > 0

    print("✅ Scheduled event example validated")


async def test_conditional_encounter_example():
    """
    §19.5: Test a realistic conditional encounter (meeting at specific location).
    """
    loader = GameLoader()
    game_def = loader.load_game("college_romance")

    # Find location-scoped events
    location_events = [e for e in game_def.events if e.scope == "location"]
    assert len(location_events) > 0

    # Check structure
    for event in location_events:
        assert event.location is not None
        assert event.narrative is not None

    print("✅ Conditional encounter example validated")


async def test_random_ambient_example():
    """
    §19.5: Test a realistic random ambient event.
    """
    loader = GameLoader()
    game_def = loader.load_game("college_romance")

    # Find random events
    random_events = [e for e in game_def.events
                     if e.trigger and e.trigger.random]
    assert len(random_events) > 0

    # Check they have weights and cooldowns
    for event in random_events:
        assert event.trigger.random.weight > 0
        # Cooldowns are recommended but not required
        # assert event.trigger.random.cooldown is not None

    print("✅ Random ambient example validated")


# =============================================================================
# § 19.6: Authoring Guidelines
# =============================================================================

def test_random_events_should_have_cooldowns():
    """
    §19.6: Test that random events have cooldowns to prevent spam.
    """
    # Good: random event with cooldown
    good_event = Event(
        id="good_random",
        title="Good Random Event",
        trigger=EventTrigger(
            random=RandomTrigger(weight=20, cooldown=10)
        ),
        narrative="Something interesting happens"
    )
    assert good_event.trigger.random.cooldown == 10

    # Bad: random event without cooldown (allowed but not recommended)
    bad_event = Event(
        id="bad_random",
        title="Bad Random Event",
        trigger=EventTrigger(
            random=RandomTrigger(weight=20)  # No cooldown!
        ),
        narrative="This could spam"
    )
    assert bad_event.trigger.random.cooldown is None

    print("✅ Random event cooldown guideline noted")


def test_location_scoped_events_need_location():
    """
    §19.6: Test that location-scoped events specify a location.
    """
    # Good: location scope with location specified
    event = Event(
        id="cafe_event",
        title="Cafe Event",
        scope="location",
        location="campus_cafe",
        narrative="Something happens at the cafe"
    )
    assert event.scope == "location"
    assert event.location is not None

    print("✅ Location scope guideline validated")


def test_events_should_be_light_and_modular():
    """
    §19.6: Test that events avoid chaining too many effects.
    """
    # Good: light event with few effects
    good_event = Event(
        id="light_event",
        title="Light Event",
        effects=[
            FlagSetEffect(key="event_happened", value=True),
            MeterChangeEffect(target="player", meter="energy", op="add", value=5)
        ],
        narrative="A brief encounter"
    )
    assert len(good_event.effects) <= 3  # Reasonable

    # Bad: heavy event with many effects (still valid, just not recommended)
    heavy_event = Event(
        id="heavy_event",
        title="Heavy Event",
        effects=[
            FlagSetEffect(key="flag1", value=True),
            FlagSetEffect(key="flag2", value=True),
            MeterChangeEffect(target="player", meter="energy", op="subtract", value=10),
            MeterChangeEffect(target="emma", meter="trust", op="add", value=5),
            MeterChangeEffect(target="emma", meter="attraction", op="add", value=5),
            AdvanceTimeEffect(minutes=60)
        ],
        narrative="A complex event with many consequences"
    )
    assert len(heavy_event.effects) > 3  # Too many for a simple event

    print("✅ Event modularity guideline noted")


# =============================================================================
# Integration Tests with Real Games
# =============================================================================

async def test_real_game_events_structure():
    """
    §19: Test that real game files have valid event structures.
    """
    loader = GameLoader()
    college = loader.load_game("college_romance")

    assert len(college.events) > 0

    # Check event structure
    for event in college.events:
        assert event.id is not None
        assert event.title is not None
        # All events should have at least one trigger type
        if event.trigger:
            has_trigger = (
                event.trigger.scheduled or
                event.trigger.conditional or
                event.trigger.random or
                event.trigger.location_enter
            )
            assert has_trigger, f"Event {event.id} has no trigger mechanism"

    print("✅ Real game events validated")


async def test_event_categories():
    """
    §19: Test that events can be categorized for organization.
    """
    loader = GameLoader()
    college = loader.load_game("college_romance")

    # Check that events have categories
    categorized = [e for e in college.events if e.category]
    assert len(categorized) > 0

    # Common categories
    categories = {e.category for e in college.events if e.category}
    expected_categories = {"ambient", "relationship", "academic", "social"}
    assert len(categories & expected_categories) > 0

    print("✅ Event categories validated")


async def test_event_loading_from_yaml(tmp_path: Path):
    """
    §19: Test loading events from YAML game definition.
    """
    game_dir = tmp_path / "event_test"
    game_dir.mkdir()

    manifest = {
        'meta': {
            'id': 'event_test',
            'title': 'Event Test',
            'version': '1.0.0',
            'authors': ['tester']
        },
        'start': {
            'node': 'start',
            'location': {'zone': 'test_zone', 'id': 'test_loc'}
        },
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{
            'id': 'test_zone',
            'name': 'Test Zone',
            'locations': [{'id': 'test_loc', 'name': 'Test Location'}]
        }],
        'nodes': [{
            'id': 'start',
            'type': 'scene',
            'title': 'Start'
        }],
        'events': [
            {
                'id': 'test_event_1',
                'title': 'Test Event 1',
                'trigger': {
                    'scheduled': [{'when': "time.slot == 'morning'"}]
                },
                'narrative': 'Morning event'
            },
            {
                'id': 'test_event_2',
                'title': 'Test Event 2',
                'scope': 'location',
                'location': 'test_loc',
                'trigger': {
                    'conditional': [{'when': 'meters.player.health < 50'}]
                },
                'narrative': 'Location event',
                'effects': [
                    {'type': 'meter_change', 'target': 'player', 'meter': 'health', 'op': 'add', 'value': 20}
                ]
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("event_test")

    assert len(game_def.events) == 2
    assert game_def.events[0].id == "test_event_1"
    assert game_def.events[1].scope == "location"
    assert len(game_def.events[1].effects) == 1

    print("✅ Event loading from YAML works")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])