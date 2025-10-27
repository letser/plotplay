import logging
from types import SimpleNamespace

from app.core.game_loader import GameLoader
from app.core.game_engine import GameEngine
from app.models.effects import FlagSetEffect
from app.models.nodes import Choice, Node, NodeType
from tests_v2.conftest import minimal_game


def build_engine(tmp_path, monkeypatch) -> GameEngine:
    def fake_logger(session_id: str) -> logging.Logger:
        logger = logging.getLogger(f"node-test-{session_id}")
        logger.handlers.clear()
        logger.setLevel(logging.DEBUG)
        logger.addHandler(logging.NullHandler())
        return logger

    monkeypatch.setattr("app.engine.runtime.setup_session_logger", fake_logger)


    game_path = minimal_game(tmp_path)
    loader = GameLoader(games_dir=game_path.parent)
    game_def = loader.load_game(game_path.name)
    return GameEngine(game_def, session_id="node-session")


def test_node_service_applies_transitions(tmp_path, monkeypatch):
    engine = build_engine(tmp_path, monkeypatch)
    current_node = engine._get_current_node()

    next_node = Node(id="next", type=NodeType.SCENE, title="Next")
    engine.game_def.nodes.append(next_node)
    engine.nodes_map[next_node.id] = next_node

    transition = SimpleNamespace(when="true", to="next")
    current_node.triggers.append(transition)

    assert engine.nodes.apply_transitions() is True
    assert engine.state_manager.state.current_node == "next"


def test_node_service_handles_predefined_choice(tmp_path, monkeypatch):
    engine = build_engine(tmp_path, monkeypatch)
    state = engine.state_manager.state
    current_node = engine._get_current_node()

    flag_effect = FlagSetEffect(key="met_friend", value=True)
    node_choice = Choice(id="greet", prompt="Greet warmly", on_select=[flag_effect])
    current_node.choices.append(node_choice)

    import asyncio

    result = asyncio.run(engine.nodes.handle_predefined_choice("greet", []))

    assert result is True
    assert state.flags.get("met_friend") is True
