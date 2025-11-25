"""Test script to verify engine error handling for invalid actions."""
import asyncio
from app.core.loader import GameLoader
from app.runtime.engine import PlotPlayEngine
from app.runtime.types import PlayerAction
from app.scenarios.mock_ai import MockAIService
from app.scenarios.models import MockResponses


async def test_errors():
    # Load game
    game = GameLoader().load_game('coffeeshop_date')

    # Setup mock AI
    ai = MockAIService()
    mocks = MockResponses(
        writer={
            'intro': 'You arrive at the cafe.',
            'test': 'Something happens.'
        },
        checker={
            'default': {'meters': {}, 'flags': {}, 'character_memories': {}, 'safety': {'ok': True}}
        }
    )
    ai.load_mocks(mocks)

    # Create engine
    engine = PlotPlayEngine(game, session_id='test-errors', ai_service=ai)

    # Start game
    ai.set_mock_key('intro')
    result = await engine.start()
    print(f'✓ Game started at: {result.state_summary["location"]["id"]}')
    print()

    # Test invalid actions
    print('=== Testing Invalid Actions ===\n')

    tests = [
        ('Invalid compass direction', PlayerAction(action_type='move', direction='invalid')),
        ('Move to nonexistent location', PlayerAction(action_type='goto', location='fake_place')),
        ('Travel to nonexistent location', PlayerAction(action_type='travel', location='fake_zone')),
        ('Select nonexistent choice', PlayerAction(action_type='choice', choice_id='fake_choice')),
        ('Use nonexistent item', PlayerAction(action_type='use', item_id='fake_item')),
        ('Give item you don\'t have', PlayerAction(action_type='give', item_id='fake_item', target='alex')),
    ]

    for name, action in tests:
        try:
            ai.set_mock_key('test')
            result = await engine.process_action(action)
            print(f'✗ {name}')
            print(f'  Expected error but got success')
            print(f'  Narrative: {result.narrative[:80]}...')
        except ValueError as e:
            print(f'✓ {name}')
            print(f'  ValueError: {str(e)[:80]}')
        except RuntimeError as e:
            print(f'✓ {name}')
            print(f'  RuntimeError: {str(e)[:80]}')
        except Exception as e:
            print(f'? {name}')
            print(f'  {type(e).__name__}: {str(e)[:80]}')
        print()


if __name__ == '__main__':
    asyncio.run(test_errors())
