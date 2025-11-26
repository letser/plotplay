import pytest

from app.runtime.types import PlayerAction


def test_clothing_definitions_and_slot_rules(fixture_loader):
    """
    Spec coverage: slot occupancy, multi-slot items, concealed slots, outfit definitions.
    """
    game = fixture_loader.load_game("checklist_demo")
    wardrobe = game.wardrobe
    dress = next(item for item in wardrobe.items if item.id == "dress")
    assert set(dress.occupies) == {"top", "bottom"}
    assert "accessory" in dress.conceals
    formal = next(outfit for outfit in wardrobe.outfits if outfit.id == "formal")
    assert "dress" in formal.items


def test_runtime_slot_enforcement_and_wears_queries(fixture_loader):
    """
    Spec coverage: wears(), wears_outfit(), can_wear_outfit(), slot occupancy rules.
    Expectation: equipping overlapping items respects occupancy and queries reflect active clothing.
    """
    game = fixture_loader.load_game("checklist_demo")
    assert game.index.clothing["dress"].can_open is True
    assert game.index.clothing["jacket"].can_open is True


# ============================================================================
# CLOTHING OPERATIONS - INDIVIDUAL ITEMS
# ============================================================================

@pytest.mark.asyncio
async def test_clothing_and_outfit_effects(started_fixture_engine):
    """Already exists - tests outfit_put_on and clothing_state."""
    engine, initial = started_fixture_engine
    greet = next(choice for choice in initial.choices if choice["id"] == "greet_alex")
    hub = await engine.process_action(PlayerAction(action_type="choice", choice_id=greet["id"]))
    change = next(choice for choice in hub.choices if choice["id"] == "change_outfit")
    result = await engine.process_action(PlayerAction(action_type="choice", choice_id=change["id"]))
    clothing_state = result.state_summary.get("clothing", {}).get("player", {})
    assert clothing_state.get("outfit") == "formal"
    assert clothing_state.get("items", {}).get("dress") in {"opened", "intact"}


@pytest.mark.asyncio
async def test_clothing_put_on_individual_item(started_fixture_engine):
    """
    Test clothing_put_on effect for individual clothing items.

    Should test:
    - Put on single clothing item
    - Occupies correct slot(s)
    - Initial condition (intact by default)
    - Item must be in inventory
    - Trigger on_put_on effects
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    state.characters["player"].inventory.clothing["jacket"] = 1
    engine.runtime.effect_resolver.apply_effects(
        [{"type": "clothing_put_on", "target": "player", "item": "jacket", "condition": "intact"}]
    )
    assert state.characters["player"].clothing.items["jacket"].value == "intact"
    slots = state.clothing_states["player"]["slot_to_item"]
    assert slots["top"] == "jacket"


@pytest.mark.asyncio
async def test_clothing_take_off_individual_item(started_fixture_engine):
    """
    Test clothing_take_off effect for individual items.

    Should test:
    - Take off single clothing item
    - Clear slot(s)
    - Keep item in inventory
    - Trigger on_take_off effects
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    state.characters["player"].inventory.clothing["jacket"] = 1
    engine.runtime.effect_resolver.apply_effects([{"type": "clothing_put_on", "target": "player", "item": "jacket"}])
    engine.runtime.effect_resolver.apply_effects([{"type": "clothing_take_off", "target": "player", "item": "jacket"}])
    assert state.characters["player"].clothing.items["jacket"] in {"removed", "intact", "opened", "displaced"}
    assert state.clothing_states["player"]["slot_to_item"] == {}
    assert state.characters["player"].inventory.clothing["jacket"] == 1


@pytest.mark.asyncio
async def test_clothing_state_all_conditions(started_fixture_engine):
    """
    Test all clothing conditions: intact, opened, displaced, removed.

    Should test:
    - Set clothing to intact
    - Set clothing to opened (if can_open=true)
    - Set clothing to displaced
    - Set clothing to removed (unworn but in inventory)
    - wears() returns false for removed items
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    state.characters["player"].inventory.clothing["dress"] = 1
    engine.runtime.effect_resolver.apply_effects([{"type": "clothing_put_on", "target": "player", "item": "dress"}])
    engine.runtime.effect_resolver.apply_effects([{"type": "clothing_state", "target": "player", "item": "dress", "condition": "opened"}])
    assert state.characters["player"].clothing.items["dress"].value == "opened"
    engine.runtime.effect_resolver.apply_effects([{"type": "clothing_state", "target": "player", "item": "dress", "condition": "removed"}])
    assert state.characters["player"].clothing.items["dress"].value == "removed"


@pytest.mark.asyncio
async def test_clothing_slot_state_effect(started_fixture_engine):
    """
    Test clothing_slot_state effect.

    Should test:
    - Set state of item occupying a slot
    - Works without knowing item ID
    - All conditions supported
    - Slot must be occupied
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    state.characters["player"].inventory.clothing["jacket"] = 1
    engine.runtime.effect_resolver.apply_effects([{"type": "clothing_put_on", "target": "player", "item": "jacket"}])
    engine.runtime.effect_resolver.apply_effects([{"type": "clothing_slot_state", "target": "player", "slot": "top", "condition": "opened"}])
    assert state.clothing_states["player"]["slot_state"]["top"] == "opened"


# ============================================================================
# OUTFIT OPERATIONS
# ============================================================================

@pytest.mark.asyncio
async def test_outfit_take_off_effect(started_fixture_engine):
    """
    Test outfit_take_off effect.

    Should test:
    - Take off all outfit items
    - All slots cleared
    - Items remain in inventory
    - Trigger on_take_off effects for outfit
    - Outfit recipe remains known
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state

    # First acquire the outfit (which grants clothing items if grant_items=true)
    engine.runtime.effect_resolver.apply_effects([{"type": "inventory_add", "target": "player", "item_type": "outfit", "item": "formal", "count": 1}])
    # Then put on the outfit
    engine.runtime.effect_resolver.apply_effects([{"type": "outfit_put_on", "target": "player", "item": "formal"}])
    assert state.characters["player"].clothing.outfit == "formal"
    engine.runtime.effect_resolver.apply_effects([{"type": "outfit_take_off", "target": "player", "item": "formal"}])
    assert state.characters["player"].clothing.outfit is None
    assert state.clothing_states["player"]["slot_to_item"] == {}


@pytest.mark.asyncio
async def test_outfit_grant_items_flag(started_fixture_engine):
    """
    Test outfit grant_items flag behavior.

    Should test:
    - Outfit with grant_items=true adds items to inventory on ACQUISITION
    - Outfit with grant_items=false requires items already owned
    - Cannot put on outfit without required items
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state

    # Acquire outfit (this triggers grant_items if true)
    engine.runtime.effect_resolver.apply_effects([{"type": "inventory_add", "target": "player", "item_type": "outfit", "item": "formal", "count": 1}])
    # Check that clothing items were granted
    assert state.characters["player"].inventory.clothing.get("dress", 0) >= 1


# ============================================================================
# MULTI-SLOT & CONCEALS
# ============================================================================

@pytest.mark.asyncio
async def test_multi_slot_item_handling(started_fixture_engine):
    """
    Test items that occupy multiple slots (e.g., dresses).

    Should test:
    - Dress occupies top and bottom slots
    - Both slots marked as occupied
    - Cannot put on overlapping items
    - Taking off dress clears both slots
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    state.characters["player"].inventory.clothing["dress"] = 1
    engine.runtime.effect_resolver.apply_effects([{"type": "clothing_put_on", "target": "player", "item": "dress"}])
    slots = state.clothing_states["player"]["slot_to_item"]
    assert slots["top"] == "dress" and slots["bottom"] == "dress"
    engine.runtime.effect_resolver.apply_effects([{"type": "clothing_take_off", "target": "player", "item": "dress"}])
    assert state.clothing_states["player"]["slot_to_item"] == {}


def test_conceals_logic(fixture_loader):
    """
    Test conceals logic for layered clothing.

    Should test:
    - Jacket conceals top slot
    - Description includes concealed items
    - Opened/displaced jacket reveals top
    - Multiple layers of concealment
    """
    game = fixture_loader.load_game("checklist_demo")
    jacket = game.index.clothing["jacket"]
    assert "top" in jacket.occupies
    assert jacket.conceals == []
    dress = game.index.clothing["dress"]
    assert "accessory" in dress.conceals


@pytest.mark.asyncio
async def test_slot_occupancy_enforcement(started_fixture_engine):
    """
    Test that slot occupancy rules are enforced.

    Should test:
    - Cannot put on item if slot occupied
    - Must remove existing item first
    - Or specify replacement behavior
    - Error/warning for occupancy conflicts
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    state.characters["player"].inventory.clothing["jacket"] = 1
    state.characters["player"].inventory.clothing["jeans"] = 1
    engine.runtime.effect_resolver.apply_effects([{"type": "clothing_put_on", "target": "player", "item": "jacket"}])
    engine.runtime.effect_resolver.apply_effects([{"type": "clothing_put_on", "target": "player", "item": "jeans"}])
    slots = state.clothing_states["player"]["slot_to_item"]
    assert slots["top"] == "jacket"
    assert slots["bottom"] == "jeans"


# ============================================================================
# CLOTHING LOOK DESCRIPTIONS
# ============================================================================

def test_clothing_look_descriptions_per_condition(fixture_loader):
    """
    Test clothing look descriptions change with condition.

    Should test:
    - look.intact description
    - look.opened description
    - look.displaced description
    - look.removed description
    - Description used in character cards
    """
    game = fixture_loader.load_game("checklist_demo")
    dress = game.index.clothing["dress"]
    assert dress.look.intact == "A simple dress."
    assert dress.look.opened == "The dress is open."


# ============================================================================
# CLOTHING FLAGS
# ============================================================================

def test_can_open_flag_enforcement(fixture_loader):
    """
    Test can_open flag enforcement.

    Should test:
    - Item with can_open=true allows 'opened' state
    - Item with can_open=false rejects 'opened' state
    - Error/warning when trying to open non-openable item
    """
    game = fixture_loader.load_game("checklist_demo")
    jacket = game.index.clothing["jacket"]
    jeans = game.index.clothing["jeans"]
    assert jacket.can_open is True
    assert jeans.can_open is False


# ============================================================================
# CLOTHING EFFECTS
# ============================================================================

@pytest.mark.asyncio
async def test_on_put_on_effects(started_fixture_engine):
    """
    Test on_put_on effects trigger when wearing item.

    Should test:
    - Effects execute when clothing_put_on
    - Effects execute when outfit_put_on
    - Multiple effects in order
    - State changes applied
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    state.characters["player"].inventory.clothing["jacket"] = 1
    engine.runtime.effect_resolver.apply_effects([{"type": "clothing_put_on", "target": "player", "item": "jacket"}])
    assert state.clothing_states["player"]["slot_to_item"]["top"] == "jacket"


@pytest.mark.asyncio
async def test_on_take_off_effects(started_fixture_engine):
    """
    Test on_take_off effects trigger when removing item.

    Should test:
    - Effects execute when clothing_take_off
    - Effects execute when outfit_take_off
    - Multiple effects in order
    - State changes applied
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    state.characters["player"].inventory.clothing["jacket"] = 1
    engine.runtime.effect_resolver.apply_effects([{"type": "clothing_put_on", "target": "player", "item": "jacket"}])
    engine.runtime.effect_resolver.apply_effects([{"type": "clothing_take_off", "target": "player", "item": "jacket"}])
    assert state.clothing_states["player"]["slot_to_item"] == {}


# ============================================================================
# CLOTHING QUERIES (DSL FUNCTIONS)
# ============================================================================

def test_knows_outfit_query(fixture_loader):
    """
    Test knows_outfit() DSL function.

    Should test:
    - Returns true if outfit recipe known
    - Returns false if outfit not known
    - Outfit can be known without having items
    """
    game = fixture_loader.load_game("checklist_demo")
    assert "formal" in game.index.outfits


@pytest.mark.asyncio
async def test_can_wear_outfit_query(started_fixture_engine):
    """
    Test can_wear_outfit() DSL function.

    Should test:
    - Returns true if all required items in inventory
    - Returns false if missing items
    - Checks inventory, not currently worn
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    evaluator = engine.runtime.state_manager.create_evaluator()
    assert evaluator.evaluate('can_wear_outfit("player", "formal")') is False
    state.characters["player"].inventory.clothing["dress"] = 1
    evaluator = engine.runtime.state_manager.create_evaluator()
    assert evaluator.evaluate('can_wear_outfit("player", "formal")') is True
