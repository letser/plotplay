import pytest

from app.core.game_loader import GameLoader
from app.core.game_validator import GameValidator
from app.models.nodes import NodeType


def load_game(game_id: str):
    loader = GameLoader()
    return loader.load_game(game_id)


def test_validator_accepts_reference_games():
    game = load_game("coffeeshop_date")
    GameValidator(game).validate()


def test_validator_rejects_unknown_meter_reference():
    game = load_game("coffeeshop_date")
    broken = game.model_copy(deep=True)
    broken.nodes[0].on_enter[0]["meter"] = "nonexistent_meter"

    with pytest.raises(ValueError, match="unknown meter"):
        GameValidator(broken).validate()


def test_validator_rejects_unlocking_non_ending():
    game = load_game("college_romance")
    broken = game.model_copy(deep=True)
    # Change the unlock effect in the first arc stage to reference a non-ending node.
    unlock_effect = broken.arcs[0].stages[-1].on_enter[0]
    non_ending_node_id = next(node.id for node in broken.nodes if node.type != NodeType.ENDING)
    unlock_effect["endings"] = [non_ending_node_id]

    with pytest.raises(ValueError, match="not an ending"):
        GameValidator(broken).validate()


def test_validator_blocks_starting_on_ending_node():
    game = load_game("college_romance")
    broken = game.model_copy(deep=True)
    ending_node_id = next(node.id for node in broken.nodes if node.type == NodeType.ENDING)
    broken.start.node = ending_node_id

    with pytest.raises(ValueError, match="cannot be an ending"):
        GameValidator(broken).validate()
