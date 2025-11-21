import pytest

from app.runtime.types import PlayerAction


@pytest.mark.skip(reason="AI writer/checker integration not yet exercised in runtime; add when available.")
@pytest.mark.asyncio
async def test_ai_writer_checker_flow(started_fixture_engine):
    """
    Spec coverage: AI action flow, character cards, checker deltas applied.
    Expectation: an AI-backed action streams prose, checker deltas, and applies them to state.
    """
    engine, _ = started_fixture_engine
    await engine.process_action(PlayerAction(action_type="say", action_text="Say hello with AI"))


@pytest.mark.skip(reason="Deterministic RNG seeding and replay tests pending runtime hooks.")
def test_rng_seed_replay_determinism(fixture_engine_factory):
    """
    Spec coverage: reproducible randomness (game_id + session_id + turn).
    Expectation: two sessions with same seed and actions produce identical event selection.
    """
    engine_a = fixture_engine_factory(session_id="seed-1")
    engine_b = fixture_engine_factory(session_id="seed-1")
    # TODO: drive identical actions and compare event/movement outcomes.
    assert engine_a.session_id == engine_b.session_id


@pytest.mark.skip(reason="State persistence/snapshots API not wired in new runtime yet.")
def test_state_persistence_and_snapshot_roundtrip(fixture_engine_factory):
    """
    Spec coverage: state save/load, snapshots for rollback.
    Expectation: serializing and restoring state preserves meters, flags, location, arcs.
    """
    engine = fixture_engine_factory()
    # TODO: call state_manager.save/load once implemented and assert equality.
    assert engine.runtime.state_manager is not None
