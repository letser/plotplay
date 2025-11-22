"""
Test all effect types systematically.

This test file covers Section 12 of the checklist:
- All effect type implementations
- Effect guard conditions (when/when_all/when_any)
- Effect execution ordering
- Effect validation and error handling
"""

import pytest

from app.models.effects import (
    AdvanceTimeEffect,
    ApplyModifierEffect,
    ClothingPutOnEffect,
    ClothingSlotStateEffect,
    ClothingStateEffect,
    ClothingTakeOffEffect,
    ConditionalEffect,
    FlagSetEffect,
    GotoEffect,
    InventoryAddEffect,
    InventoryDropEffect,
    InventoryRemoveEffect,
    InventorySellEffect,
    InventoryTakeEffect,
    MeterChangeEffect,
    OutfitPutOnEffect,
    OutfitTakeOffEffect,
    RandomChoice,
    RandomEffect,
    RemoveModifierEffect,
    UnlockEffect,
    LockEffect,
)
from app.runtime.types import PlayerAction

# ============================================================================
# METER EFFECTS
# ============================================================================

async def test_meter_change_multiply_operation(started_fixture_engine):
    """Test meter_change with op: multiply."""
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    state.characters["player"].meters["energy"] = 50
    effect = MeterChangeEffect(target="player", meter="energy", op="multiply", value=2, respect_caps=True, cap_per_turn=False)
    engine.runtime.effect_resolver.apply_effects([effect])
    assert state.characters["player"].meters["energy"] == 100  # 50 * 2 capped at 100


async def test_meter_change_divide_operation(started_fixture_engine):
    """Test meter_change with op: divide."""
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    state.characters["player"].meters["energy"] = 50
    effect = MeterChangeEffect(target="player", meter="energy", op="divide", value=2, respect_caps=True, cap_per_turn=False)
    engine.runtime.effect_resolver.apply_effects([effect])
    assert state.characters["player"].meters["energy"] == 25


async def test_meter_change_respect_caps_flag(started_fixture_engine):
    """Test meter_change with respect_caps=true/false."""
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    state.characters["player"].meters["energy"] = 50
    effect_cap = MeterChangeEffect(target="player", meter="energy", op="add", value=100, respect_caps=True, cap_per_turn=False)
    engine.runtime.effect_resolver.apply_effects([effect_cap])
    assert state.characters["player"].meters["energy"] == 100

    # Reset and test without caps
    state.characters["player"].meters["energy"] = 50
    effect_no_cap = MeterChangeEffect(target="player", meter="energy", op="add", value=200, respect_caps=False, cap_per_turn=False)
    engine.runtime.effect_resolver.apply_effects([effect_no_cap])
    assert state.characters["player"].meters["energy"] == 250


async def test_meter_change_cap_per_turn_flag(started_fixture_engine):
    """Test meter_change with cap_per_turn enforcement."""
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    # Inject a per-turn cap to the meter definition
    meter_def = engine.runtime.index.player_meters["energy"]
    setattr(meter_def, "delta_cap_per_turn", 5)
    state.characters["player"].meters["energy"] = 50

    effect = MeterChangeEffect(target="player", meter="energy", op="add", value=10, respect_caps=True, cap_per_turn=True)
    engine.runtime.current_context = type("Ctx", (), {"meter_deltas": {}})
    engine.runtime.effect_resolver.apply_effects([effect])
    assert state.characters["player"].meters["energy"] == 55
    engine.runtime.effect_resolver.apply_effects([effect])
    assert state.characters["player"].meters["energy"] == 55  # capped for the turn


# ============================================================================
# INVENTORY EFFECTS
# ============================================================================

async def test_inventory_add_effect(started_fixture_engine):
    """
    Test inventory_add effect.

    Should test:
    - Add item to character inventory
    - Add clothing to character inventory
    - Add outfit to character inventory
    - Count parameter
    - Trigger on_get effects
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    add_item = InventoryAddEffect(target="player", item_type="item", item="coffee", count=2)
    add_clothing = InventoryAddEffect(target="player", item_type="clothing", item="jacket", count=1)
    add_outfit = InventoryAddEffect(target="player", item_type="outfit", item="casual", count=1)
    engine.runtime.effect_resolver.apply_effects([add_item, add_clothing, add_outfit])
    assert state.characters["player"].inventory.items["coffee"] == 2
    assert state.characters["player"].inventory.clothing["jacket"] == 1
    assert state.characters["player"].inventory.outfits["casual"] == 1


async def test_inventory_remove_effect(started_fixture_engine):
    """
    Test inventory_remove effect.

    Should test:
    - Remove item from character inventory
    - Remove clothing from character inventory
    - Remove outfit from character inventory
    - Count parameter
    - Trigger on_lost effects
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    state.characters["player"].inventory.items["coffee"] = 3
    effect = InventoryRemoveEffect(target="player", item_type="item", item="coffee", count=2)
    engine.runtime.effect_resolver.apply_effects([effect])
    assert state.characters["player"].inventory.items["coffee"] == 1


async def test_inventory_take_effect(started_fixture_engine):
    """
    Test inventory_take effect from location.

    Should test:
    - Take item from location inventory
    - Take clothing from location inventory
    - Take outfit from location inventory
    - Validate item availability
    - Update location inventory
    - Trigger on_get effects
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    loc = state.locations[state.current_location]
    loc.inventory.items["map"] = 1
    effect = InventoryTakeEffect(target="player", item_type="item", item="map", count=1)
    engine.runtime.effect_resolver.apply_effects([effect])
    assert state.characters["player"].inventory.items["map"] == 1
    assert loc.inventory.items.get("map", 0) == 0


async def test_inventory_drop_effect(started_fixture_engine):
    """
    Test inventory_drop effect to location.

    Should test:
    - Drop item to location inventory
    - Drop clothing to location inventory
    - Drop outfit to location inventory (drops items, keeps recipe)
    - Update location inventory
    - Trigger on_lost effects
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    state.characters["player"].inventory.items["map"] = 1
    effect = InventoryDropEffect(target="player", item_type="item", item="map", count=1)
    engine.runtime.effect_resolver.apply_effects([effect])
    loc = state.locations[state.current_location]
    assert loc.inventory.items["map"] == 1
    assert state.characters["player"].inventory.items.get("map", 0) == 0


async def test_inventory_sell_effect(started_fixture_engine):
    """
    Test inventory_sell effect.

    Should test:
    - Sell item to shop
    - Sell clothing to shop
    - Sell outfit to shop
    - Money addition
    - Shop inventory update (if resell=true)
    - Price calculation with multipliers
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    state.characters["player"].inventory.items["coffee"] = 1
    state.characters["player"].meters["money"] = 0
    effect = InventorySellEffect(target="cafe", source="player", item_type="item", item="coffee", count=1, price=10)
    engine.runtime.effect_resolver.apply_effects([effect])
    assert state.characters["player"].inventory.items.get("coffee", 0) == 0
    assert state.characters["player"].meters["money"] >= 5  # after sell at 0.5 multiplier


# ============================================================================
# CLOTHING EFFECTS
# ============================================================================

async def test_clothing_put_on_effect(started_fixture_engine):
    """
    Test clothing_put_on effect for individual items.

    Should test:
    - Put on clothing item
    - Occupy correct slot(s)
    - Set initial condition (intact by default)
    - Trigger on_put_on effects
    - Validate item in inventory
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    state.characters["player"].inventory.clothing["jacket"] = 1
    effect = ClothingPutOnEffect(target="player", item="jacket", condition="intact")
    engine.runtime.effect_resolver.apply_effects([effect])
    assert state.characters["player"].clothing.items["jacket"] == "intact"
    slot_state = state.clothing_states["player"]
    assert slot_state["slot_to_item"]["top"] == "jacket"


async def test_clothing_take_off_effect(started_fixture_engine):
    """
    Test clothing_take_off effect for individual items.

    Should test:
    - Take off clothing item
    - Clear slot(s)
    - Keep item in inventory
    - Trigger on_take_off effects
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    state.characters["player"].inventory.clothing["jacket"] = 1
    engine.runtime.effect_resolver.apply_effects([ClothingPutOnEffect(target="player", item="jacket", condition="intact")])
    engine.runtime.effect_resolver.apply_effects([ClothingTakeOffEffect(target="player", item="jacket")])
    assert state.characters["player"].clothing.items["jacket"] == "removed"
    assert state.clothing_states["player"]["slot_to_item"] == {}


async def test_clothing_state_effect(started_fixture_engine):
    """
    Test clothing_state effect.

    Should test:
    - Set clothing to intact
    - Set clothing to opened
    - Set clothing to displaced
    - Set clothing to removed
    - Validate item must be worn
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    state.characters["player"].inventory.clothing["dress"] = 1
    engine.runtime.effect_resolver.apply_effects([ClothingPutOnEffect(target="player", item="dress", condition="intact")])
    engine.runtime.effect_resolver.apply_effects([ClothingStateEffect(target="player", item="dress", condition="opened")])
    assert state.characters["player"].clothing.items["dress"] == "opened"


async def test_clothing_slot_state_effect(started_fixture_engine):
    """
    Test clothing_slot_state effect.

    Should test:
    - Set slot item to intact
    - Set slot item to opened
    - Set slot item to displaced
    - Set slot item to removed
    - Validate slot is occupied
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    state.characters["player"].inventory.clothing["jacket"] = 1
    engine.runtime.effect_resolver.apply_effects([ClothingPutOnEffect(target="player", item="jacket", condition="intact")])
    engine.runtime.effect_resolver.apply_effects([ClothingSlotStateEffect(target="player", slot="top", condition="opened")])
    assert state.clothing_states["player"]["slot_state"]["top"] == "opened"


async def test_outfit_take_off_effect(started_fixture_engine):
    """
    Test outfit_take_off effect.

    Should test:
    - Take off all outfit items
    - Clear all occupied slots
    - Keep items in inventory
    - Trigger on_take_off effects
    - Outfit recipe remains known
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    effect_put = OutfitPutOnEffect(target="player", item="formal")
    engine.runtime.effect_resolver.apply_effects([effect_put])
    assert state.characters["player"].clothing.outfit == "formal"
    engine.runtime.effect_resolver.apply_effects([OutfitTakeOffEffect(target="player", item="formal")])
    assert state.characters["player"].clothing.outfit is None
    assert state.clothing_states["player"]["slot_to_item"] == {}


# ============================================================================
# MOVEMENT & TIME EFFECTS
# ============================================================================

async def test_advance_time_effect(started_fixture_engine):
    """
    Test advance_time effect.

    Should test:
    - Advance time by specified minutes
    - Update current_minutes
    - Recalculate slot
    - Handle day rollover
    - Tick modifier durations
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    effect = AdvanceTimeEffect(minutes=120)
    engine.runtime.effect_resolver.apply_effects([effect])
    assert state.time.time_hhmm.startswith("10:")
    assert state.time.slot == "morning"


# ============================================================================
# FLOW CONTROL EFFECTS
# ============================================================================

async def test_goto_effect(started_fixture_engine):
    """
    Test goto effect (forced node transition).

    Should test:
    - Force transition to target node
    - Override normal transition logic
    - Update current_node
    - Add to nodes_history
    - Apply target node entry_effects
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    effect = GotoEffect(node="campus_hub")
    engine.runtime.effect_resolver.apply_effects([effect])
    assert state.current_node == "campus_hub"


async def test_conditional_effect_then_otherwise(started_fixture_engine):
    """
    Test conditional effect with then/otherwise branches.

    Should test:
    - when condition evaluates true -> execute then effects
    - when condition evaluates false -> execute otherwise effects
    - when_all conditions
    - when_any conditions
    - Nested conditionals
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    effect = ConditionalEffect(
        when="flags.met_alex == true",
        then=[FlagSetEffect(key="route", value="friendly")],
        otherwise=[FlagSetEffect(key="route", value="neutral")],
    )
    engine.runtime.effect_resolver.apply_effects([effect])
    assert state.flags["route"] == "neutral"
    state.flags["met_alex"] = True
    engine.runtime.effect_resolver.apply_effects([effect])
    assert state.flags["route"] == "friendly"


async def test_random_effect_weighted_choices(started_fixture_engine):
    """
    Test random effect with weighted choices.

    Should test:
    - Multiple choices with weights
    - Deterministic RNG selection
    - Total weight calculation
    - Effect execution from selected choice
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    state.flags["route"] = "neutral"
    effect = RandomEffect(
        choices=[
            RandomChoice(weight=1, effects=[FlagSetEffect(key="route", value="random_a")]),
            RandomChoice(weight=1, effects=[FlagSetEffect(key="route", value="random_b")]),
        ]
    )
    engine.runtime.effect_resolver.apply_effects([effect])
    assert state.flags["route"] in {"random_a", "random_b"}


# ============================================================================
# MODIFIER EFFECTS
# ============================================================================

async def test_remove_modifier_effect(started_fixture_engine):
    """
    Test remove_modifier effect.

    Should test:
    - Remove active modifier
    - Trigger on_exit effects
    - Clear modifier from character state
    - Handle non-existent modifier gracefully
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    engine.runtime.effect_resolver.apply_effects(
        [ApplyModifierEffect(target="player", modifier_id="caffeinated", duration=10)]
    )
    assert state.modifiers["player"]
    engine.runtime.effect_resolver.apply_effects([RemoveModifierEffect(target="player", modifier_id="caffeinated")])
    assert not state.modifiers["player"]


# ============================================================================
# UNLOCK/LOCK EFFECTS
# ============================================================================

async def test_unlock_effect_all_categories(started_fixture_engine):
    """
    Test unlock effect for all categories.

    Should test:
    - Unlock items
    - Unlock clothing
    - Unlock outfits
    - Unlock zones
    - Unlock locations
    - Unlock actions
    - Unlock endings
    - Update unlocked lists in state
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    effect = UnlockEffect(
        locations=["cafe"],
        zones=["downtown"],
        actions=["unlock_cafe_route"],
        endings=["demo_complete"],
        items=["keycard"],
        clothing=["jacket"],
    )
    engine.runtime.effect_resolver.apply_effects([effect])
    assert "cafe" in state.discovered_locations
    assert "downtown" in state.discovered_zones
    assert "unlock_cafe_route" in state.unlocked_actions
    assert "demo_complete" in state.unlocked_endings
    assert "keycard" in state.unlocked_items
    assert "jacket" in state.unlocked_clothing


async def test_lock_effect_all_categories(started_fixture_engine):
    """
    Test lock effect for all categories.

    Should test:
    - Lock items
    - Lock clothing
    - Lock outfits
    - Lock zones
    - Lock locations
    - Lock actions
    - Lock endings
    - Remove from unlocked lists in state
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    state.discovered_locations.update(["cafe"])
    state.discovered_zones.update(["downtown"])
    state.unlocked_actions.append("unlock_cafe_route")
    state.unlocked_endings.append("demo_complete")
    state.unlocked_items.append("keycard")
    state.unlocked_clothing.append("jacket")

    effect = LockEffect(
        locations=["cafe"],
        zones=["downtown"],
        actions=["unlock_cafe_route"],
        endings=["demo_complete"],
        items=["keycard"],
        clothing=["jacket"],
    )
    engine.runtime.effect_resolver.apply_effects([effect])
    assert "cafe" in state.locations and state.locations["cafe"].locked is True
    assert "downtown" in state.zones and state.zones["downtown"].locked is True
    assert "unlock_cafe_route" not in state.unlocked_actions
    assert "demo_complete" not in state.unlocked_endings


# ============================================================================
# EFFECT GUARDS & VALIDATION
# ============================================================================

async def test_effect_guard_when_condition(started_fixture_engine):
    """
    Test effect guard with when condition.

    Should test:
    - Effect executes when condition is true
    - Effect skips when condition is false
    - No error/warning when guard fails
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    state.flags["met_alex"] = False
    state.characters["player"].meters["energy"] = 50
    guarded = MeterChangeEffect(target="player", meter="energy", op="add", value=10)
    guarded.when = "flags.met_alex == true"
    engine.runtime.effect_resolver.apply_effects([guarded])
    assert state.characters["player"].meters["energy"] != 60
    state.flags["met_alex"] = True
    engine.runtime.effect_resolver.apply_effects([guarded])
    assert state.characters["player"].meters["energy"] >= 60


async def test_effect_guard_when_all_conditions(started_fixture_engine):
    """
    Test effect guard with when_all conditions.

    Should test:
    - Effect executes when all conditions are true
    - Effect skips when any condition is false
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    guarded = FlagSetEffect(key="route", value="combo")
    guarded.when_all = ["flags.met_alex == true", "flags.hidden_clue == true"]
    engine.runtime.effect_resolver.apply_effects([guarded])
    assert state.flags["route"] != "combo"
    state.flags["met_alex"] = True
    state.flags["hidden_clue"] = True
    engine.runtime.effect_resolver.apply_effects([guarded])
    assert state.flags["route"] == "combo"


async def test_effect_guard_when_any_conditions(started_fixture_engine):
    """
    Test effect guard with when_any conditions.

    Should test:
    - Effect executes when any condition is true
    - Effect skips when all conditions are false
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    guarded = FlagSetEffect(key="route", value="any")
    guarded.when_any = ["flags.met_alex == true", "flags.hidden_clue == true"]
    engine.runtime.effect_resolver.apply_effects([guarded])
    assert state.flags["route"] != "any"
    state.flags["hidden_clue"] = True
    engine.runtime.effect_resolver.apply_effects([guarded])
    assert state.flags["route"] == "any"


async def test_effect_validation_rejects_invalid_effects(started_fixture_engine):
    """
    Test effect validation.

    Should test:
    - Unknown effect type rejected
    - Invalid target character rejected
    - Invalid item ID rejected
    - Invalid meter ID rejected
    - Invalid flag ID rejected
    - Warnings logged for invalid effects
    """
    engine, _ = started_fixture_engine
    with pytest.raises(Exception):
        engine.runtime.effect_resolver.apply_effects([{"type": "unknown_type"}])


async def test_effect_execution_order(started_fixture_engine):
    """
    Test that effects execute in correct order.

    Should test:
    - Effects execute sequentially
    - Earlier effects influence later effects
    - Order matters for state changes
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    effects = [
        FlagSetEffect(key="met_alex", value=True),
        ConditionalEffect(
            when="flags.met_alex == true",
            then=[FlagSetEffect(key="route", value="ordered")],
            otherwise=[FlagSetEffect(key="route", value="out_of_order")],
        ),
    ]
    engine.runtime.effect_resolver.apply_effects(effects)
    assert state.flags["route"] == "ordered"
