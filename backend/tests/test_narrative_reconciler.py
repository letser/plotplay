import pytest
from types import SimpleNamespace

from app.engine.narrative import NarrativeReconciler
from tests_v2.conftest_services import engine_fixture


@pytest.fixture
def reconciler(engine_fixture) -> NarrativeReconciler:
    return NarrativeReconciler(engine_fixture)


def test_narrative_respects_behaviors(reconciler):
    engine = reconciler.engine
    engine.characters_map["friend"] = SimpleNamespace(
        name="Friend",
        pronouns=["she"],
        behaviors=SimpleNamespace(
            gates=[SimpleNamespace(id="accept_kiss", when="false", when_any=[], when_all=[])],
            refusals=SimpleNamespace(generic="She pulls away."),
        ),
    )
    result = reconciler.reconcile("kiss friend", "She smiles.", {}, "friend")
    assert result == "She pulls away."


def test_narrative_allows_if_gate_satisfied(reconciler):
    engine = reconciler.engine
    engine.characters_map["friend"] = SimpleNamespace(
        name="Friend",
        pronouns=["she"],
        behaviors=SimpleNamespace(
            gates=[SimpleNamespace(id="accept_kiss", when="true", when_any=[], when_all=[])],
            refusals=SimpleNamespace(generic="She pulls away."),
        ),
    )

    result = reconciler.reconcile("kiss friend", "She smiles.", {}, "friend")
    assert result == "She smiles."
