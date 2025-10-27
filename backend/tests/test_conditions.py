from app.core.conditions import ConditionEvaluator


def test_single_expression_evaluation(sample_game_state):
    evaluator = ConditionEvaluator(sample_game_state, rng_seed=123)

    assert evaluator.evaluate("meters.player.energy > 50")
    assert evaluator.evaluate("flags.met_emma == true")
    assert evaluator.evaluate("location.privacy in ['low','medium','high']")
    assert evaluator.evaluate("has('coffee')")
    assert not evaluator.evaluate("has('ticket')")
    assert evaluator.evaluate("npc_present('emma')")


def test_evaluate_all_any(sample_game_state):
    evaluator = ConditionEvaluator(sample_game_state, rng_seed=321)

    assert evaluator.evaluate_all(["meters.player.energy > 50", "flags.met_emma"])
    assert not evaluator.evaluate_all(["meters.player.energy > 50", "flags.invitation_sent"])

    assert evaluator.evaluate_any(["flags.invitation_sent", "meters.player.money >= 40"])
    assert not evaluator.evaluate_any(["flags.invitation_sent", "has('ticket')"])


def test_evaluate_conditions_helper(sample_game_state):
    gates = {"emma": {"accept_walk": True}}
    evaluator = ConditionEvaluator(sample_game_state, gates=gates)

    assert evaluator.evaluate_conditions(
        when="meters.emma.trust >= 50",
        when_all=["npc_present('emma')"],
    )

    assert not evaluator.evaluate_conditions(
        when="meters.emma.trust >= 50",
        when_all=["flags.invitation_sent"],
    )

    assert evaluator.evaluate_conditions(
        when="meters.emma.trust >= 50",
        when_all=["npc_present('emma')"],
        when_any=["gates.emma.accept_walk", "has('ticket')"],
    )


def test_rand_and_get_helpers(sample_game_state):
    evaluator = ConditionEvaluator(sample_game_state, rng_seed=42)

    assert evaluator.evaluate("get('flags.met_emma', false)")
    assert not evaluator.evaluate("get('flags.missing_flag', false)")

    results = {evaluator.evaluate("rand(0.2)") for _ in range(10)}
    # With deterministic seed we should get both True and False over several calls.
    assert results == {True, False}


def test_context_includes_gates(sample_game_state):
    gates = {"emma": {"accept_walk": True, "accept_kiss": False}}
    evaluator = ConditionEvaluator(sample_game_state, gates=gates)

    assert evaluator.evaluate("gates.emma.accept_walk")
    assert not evaluator.evaluate("gates.emma.accept_kiss")
