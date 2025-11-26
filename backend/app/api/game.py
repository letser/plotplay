"""
Main game API endpoints.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, Literal, Dict
import uuid
import json

from app.core.loader import GameLoader
from app.runtime.engine import PlotPlayEngine
from app.runtime.types import PlayerAction
from app.services.ai_service import AIService

router = APIRouter()

# In-memory session storage. In a production app, this would be a database or Redis.
game_sessions: Dict[str, PlotPlayEngine] = {}


class StartGameRequest(BaseModel):
    game_id: str


class GameAction(BaseModel):
    action_type: Literal["say", "do", "choice", "use", "give"]
    action_text: str | None = None
    target: str | None = None
    choice_id: str | None = None
    item_id: str | None = None
    skip_ai: bool = False


class GameResponse(BaseModel):
    session_id: str
    narrative: str
    choices: list[dict[str, Any]]
    state_summary: dict[str, Any]
    time_advanced: bool = False
    location_changed: bool = False
    generated_seed: int | None = None
    action_summary: str | None = None


def _get_engine(session_id: str) -> PlotPlayEngine:
    engine = game_sessions.get(session_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Session not found")
    return engine


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
        # IMPORTANT: Use real AIService (OpenRouter) for production
        # Tests use MockAIService (see tests_v2/conftest.py)
        ai_service = AIService()
        engine = PlotPlayEngine(game_def, session_id, ai_service=ai_service)

        game_sessions[session_id] = engine

        # A default "look around" action to generate the first narrative block
        result = await engine.process_action(
            PlayerAction(action_type="do", action_text="Look around and observe the surroundings")
        )

        return GameResponse(
            session_id=session_id,
            narrative=result.narrative,
            choices=result.choices,
            state_summary=result.state_summary,
            time_advanced=result.time_advanced,
            location_changed=result.location_changed,
            generated_seed=engine.runtime.generated_seed,
            action_summary=result.action_summary,
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/start/stream")
async def start_game_stream(request: StartGameRequest):
    """Start a new game session with streaming narrative (fast opening scene)."""
    session_id = str(uuid.uuid4())

    async def generate():
        try:
            print(f"[START] Loading game {request.game_id}...")
            loader = GameLoader()
            game_def = loader.load_game(request.game_id)
            print(f"[START] Game loaded, creating engine...")
            # IMPORTANT: Use real AIService (OpenRouter) for production
            # Tests use MockAIService (see tests_v2/conftest.py)
            ai_service = AIService()
            engine = PlotPlayEngine(game_def, session_id, ai_service=ai_service)
            print(f"[START] Engine created")

            game_sessions[session_id] = engine

            # Send session info first
            session_event = {
                "type": "session_created",
                "session_id": session_id,
                "generated_seed": engine.runtime.generated_seed
            }
            yield f"data: {json.dumps(session_event)}\n\n"
            print(f"[START] Session created event sent")

            # Send initial state snapshot immediately (before narrative)
            # This populates all the panels right away
            initial_state = engine.state_summary.build()
            current_node = engine.runtime.index.nodes.get(engine.runtime.state_manager.state.current_node)
            initial_choices = engine.choice_builder.build(current_node, [])

            initial_state_event = {
                "type": "initial_state",
                "state_summary": initial_state,
                "choices": initial_choices
            }
            yield f"data: {json.dumps(initial_state_event)}\n\n"
            print(f"[START] Initial state sent")

            # Send action summary immediately
            action_summary_event = {
                "type": "action_summary",
                "content": "You arrive at the scene."
            }
            yield f"data: {json.dumps(action_summary_event)}\n\n"
            print(f"[START] Action summary sent")

            # Stream opening scene (Writer only, no Checker)
            print(f"[START] Starting opening scene stream...")
            result = await engine.process_action(
                PlayerAction(action_type="do", action_text="Look around and observe the surroundings")
            )
            completion_event = {
                "type": "complete",
                "narrative": result.narrative,
                "choices": result.choices,
                "state_summary": result.state_summary,
                "action_summary": result.action_summary,
            }
            yield f"data: {json.dumps(completion_event)}\n\n"

            yield "data: [DONE]\n\n"
            print(f"[START] Done!")

        except Exception as e:
            print(f"[START ERROR] {e}")
            import traceback
            traceback.print_exc()
            error_event = {
                "type": "error",
                "message": str(e)
            }
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/action/{session_id}")
async def process_action(session_id: str, action: GameAction) -> GameResponse:
    """Process a game action."""
    engine = _get_engine(session_id)

    try:
        if isinstance(engine, PlotPlayEngine):
            player_action = PlayerAction(
                action_type=action.action_type,
                action_text=action.action_text,
                choice_id=action.choice_id,
                item_id=action.item_id,
                target=action.target,
                skip_ai=action.skip_ai,
            )
            result = await engine.process_action(player_action)
            return GameResponse(
                session_id=session_id,
                narrative=result.narrative,
                choices=result.choices,
                state_summary=result.state_summary,
                time_advanced=result.time_advanced,
                location_changed=result.location_changed,
                action_summary=result.action_summary,
            )
        else:
            result = await engine.process_action(
                action_type=action.action_type,
                action_text=action.action_text,
                target=action.target,
                choice_id=action.choice_id,
                item_id=action.item_id,
                skip_ai=action.skip_ai,
            )

            return GameResponse(
                session_id=session_id,
                narrative=result['narrative'],
                choices=result['choices'],
                state_summary=result['current_state'],
                time_advanced=result.get('time_advanced', False),
                location_changed=result.get('location_changed', False),
                action_summary=result.get("action_summary"),
            )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/action/{session_id}/stream")
async def process_action_stream(session_id: str, action: GameAction):
    """Process a game action with streaming narrative response."""
    engine = _get_engine(session_id)

    async def generate():
        try:
            if isinstance(engine, PlotPlayEngine):
                player_action = PlayerAction(
                    action_type=action.action_type,
                    action_text=action.action_text,
                    choice_id=action.choice_id,
                    item_id=action.item_id,
                    target=action.target,
                    skip_ai=action.skip_ai,
                )
                async for chunk in engine.process_action_stream(player_action):
                    yield f"data: {json.dumps(chunk)}\n\n"
            else:
                # First, send the action summary immediately for legacy engine
                action_summary_event = {
                    "type": "action_summary",
                    "content": f"Processing action..."
                }
                yield f"data: {json.dumps(action_summary_event)}\n\n"

                async for chunk in engine.process_action_stream(
                    action_type=action.action_type,
                    action_text=action.action_text,
                    target=action.target,
                    choice_id=action.choice_id,
                    item_id=action.item_id,
                    skip_ai=action.skip_ai,
                ):
                    yield f"data: {json.dumps(chunk)}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"ERROR in process_action_stream: {error_details}")
            engine.logger.error(f"Stream error: {error_details}")
            error_event = {
                "type": "error",
                "message": f"{str(e)}\n{error_details}"
            }
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
