import pytest

from app.models.game import GameState, CharacterState
from app.runtime.types import PlayerAction


@pytest.mark.asyncio
async def test_ai_writer_checker_flow(fixture_engine_factory):
    """Verify AI writer streams narrative and checker deltas apply cleanly."""
    engine = fixture_engine_factory(session_id="ai-seed")
    events = []
    async for chunk in engine.process_action_stream(
        PlayerAction(action_type="say", action_text="Say hello with AI")
    ):
        events.append(chunk)
    # At least one narrative chunk plus the completion payload
    narrative_chunks = [e for e in events if e["type"] == "narrative_chunk"]
    complete = next(e for e in events if e["type"] == "complete")
    assert narrative_chunks, "AI writer did not stream any narrative chunks"
    # Checker deltas from MockAIService are empty; state should still advance and narrative recorded
    assert complete["narrative"]
    assert engine.runtime.state_manager.state.narrative_history[-1] == complete["narrative"]
    assert complete["rng_seed"] == 1337  # base_seed * turn 1 for fixture game


def test_rng_seed_replay_determinism(fixture_engine_factory):
    """Verify Same session + actions produce identical RNG seeds and outcomes."""
    engine_a = fixture_engine_factory(session_id="seed-1")
    engine_b = fixture_engine_factory(session_id="seed-1")

    async def run_two_turns(engine):
        first = await engine.start()
        second = await engine.process_action(PlayerAction(action_type="choice", choice_id="greet_alex"))
        return first, second

    import asyncio

    first_a, second_a = asyncio.run(run_two_turns(engine_a))
    first_b, second_b = asyncio.run(run_two_turns(engine_b))

    assert first_a.rng_seed == first_b.rng_seed == 1337
    assert second_a.rng_seed == second_b.rng_seed == 2674
    assert first_a.choices == first_b.choices
    assert second_a.state_summary == second_b.state_summary


def test_state_persistence_and_snapshot_roundtrip(fixture_engine_factory):
    """Verify State to_dict roundtrips through GameState construction."""
    engine = fixture_engine_factory()
    state = engine.runtime.state_manager.state
    snapshot = state.to_dict()
    restored = GameState(**snapshot)
    # Rehydrate nested character states from dicts for comparison
    for char_id, char_data in list(restored.characters.items()):
        if isinstance(char_data, dict):
            restored.characters[char_id] = CharacterState(**char_data)
    assert restored.current_location == state.current_location
    assert restored.current_node == state.current_node
    assert restored.flags == state.flags
    assert restored.characters["player"].meters == state.characters["player"].meters
