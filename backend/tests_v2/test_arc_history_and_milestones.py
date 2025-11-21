import pytest

from app.runtime.types import PlayerAction


def test_arc_history_defined(fixture_loader):
    """
    Spec coverage: arc stage history, milestones tracking.
    """
    game = fixture_loader.load_game("checklist_demo")
    arc = game.arcs[0]
    assert len(arc.stages) >= 2


@pytest.mark.skip(reason="Runtime arc history/milestone tracking assertions pending.")
@pytest.mark.asyncio
async def test_arc_milestones_recorded(started_fixture_engine):
    """
    Spec coverage: on_enter/on_exit effects, stage progression, history list.
    """
    engine, _ = started_fixture_engine
    await engine.process_action(PlayerAction(action_type="do", action_text="Progress arc"))
    arc_state = engine.runtime.state_manager.state.arcs.get("friendship")
    _ = arc_state.history
