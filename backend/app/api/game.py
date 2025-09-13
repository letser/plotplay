from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter()

class GameAction(BaseModel):
    action: str
    target: Optional[str] = None
    dialogue: Optional[str] = None

class GameState(BaseModel):
    node_id: str
    narrative: str
    choices: List[str]
    state: dict

@router.get("/list")
async def list_games():
    """List available games"""
    return {
        "games": [
            {"id": "college_romance", "title": "College Romance", "nsfw": True},
            {"id": "cyberpunk_noir", "title": "Neon Shadows", "nsfw": True}
        ]
    }

@router.post("/start/{game_id}")
async def start_game(game_id: str):
    """Start a new game"""
    return {
        "session_id": "temp_session",
        "game_id": game_id,
        "state": {
            "node_id": "start",
            "narrative": "Welcome to PlotPlay!",
            "choices": ["Begin Adventure"]
        }
    }

@router.post("/action/{session_id}")
async def game_action(session_id: str, action: GameAction):
    """Process a game action"""
    return {
        "state": {
            "node_id": "next",
            "narrative": f"You chose: {action.action}",
            "choices": ["Continue"]
        }
    }
