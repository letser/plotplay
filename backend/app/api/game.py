# backend/app/api/game.py (replace content)
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.core.game_loader import GameLoader
from app.core.state_manager import StateManager, GameState
from app.core.conditions import ConditionEvaluator
import uuid

router = APIRouter()

# In-memory session storage (replace with Redis in production)
game_sessions: Dict[str, StateManager] = {}


class GameAction(BaseModel):
    action_type: str  # 'dialogue', 'move', 'interact', 'use_item'
    target: Optional[str] = None
    dialogue: Optional[str] = None
    choice_id: Optional[str] = None


class GameResponse(BaseModel):
    session_id: str
    narrative: str
    choices: List[Dict[str, Any]]
    state_summary: Dict[str, Any]
    current_location: str
    present_characters: List[str]


@router.get("/list")
async def list_games():
    """List all available games"""
    loader = GameLoader()
    return {"games": loader.list_games()}


@router.post("/start/{game_id}")
async def start_game(game_id: str) -> GameResponse:
    """Start a new game session"""
    try:
        # Load game definition
        loader = GameLoader()
        game_def = loader.load_game(game_id)

        # Create state manager
        state_mgr = StateManager(game_def)

        # Generate session ID
        session_id = str(uuid.uuid4())
        game_sessions[session_id] = state_mgr

        # Get starting node
        start_node = next((n for n in game_def.nodes if n['id'] == 'start'), None)
        if not start_node:
            start_node = {
                'id': 'start',
                'description': game_def.world.get('world', {}).get('setting', 'Welcome to the game!'),
                'choices': [{'id': 'begin', 'text': 'Begin Adventure'}]
            }

        return GameResponse(
            session_id=session_id,
            narrative=start_node.get('description', 'Your adventure begins...'),
            choices=start_node.get('choices', []),
            state_summary={
                'day': state_mgr.state.day,
                'time': state_mgr.state.time_slot,
                'meters': state_mgr.state.meters
            },
            current_location=state_mgr.state.location_current,
            present_characters=state_mgr.state.present_chars
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/action/{session_id}")
async def process_action(session_id: str, action: GameAction) -> GameResponse:
    """Process a game action"""
    if session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    state_mgr = game_sessions[session_id]

    # TODO: Process action through AI models
    # For now, return a simple response

    # Update state based on action
    state_mgr.state.actions_this_slot += 1

    # Check if time should advance
    time_settings = state_mgr.game_def.config['game']['settings'].get('time_system', {})
    if state_mgr.state.actions_this_slot >= time_settings.get('actions_per_slot', 3):
        state_mgr.apply_effects([{'type': 'advance_time', 'slots': 1}])

    return GameResponse(
        session_id=session_id,
        narrative=f"You chose to {action.action_type}. The story continues...",
        choices=[
            {'id': 'continue', 'text': 'Continue exploring'},
            {'id': 'rest', 'text': 'Rest for a while'}
        ],
        state_summary={
            'day': state_mgr.state.day,
            'time': state_mgr.state.time_slot,
            'meters': state_mgr.state.meters
        },
        current_location=state_mgr.state.location_current,
        present_characters=state_mgr.state.present_chars
    )


@router.get("/session/{session_id}/state")
async def get_state(session_id: str):
    """Get current game state"""
    if session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    state_mgr = game_sessions[session_id]
    return {"state": state_mgr.state.to_dict()}