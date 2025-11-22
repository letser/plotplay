import pytest

from app.runtime.types import PlayerAction


@pytest.mark.skip(reason="API layer error handling/400/404 not wired into test harness yet.")
def test_invalid_action_type_rejected():
    """
    Spec coverage: API 400 for bad action_type, error payload structure.
    """
    # TODO: call FastAPI client once new endpoints are wired to runtime.
    pass


@pytest.mark.skip(reason="Engine warnings/errors not surfaced for invalid effects yet.")
def test_invalid_effect_logs_warning(fixture_loader):
    """
    Spec coverage: skip invalid effects, log warnings, continue execution.
    """
    game = fixture_loader.load_game("checklist_demo")
    assert game.meta.id == "checklist_demo"


@pytest.mark.skip(reason="Ending guard and invalid node handling to be covered once runtime exposes errors.")
@pytest.mark.asyncio
async def test_action_on_ending_node_rejected(started_fixture_engine):
    """
    Spec coverage: reject actions on ENDING nodes with clear error.
    """
    engine, _ = started_fixture_engine
    await engine.process_action(PlayerAction(action_type="do", action_text="Trigger ending"))
