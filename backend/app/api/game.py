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
from app.core.conditions import ConditionEvaluator
from app.models.wardrobe import ClothingState

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
    method: str | None = None  # Travel method for zone travel
    entry_location_id: str | None = None  # Specific entry location for zone travel
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


class ClothingPutOnRequest(BaseModel):
    character_id: str = "player"
    clothing_id: str
    state: ClothingState | None = None


class ClothingTakeOffRequest(BaseModel):
    character_id: str = "player"
    clothing_id: str


class ClothingStateRequest(BaseModel):
    character_id: str = "player"
    clothing_id: str
    state: ClothingState


class OutfitPutOnRequest(BaseModel):
    character_id: str = "player"
    outfit_id: str


class OutfitTakeOffRequest(BaseModel):
    character_id: str = "player"
    outfit_id: str


def _get_engine(session_id: str) -> GameEngine:
    engine = game_sessions.get(session_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Session not found")
    return engine


def _describe_character(engine: GameEngine, char_id: str) -> str:
    if char_id == "player":
        return "You"
    character = engine.characters_map.get(char_id)
    if character and getattr(character, "name", None):
        return character.name
    return char_id


def _describe_item(engine: GameEngine, item_id: str) -> str:
    item_def = (
        engine.inventory.item_defs.get(item_id)
        or engine.inventory.clothing_defs.get(item_id)
        or engine.inventory.outfit_defs.get(item_id)
    )
    if item_def and getattr(item_def, "name", None):
        return item_def.name
    return item_id.replace("_", " ")


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
            initial_choices = engine._generate_choices(engine.get_current_node(), [])

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
        # Use direct zone travel method with parameters
        success = engine.movement.travel_to_zone(
            zone_id=request.zone_id,
            method=request.method,
            entry_location_id=request.entry_location_id,
            with_characters=request.companions or []
        )
        summary = engine._get_state_summary()
        if success:
            zone = engine.zones_map.get(request.zone_id)
            zone_name = zone.name if zone else request.zone_id
            message = f"You travel to {zone_name}."
        else:
            message = "You cannot travel there right now."
        details = {"zone_id": request.zone_id, "method": request.method, "entry_location_id": request.entry_location_id}
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


@router.post("/clothing/{session_id}/put-on")
async def deterministic_clothing_put_on(session_id: str, request: ClothingPutOnRequest) -> DeterministicActionResponse:
    engine = _get_engine(session_id)
    state_value = request.state.value if isinstance(request.state, ClothingState) else request.state
    apply_state = state_value or ClothingState.INTACT.value
    success = engine.clothing.put_on_clothing(request.character_id, request.clothing_id, apply_state)
    clothing_name = _describe_item(engine, request.clothing_id)
    character_label = _describe_character(engine, request.character_id)
    is_player = request.character_id == "player"
    if success:
        message = f"{'You' if is_player else character_label} put{'s' if not is_player else ''} on {clothing_name}."
    else:
        message = f"Could not put on {clothing_name}."
    summary = engine._get_state_summary()
    return DeterministicActionResponse(
        session_id=session_id,
        success=success,
        message=message,
        state_summary=summary,
        details={
            "character": request.character_id,
            "clothing": request.clothing_id,
            "state": apply_state,
        },
        action_summary=engine.state_summary.build_action_summary(message),
    )


@router.post("/clothing/{session_id}/take-off")
async def deterministic_clothing_take_off(session_id: str, request: ClothingTakeOffRequest) -> DeterministicActionResponse:
    engine = _get_engine(session_id)
    success = engine.clothing.take_off_clothing(request.character_id, request.clothing_id)
    clothing_name = _describe_item(engine, request.clothing_id)
    character_label = _describe_character(engine, request.character_id)
    is_player = request.character_id == "player"
    if success:
        message = f"{'You' if is_player else character_label} take{'s' if not is_player else ''} off {clothing_name}."
    else:
        message = f"Could not remove {clothing_name}."
    summary = engine._get_state_summary()
    return DeterministicActionResponse(
        session_id=session_id,
        success=success,
        message=message,
        state_summary=summary,
        details={
            "character": request.character_id,
            "clothing": request.clothing_id,
        },
        action_summary=engine.state_summary.build_action_summary(message),
    )


@router.post("/clothing/{session_id}/state")
async def deterministic_clothing_state(session_id: str, request: ClothingStateRequest) -> DeterministicActionResponse:
    engine = _get_engine(session_id)
    state_value = request.state.value if isinstance(request.state, ClothingState) else str(request.state)
    success = engine.clothing.set_clothing_state(request.character_id, request.clothing_id, state_value)
    clothing_name = _describe_item(engine, request.clothing_id)
    character_label = _describe_character(engine, request.character_id)
    is_player = request.character_id == "player"
    if success:
        message = f"{'You' if is_player else character_label} adjust{'s' if not is_player else ''} {clothing_name} to {state_value}."
    else:
        message = f"Could not adjust {clothing_name}."
    summary = engine._get_state_summary()
    return DeterministicActionResponse(
        session_id=session_id,
        success=success,
        message=message,
        state_summary=summary,
        details={
            "character": request.character_id,
            "clothing": request.clothing_id,
            "state": state_value,
        },
        action_summary=engine.state_summary.build_action_summary(message),
    )


@router.post("/outfits/{session_id}/put-on")
async def deterministic_outfit_put_on(session_id: str, request: OutfitPutOnRequest) -> DeterministicActionResponse:
    engine = _get_engine(session_id)
    success = engine.clothing.put_on_outfit(request.character_id, request.outfit_id)
    outfit_name = _describe_item(engine, request.outfit_id)
    character_label = _describe_character(engine, request.character_id)
    is_player = request.character_id == "player"
    if success:
        message = f"{'You' if is_player else character_label} change{'s' if not is_player else ''} into {outfit_name}."
    else:
        message = f"Could not change into {outfit_name}."
    summary = engine._get_state_summary()
    return DeterministicActionResponse(
        session_id=session_id,
        success=success,
        message=message,
        state_summary=summary,
        details={
            "character": request.character_id,
            "outfit": request.outfit_id,
        },
        action_summary=engine.state_summary.build_action_summary(message),
    )


@router.post("/outfits/{session_id}/take-off")
async def deterministic_outfit_take_off(session_id: str, request: OutfitTakeOffRequest) -> DeterministicActionResponse:
    engine = _get_engine(session_id)
    success = engine.clothing.take_off_outfit(request.character_id, request.outfit_id)
    outfit_name = _describe_item(engine, request.outfit_id)
    character_label = _describe_character(engine, request.character_id)
    is_player = request.character_id == "player"
    if success:
        message = f"{'You' if is_player else character_label} remove{'s' if not is_player else ''} {outfit_name}."
    else:
        message = f"Could not remove {outfit_name}."
    summary = engine._get_state_summary()
    return DeterministicActionResponse(
        session_id=session_id,
        success=success,
        message=message,
        state_summary=summary,
        details={
            "character": request.character_id,
            "outfit": request.outfit_id,
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


@router.get("/session/{session_id}/characters")
async def get_characters_list(session_id: str):
    """
    Get list of all characters for the notebook sidebar.
    Returns player info and all NPCs with their presence status.
    """
    engine = _get_engine(session_id)
    state = engine.state_manager.state

    # Get player info
    player_char = engine.characters_map.get("player")
    player_info = {
        "id": "player",
        "name": player_char.name if player_char else "You",
    }

    # Get all NPCs with presence status
    characters_list = []
    for char_def in engine.game_def.characters:
        if char_def.id == "player":
            continue
        characters_list.append({
            "id": char_def.id,
            "name": char_def.name,
            "present": char_def.id in state.present_chars,
            "location": state.location_current if char_def.id in state.present_chars else None,
        })

    return {
        "player": player_info,
        "characters": characters_list,
    }


@router.get("/session/{session_id}/character/{character_id}")
async def get_character_full(session_id: str, character_id: str):
    """
    Get full character data including personality, gates, current state, and filtered memories.
    For player: returns all memories.
    For NPCs: returns only memories tagged with that character (last 5).
    """
    engine = _get_engine(session_id)
    state = engine.state_manager.state

    # Get character definition
    char_def = engine.characters_map.get(character_id)
    if not char_def:
        raise HTTPException(status_code=404, detail=f"Character '{character_id}' not found")

    # Evaluate gates if they exist
    evaluator = ConditionEvaluator(state, rng_seed=engine.get_turn_seed())
    evaluated_gates = []
    if hasattr(char_def, 'gates') and char_def.gates:
        for gate in char_def.gates:
            # Evaluate the gate condition
            allow = False
            condition_str = None
            if gate.when_all:
                allow = evaluator.evaluate_all(gate.when_all)
                condition_str = " and ".join(gate.when_all)
            elif gate.when_any:
                allow = evaluator.evaluate_any(gate.when_any)
                condition_str = " or ".join(gate.when_any)
            elif gate.when:
                allow = evaluator.evaluate(gate.when)
                condition_str = gate.when
            else:
                # No condition means always allow
                allow = True
                condition_str = "always"

            evaluated_gates.append({
                "id": gate.id,
                "allow": allow,
                "condition": condition_str,
                "acceptance": gate.acceptance,
                "refusal": gate.refusal,
            })

    # Filter memories for this character
    character_memories = []
    if character_id == "player":
        # Player gets ALL memories
        for memory in state.memory_log:
            if isinstance(memory, dict):
                character_memories.append(memory)
            elif isinstance(memory, str):
                # Legacy format - convert
                character_memories.append({
                    "text": memory,
                    "characters": [],
                    "day": state.day,
                })
    else:
        # NPCs get only memories they're tagged in
        for memory in state.memory_log:
            if isinstance(memory, dict) and character_id in memory.get("characters", []):
                character_memories.append(memory)
            # Skip legacy string format for NPCs (no character info)

    # Keep last 5 memories
    character_memories = character_memories[-5:]

    # Get current state from summary
    summary = engine._get_state_summary()
    summary_meters = summary.get("meters", {})
    summary_modifiers = summary.get("modifiers", {})

    # Get inventory and separate clothing from regular items
    # state.inventory is dict[str, dict[str, int]] where first key is owner_id
    full_inventory = state.inventory.get(character_id, {})

    # Build set of clothing item IDs for filtering
    # Include items from both global wardrobe AND character's personal wardrobe
    clothing_item_ids = set()

    # Add global wardrobe items
    if engine.game_def.wardrobe and engine.game_def.wardrobe.items:
        clothing_item_ids.update(item.id for item in engine.game_def.wardrobe.items)

    # Add character's personal wardrobe items
    if char_def.wardrobe and char_def.wardrobe.items:
        clothing_item_ids.update(item.id for item in char_def.wardrobe.items)

    # Split inventory into regular items vs clothing items
    inventory = {}
    wardrobe_items = {}
    for item_id, count in full_inventory.items():
        if item_id in clothing_item_ids:
            wardrobe_items[item_id] = count
        else:
            inventory[item_id] = count

    # Build item details (inventory items + clothing items)
    item_details = {}

    # Add regular inventory item details
    for item_id in inventory.keys():
        if item_def := engine.inventory.item_defs.get(item_id):
            item_details[item_id] = item_def.model_dump()

    # Add ALL clothing item details (not just owned ones)
    # This allows UI to show missing items in outfits
    # Check both global and character-level wardrobes
    if engine.game_def.wardrobe and engine.game_def.wardrobe.items:
        for clothing_item in engine.game_def.wardrobe.items:
            item_details[clothing_item.id] = {
                "id": clothing_item.id,
                "name": clothing_item.name,
                "description": clothing_item.description if hasattr(clothing_item, 'description') else None,
                "icon": "👕",  # Default icon for clothing
                "stackable": False,
                "value": clothing_item.value if hasattr(clothing_item, 'value') else 0,
            }

    if char_def.wardrobe and char_def.wardrobe.items:
        for clothing_item in char_def.wardrobe.items:
            item_details[clothing_item.id] = {
                "id": clothing_item.id,
                "name": clothing_item.name,
                "description": clothing_item.description if hasattr(clothing_item, 'description') else None,
                "icon": "👕",  # Default icon for clothing
                "stackable": False,
                "value": clothing_item.value if hasattr(clothing_item, 'value') else 0,
            }

    # Build outfit details with ownership status
    unlocked_outfit_ids = state.unlocked_outfits.get(character_id, [])
    outfits_data = []

    # Check both global and character-level outfits
    outfits_to_check = []
    if engine.game_def.wardrobe and engine.game_def.wardrobe.outfits:
        outfits_to_check.extend(engine.game_def.wardrobe.outfits)
    if char_def.wardrobe and char_def.wardrobe.outfits:
        outfits_to_check.extend(char_def.wardrobe.outfits)

    for outfit in outfits_to_check:
        if outfit.id in unlocked_outfit_ids:
            # Determine which items character owns vs missing
            owned_items = []
            missing_items = []
            for item_id in outfit.items:
                if item_id in wardrobe_items:
                    owned_items.append(item_id)
                else:
                    missing_items.append(item_id)

            outfits_data.append({
                "id": outfit.id,
                "name": outfit.name,
                "description": outfit.description if hasattr(outfit, 'description') else None,
                "items": outfit.items,  # All items in outfit
                "owned_items": owned_items,  # Items character has
                "missing_items": missing_items,  # Items character doesn't have
                "grant_items": outfit.grant_items if hasattr(outfit, 'grant_items') else True,
            })

    # Build response
    response = {
        "id": char_def.id,
        "name": char_def.name,
        "age": char_def.age,
        "gender": char_def.gender,
        "pronouns": char_def.pronouns,
        "personality": char_def.personality if hasattr(char_def, 'personality') else None,
        "appearance": char_def.appearance if hasattr(char_def, 'appearance') else None,
        "dialogue_style": char_def.dialogue_style if hasattr(char_def, 'dialogue_style') else None,
        "gates": evaluated_gates,
        "memories": character_memories,
        # Current state
        "meters": summary_meters.get(character_id, {}),
        "modifiers": summary_modifiers.get(character_id, []),
        "attire": engine.clothing.get_character_appearance(character_id),
        "wardrobe_state": state.clothing_states.get(character_id),
        "inventory": inventory,
        "wardrobe": wardrobe_items,  # Individual clothing items owned
        "outfits": outfits_data,  # Unlocked outfits with ownership status
        "item_details": item_details,  # Item definitions for both inventory and wardrobe
        "present": character_id in state.present_chars,
        "location": state.location_current if character_id in state.present_chars else None,
    }

    return response


@router.get("/session/{session_id}/story-events")
async def get_story_events(session_id: str):
    """
    Get general story events (memories with no character tags).
    These are atmosphere, world events, etc. that aren't tied to specific characters.
    """
    engine = _get_engine(session_id)
    state = engine.state_manager.state

    # Filter for memories with empty character tags
    general_memories = []
    for memory in state.memory_log:
        if isinstance(memory, dict):
            characters = memory.get("characters", [])
            if len(characters) == 0:
                general_memories.append(memory)
        # Skip legacy string format (no way to know if it's general or character-specific)

    return {
        "memories": general_memories,
    }
