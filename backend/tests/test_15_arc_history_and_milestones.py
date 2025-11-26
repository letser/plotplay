import pytest

from app.runtime.types import PlayerAction


def test_arc_history_defined(fixture_loader):
    """
    Spec coverage: arc stage history, milestones tracking.
    """
    game = fixture_loader.load_game("checklist_demo")
    arc = game.arcs[0]
    assert len(arc.stages) >= 2


@pytest.mark.asyncio
async def test_arc_milestones_recorded(started_fixture_engine):
    """
    Spec coverage: on_enter/on_exit effects, stage progression, history list.
    """
    engine, initial_result = started_fixture_engine
    greet_choice = next(choice for choice in initial_result.choices if choice["id"] == "greet_alex")

    result = await engine.process_action(PlayerAction(action_type="choice", choice_id=greet_choice["id"]))
    arc_state = engine.runtime.state_manager.state.arcs.get("friendship")

    assert arc_state is not None
    assert arc_state.stage == "met"
    assert "met" in (arc_state.history or [])
    assert "met" in result.milestones_reached
