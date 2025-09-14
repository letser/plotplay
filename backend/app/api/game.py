from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Literal
from app.core.game_loader import GameLoader
from app.core.game_engine import GameEngine
import uuid

router = APIRouter()

# Session storage
game_sessions: Dict[str, GameEngine] = {}


class GameAction(BaseModel):
    action_type: Literal["say", "do", "choice"]  # New action types
    action_text: str
    target: Optional[str] = None
    choice_id: Optional[str] = None  # For predefined choices


class GameResponse(BaseModel):
    session_id: str
    narrative: str
    choices: List[Dict[str, Any]]
    state_summary: Dict[str, Any]
    time_advanced: bool = False
    location_changed: bool = False


@router.get("/list")
async def list_games():
    """List all available games"""
    loader = GameLoader()
    return {"games": loader.list_games()}


@router.post("/start/{game_id}")
async def start_game(game_id: str) -> GameResponse:
    """Start a new game session"""
    try:
        # Load game and create engine
        loader = GameLoader()
        game_def = loader.load_game(game_id)
        engine = GameEngine(game_def)

        # Generate session ID
        session_id = str(uuid.uuid4())
        game_sessions[session_id] = engine

        # Get a starting narrative
        result = await engine.process_action(
            action_type="do",
            action_text="Look around and observe the surroundings"
        )

        return GameResponse(
            session_id=session_id,
            narrative=result['narrative'],
            choices=result['choices'],
            state_summary=result['current_state'],
            time_advanced=result.get('time_advanced', False),
            location_changed=result.get('location_changed', False)
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/action/{session_id}")
async def process_action(session_id: str, action: GameAction) -> GameResponse:
    """Process a game action"""
    if session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    engine = game_sessions[session_id]

    try:
        # Process action
        result = await engine.process_action(
            action_type=action.action_type,
            action_text=action.action_text,
            target=action.target,
            choice_id=action.choice_id
        )

        return GameResponse(
            session_id=session_id,
            narrative=result['narrative'],
            choices=result['choices'],
            state_summary=result['current_state'],
            time_advanced=result.get('time_advanced', False),
            location_changed=result.get('location_changed', False)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/session/{session_id}/state")
async def get_state(session_id: str):
    """Get a detailed game state"""
    if session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    engine = game_sessions[session_id]
    return {
        "state": engine.state_manager.state.to_dict(),
        "history": engine.narrative_history[-5:]  # Last 5 narratives
    }