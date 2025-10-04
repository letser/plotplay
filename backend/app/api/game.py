from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Literal, Dict
import uuid

from app.core.game_loader import GameLoader
from app.core.game_engine import GameEngine

router = APIRouter()

# In-memory session storage. In a production app, this would be a database or Redis.
game_sessions: Dict[str, GameEngine] = {}


class StartGameRequest(BaseModel):
    game_id: str


class GameAction(BaseModel):
    action_type: Literal["say", "do", "choice", "use", "give"]
    action_text: str | None = None
    target: str | None = None
    choice_id: str | None = None
    item_id: str | None = None


class GameResponse(BaseModel):
    session_id: str
    narrative: str
    choices: list[dict[str, Any]]
    state_summary: dict[str, Any]
    time_advanced: bool = False
    location_changed: bool = False


@router.get("/list")
async def list_games():
    """List all available games."""
    loader = GameLoader()
    return {"games": loader.list_games()}


@router.post("/start")
async def start_game(request: StartGameRequest) -> GameResponse:
    """Start a new game session."""
    session_id = str(uuid.uuid4())
    try:
        loader = GameLoader()
        game_def = loader.load_game(request.game_id)
        engine = GameEngine(game_def, session_id)

        game_sessions[session_id] = engine

        # A default "look around" action to generate the first narrative block
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
        # Log the full exception for debugging
        # engine.logger.error(f"Failed to start game '{request.game_id}': {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/action/{session_id}")
async def process_action(session_id: str, action: GameAction) -> GameResponse:
    """Process a game action."""
    if session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    engine = game_sessions[session_id]

    try:
        result = await engine.process_action(
            action_type=action.action_type,
            action_text=action.action_text,
            target=action.target,
            choice_id=action.choice_id,
            item_id=action.item_id
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
        # engine.logger.error(f"Action failed in session '{session_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/session/{session_id}/state")
async def get_state(session_id: str):
    """Get a detailed game state for debugging."""
    if session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    engine = game_sessions[session_id]
    return {
        "state": engine.state_manager.state.to_dict(),
        "history": engine.state_manager.state.narrative_history[-5:]
    }