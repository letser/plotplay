import pytest

from app.core.state import StateManager


def test_dsl_basic_operators_and_paths(fixture_loader):
    game = fixture_loader.load_game("checklist_demo")
    state_manager = StateManager(game)
    evaluator = state_manager.create_evaluator()

    assert evaluator.evaluate("meters.player.energy >= 50") is True
    assert evaluator.evaluate('flags.met_alex == false') is True
    # Missing paths should be falsey, not crash
    assert evaluator.evaluate('get("meters.alex.nonexistent", 0) == 0') is True
    assert evaluator.evaluate('get("inventory.player.items.coffee", 0) == 0') is True


def test_dsl_functions_has_and_discovery(fixture_loader):
    game = fixture_loader.load_game("checklist_demo")
    state_manager = StateManager(game)
    evaluator = state_manager.create_evaluator()

    # Player starts without map (it is added via intro on_enter after start)
    assert evaluator.evaluate("has('player','map')") is False
    # Quad is discovered at start, cafe/library are gated
    assert evaluator.evaluate("discovered('quad')") is True
    assert evaluator.evaluate("discovered('cafe')") is False
    assert evaluator.evaluate("discovered('library')") is False


def test_dsl_clothing_and_unlock_helpers(fixture_loader):
    game = fixture_loader.load_game("checklist_demo")
    state_manager = StateManager(game)
    evaluator = state_manager.create_evaluator()
    assert evaluator.evaluate("wears('player','jacket')") is False
    assert evaluator.evaluate("has_outfit('player','formal')") is False
    assert evaluator.evaluate("unlocked('ending','demo_complete')") is False


@pytest.mark.skip(reason="rand() determinism and function coverage to be finalized with runtime RNG hook")
def test_dsl_rand_probability(fixture_loader):
    game = fixture_loader.load_game("checklist_demo")
    state_manager = StateManager(game)
    evaluator = state_manager.create_evaluator()
    assert evaluator.evaluate("rand(0.0)") is False
