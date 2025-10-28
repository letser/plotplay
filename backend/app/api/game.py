"""
Main game API endpoints.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Any, Literal, Dict
import uuid
import json
import asyncio

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


class DeterministicActionResponse(BaseModel):
    session_id: str
    success: bool
    message: str
    state_summary: dict[str, Any]
    details: dict[str, Any] | None = None
    action_summary: str | None = None


class MovementRequest(BaseModel):
    destination_id: str | None = None
    zone_id: str | None = None
    direction: str | None = None
    companions: list[str] = Field(default_factory=list)


class PurchaseRequest(BaseModel):
    buyer_id: str = "player"
    seller_id: str | None = None
    item_id: str
    count: int = 1
    price: float | None = None


class SellRequest(BaseModel):
    seller_id: str = "player"
    buyer_id: str | None = None
    item_id: str
    count: int = 1
    price: float | None = None


class InventoryTakeRequest(BaseModel):
    owner_id: str = "player"
    item_id: str
    count: int = 1


class InventoryDropRequest(BaseModel):
    owner_id: str = "player"
    item_id: str
    count: int = 1


class InventoryGiveRequest(BaseModel):
    source_id: str = "player"
    target_id: str
    item_id: str
    count: int = 1


def _get_engine(session_id: str) -> GameEngine:
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
            location_changed=result.get('location_changed', False),
            generated_seed=engine.generated_seed,
            action_summary=result.get("action_summary"),
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
            engine = GameEngine(game_def, session_id)
            print(f"[START] Engine created")

            game_sessions[session_id] = engine

            # Send session info first
            session_event = {
                "type": "session_created",
                "session_id": session_id,
                "generated_seed": engine.generated_seed
            }
            yield f"data: {json.dumps(session_event)}\n\n"
            print(f"[START] Session created event sent")

            # Send initial state snapshot immediately (before narrative)
            # This populates all the panels right away
            initial_state = engine._get_state_summary()
            initial_choices = engine._generate_choices(engine._get_current_node(), [])

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
            async for chunk in engine.generate_opening_scene_stream():
                print(f"[START] Chunk type: {chunk.get('type')}")
                yield f"data: {json.dumps(chunk)}\n\n"

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
            # First, send the action summary immediately
            action_summary_event = {
                "type": "action_summary",
                "content": f"Processing action..."
            }
            yield f"data: {json.dumps(action_summary_event)}\n\n"

            # Process action with streaming
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


@router.post("/action/{session_id}/original")
async def process_action_original(session_id: str, action: GameAction) -> GameResponse:
    """Original non-streaming endpoint (kept for backwards compatibility)."""
    return await process_action(session_id, action)


@router.post("/action_old/{session_id}")
async def process_action_old(session_id: str, action: GameAction) -> GameResponse:
    """Deprecated: Use /action/{session_id} instead."""
    engine = _get_engine(session_id)

    try:
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
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/move/{session_id}")
async def deterministic_move(session_id: str, request: MovementRequest) -> DeterministicActionResponse:
    engine = _get_engine(session_id)
    state = engine.state_manager.state
    before_location = state.location_current
    before_zone = state.zone_current

    if not any([request.destination_id, request.zone_id, request.direction]):
        raise HTTPException(status_code=400, detail="Provide destination_id, zone_id, or direction.")

    details: dict[str, Any] | None = None
    summary: dict[str, Any]
    success = False
    message = ""

    if request.destination_id:
        result = await engine.movement.handle_choice(f"move_{request.destination_id}")
        summary = result.get("current_state", engine._get_state_summary())
        message = result.get("narrative", "").strip()
        success = engine.state_manager.state.location_current != before_location
        details = {"choices": result.get("choices", [])}
    elif request.zone_id:
        result = await engine.movement.handle_choice(f"travel_{request.zone_id}")
        summary = result.get("current_state", engine._get_state_summary())
        message = result.get("narrative", "").strip()
        success = engine.state_manager.state.zone_current != before_zone
        details = {"choices": result.get("choices", [])}
    else:
        success = engine.movement.move_by_direction(request.direction, request.companions or [])
        summary = engine._get_state_summary()
        new_location = engine.locations_map.get(state.location_current)
        if success:
            dest_name = new_location.name if new_location else state.location_current
            message = f"You move {request.direction.lower()} to {dest_name}."
        else:
            message = f"You cannot move {request.direction.lower()} from here."
        details = {"location_id": state.location_current}

    if success:
        engine._update_discoveries()

    return DeterministicActionResponse(
        session_id=session_id,
        success=bool(success),
        message=message,
        state_summary=summary,
        details=details,
        action_summary=engine.state_summary.build_action_summary(message),
    )


@router.post("/shop/{session_id}/purchase")
async def deterministic_purchase(session_id: str, request: PurchaseRequest) -> DeterministicActionResponse:
    engine = _get_engine(session_id)
    if request.count <= 0:
        raise HTTPException(status_code=400, detail="count must be positive")
    success, message = engine.purchase_item(
        request.buyer_id,
        request.seller_id,
        request.item_id,
        count=request.count,
        price=request.price,
    )
    summary = engine._get_state_summary()
    return DeterministicActionResponse(
        session_id=session_id,
        success=success,
        message=message,
        state_summary=summary,
        details={
            "buyer": request.buyer_id,
            "seller": request.seller_id or engine.state_manager.state.location_current,
            "item": request.item_id,
            "count": request.count,
        },
        action_summary=engine.state_summary.build_action_summary(message),
    )


@router.post("/shop/{session_id}/sell")
async def deterministic_sell(session_id: str, request: SellRequest) -> DeterministicActionResponse:
    engine = _get_engine(session_id)
    if request.count <= 0:
        raise HTTPException(status_code=400, detail="count must be positive")
    success, message = engine.sell_item(
        request.seller_id,
        request.buyer_id,
        request.item_id,
        count=request.count,
        price=request.price,
    )
    summary = engine._get_state_summary()
    return DeterministicActionResponse(
        session_id=session_id,
        success=success,
        message=message,
        state_summary=summary,
        details={
            "seller": request.seller_id,
            "buyer": request.buyer_id or engine.state_manager.state.location_current,
            "item": request.item_id,
            "count": request.count,
        },
        action_summary=engine.state_summary.build_action_summary(message),
    )


@router.post("/inventory/{session_id}/take")
async def deterministic_take(session_id: str, request: InventoryTakeRequest) -> DeterministicActionResponse:
    engine = _get_engine(session_id)
    if request.count <= 0:
        raise HTTPException(status_code=400, detail="count must be positive")
    success, message = engine.take_item(
        request.owner_id,
        request.item_id,
        count=request.count,
    )
    summary = engine._get_state_summary()
    return DeterministicActionResponse(
        session_id=session_id,
        success=success,
        message=message,
        state_summary=summary,
        details={
            "owner": request.owner_id,
            "item": request.item_id,
            "count": request.count,
            "location": engine.state_manager.state.location_current,
        },
        action_summary=engine.state_summary.build_action_summary(message),
    )


@router.post("/inventory/{session_id}/drop")
async def deterministic_drop(session_id: str, request: InventoryDropRequest) -> DeterministicActionResponse:
    engine = _get_engine(session_id)
    if request.count <= 0:
        raise HTTPException(status_code=400, detail="count must be positive")
    success, message = engine.drop_item(
        request.owner_id,
        request.item_id,
        count=request.count,
    )
    summary = engine._get_state_summary()
    return DeterministicActionResponse(
        session_id=session_id,
        success=success,
        message=message,
        state_summary=summary,
        details={
            "owner": request.owner_id,
            "item": request.item_id,
            "count": request.count,
            "location": engine.state_manager.state.location_current,
        },
        action_summary=engine.state_summary.build_action_summary(message),
    )


@router.post("/inventory/{session_id}/give")
async def deterministic_give(session_id: str, request: InventoryGiveRequest) -> DeterministicActionResponse:
    engine = _get_engine(session_id)
    if request.count <= 0:
        raise HTTPException(status_code=400, detail="count must be positive")
    success, message = engine.give_item(
        request.source_id,
        request.target_id,
        request.item_id,
        count=request.count,
    )
    summary = engine._get_state_summary()
    return DeterministicActionResponse(
        session_id=session_id,
        success=success,
        message=message,
        state_summary=summary,
        details={
            "source": request.source_id,
            "target": request.target_id,
            "item": request.item_id,
            "count": request.count,
        },
        action_summary=engine.state_summary.build_action_summary(message),
    )


@router.get("/session/{session_id}/state")
async def get_state(session_id: str):
    """Get a detailed game state for debugging."""
    engine = _get_engine(session_id)
    return {
        "state": engine.state_manager.state.to_dict(),
        "history": engine.state_manager.state.narrative_history[-5:]
    }
