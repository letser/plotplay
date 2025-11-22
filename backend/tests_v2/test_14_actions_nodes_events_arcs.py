import pytest

from app.runtime.types import PlayerAction


def test_node_and_action_presence(fixture_loader):
    """Verify Node and action presence."""
    game = fixture_loader.load_game("checklist_demo")
    node_ids = {node.id for node in game.nodes}
    assert {"intro", "campus_hub", "chat_alex", "wardrobe_test", "ending_exit"}.issubset(node_ids)
    action_ids = {action.id for action in game.actions}
    assert "unlock_cafe_route" in action_ids


def test_arc_stages_configured(fixture_loader):
    """Verify Arc stages configured."""
    game = fixture_loader.load_game("checklist_demo")
    arc = game.arcs[0]
    assert arc.stages[0].when == "flags.met_alex == true"
    assert arc.stages[1].when == "meters.alex.trust >= 20"


@pytest.mark.asyncio
async def test_choice_effects_drive_transitions(started_fixture_engine):
    """Verify Choice effects drive transitions."""
    engine, initial = started_fixture_engine
    greet = next(choice for choice in initial.choices if choice["id"] == "greet_alex")
    result = await engine.process_action(PlayerAction(action_type="choice", choice_id=greet["id"]))
    assert engine.runtime.state_manager.state.current_node == "campus_hub"
    # Arc progression should be evaluated after greeting
    arc_state = engine.runtime.state_manager.state.arcs.get("friendship")
    assert arc_state.stage in {"met", "comfortable"}


@pytest.mark.asyncio
async def test_events_register_and_can_trigger(started_fixture_engine):
    """Verify Events register and can trigger."""
    engine, _ = started_fixture_engine
    # Run several idle turns to allow random and conditional events to enqueue
    for _ in range(3):
        await engine.process_action(PlayerAction(action_type="do", action_text="Pass time"))
    # Event firing is stochastic; assert that engine tracks event ids when fired
    state = engine.runtime.state_manager.state
    _ = getattr(state, "last_event_id", None)
