
import pytest
from app.core.game_engine import GameEngine
from app.models.actions import Action
from app.models.effects import InventoryAddEffect

@pytest.mark.asyncio
async def test_deterministic_action_execution(game_for_effects_test, mock_ai_service):
    """
    Test that deterministic actions (like 'purchase') are executed 
    in the main pipeline without relying on AI.
    """
    # Setup game with economy
    game_for_effects_test.economy.enabled = True
    game_for_effects_test.economy.currency_symbol = "$"
    
    # Give player some money
    engine = GameEngine(game_for_effects_test, session_id="test-deterministic", ai_service=mock_ai_service)
    state = engine.state_manager.state
    state.meters["player"]["money"] = 100
    
    # Define an item price (implicitly or explicitly)
    # For this test, we'll try to purchase 'potion' which is in the game definition
    # We need to make sure it's available to buy. 
    # Usually purchase requires a seller or location inventory, 
    # but let's see if we can trigger the purchase logic.
    
    # In the current implementation, 'purchase' is a deterministic action.
    # We expect process_action to handle it.
    
    # We'll try to buy a potion.
    # Note: The game_for_effects_test fixture might need adjustment to support purchase 
    # if purchase logic checks for item availability in location.
    # For now, let's just see if the engine even TRIES to handle the action type.
    
    # We can mock the internal handler or check the state change.
    # Let's try to trigger a simple 'move' action first, as that's also deterministic.
    
    # Add a connection to the room
    # The game has 'room' and 'hall'. Let's connect them.
    # (The fixture defines them in the same zone but no explicit paths in the fixture code shown, 
    # but let's assume we can try to move or just check if the method is called)
    
    # Actually, let's look at 'purchase_item' helper in game_engine.py. 
    # It checks if item exists. 'potion' exists.
    
    # We need to make sure the action is processed.
    result = await engine.process_action(
        action_type="purchase",
        item_id="potion",
        skip_ai=True
    )
    
    # If the action was handled, we should see a result.
    # But more importantly, we want to see if the purchase logic was executed.
    # Since we didn't set up a seller, it might fail, but it should return a failure message
    # NOT just ignore it or return an empty result.
    
    # However, since _execute_action_effects currently ONLY handles 'choice',
    # we expect this to effectively do nothing or fail to produce the expected side effects.
    
    # Let's check if we can spy on the purchase_item method or check state.
    # If we can't buy, maybe we can 'drop' something we have.
    
    # Give player a potion
    engine.apply_effects([
        InventoryAddEffect(target="player", item_type="item", item="potion", count=1)
    ])
    assert state.inventory["player"]["potion"] == 1
    
    # Now try to drop it
    await engine.process_action(
        action_type="drop",
        item_id="potion",
        skip_ai=True
    )
    
    # If logic works, potion count should be 0
    assert state.inventory["player"]["potion"] == 0, "Drop action was not executed!"
