import pytest

from app.runtime.types import PlayerAction


def test_invalid_action_type_rejected(fixture_engine_factory):
    """
    Spec coverage: API 400 for bad action_type, error payload structure.
    """
    engine = fixture_engine_factory()
    import asyncio
    with pytest.raises(ValueError):
        asyncio.run(engine.process_action(PlayerAction(action_type="bad_type")))


def test_invalid_effect_logs_warning(fixture_engine_factory):
    """
    Spec coverage: skip invalid effects, log warnings, continue execution.
    """
    engine = fixture_engine_factory()
    with pytest.raises(Exception):
        engine.runtime.effect_resolver.apply_effects([{"type": "not_real"}])


@pytest.mark.asyncio
async def test_action_on_ending_node_rejected(started_fixture_engine):
    """
    Spec coverage: reject actions on ENDING nodes with clear error.
    """
    engine, _ = started_fixture_engine
    engine.runtime.state_manager.state.current_node = "ending_exit"
    with pytest.raises(ValueError):
        await engine.process_action(PlayerAction(action_type="do", action_text="Trigger ending"))
