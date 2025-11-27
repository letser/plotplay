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
    action_type: Literal["say", "do", "choice", "use", "give", "move", "goto", "travel", "shop_buy", "shop_sell", "inventory", "clothing"]
    action_text: str | None = None
    target: str | None = None
    choice_id: str | None = None
    item_id: str | None = None
    # Movement fields
    direction: str | None = None
    location: str | None = None
    with_characters: list[str] | None = None
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
        # Tests use MockAIService (see tests/conftest.py)
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
            # Tests use MockAIService (see tests/conftest.py)
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
                direction=action.direction,
                location=action.location,
                with_characters=action.with_characters,
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
                    direction=action.direction,
                    location=action.location,
                    with_characters=action.with_characters,
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


# Helper endpoint response models
class CharacterListItem(BaseModel):
    id: str
    name: str
    present: bool
    location: str | None = None


class CharactersListResponse(BaseModel):
    player: dict[str, str]
    characters: list[CharacterListItem]


class CharacterMemory(BaseModel):
    text: str
    characters: list[str]
    day: int


class StoryEventsResponse(BaseModel):
    memories: list[CharacterMemory]


@router.get("/session/{session_id}/characters")
async def get_characters_list(session_id: str) -> CharactersListResponse:
    """Get list of all characters with basic info for Character Notebook sidebar."""
    engine = _get_engine(session_id)
    state = engine.runtime.state_manager.state
    game = engine.runtime.game

    # Get player info
    player_def = game.player
    player_state = state.characters.get("player")
    player_info = {
        "id": "player",
        "name": player_state.name if player_state else (player_def.name if player_def else "Player")
    }

    # Get all character info
    characters = []
    for char_id, char_def in (game.characters or {}).items():
        char_state = state.characters.get(char_id)
        characters.append(CharacterListItem(
            id=char_id,
            name=char_state.name if char_state else char_def.name,
            present=char_id in state.present_characters,
            location=state.current_location if char_id in state.present_characters else None
        ))

    return CharactersListResponse(player=player_info, characters=characters)


@router.get("/session/{session_id}/character/{character_id}")
async def get_character_details(session_id: str, character_id: str) -> dict[str, Any]:
    """Get detailed character profile for Character Notebook."""
    engine = _get_engine(session_id)
    state = engine.runtime.state_manager.state
    game = engine.runtime.game

    # Get character definition and state
    if character_id == "player":
        char_def = game.player
        char_state = state.characters.get("player")
    else:
        char_def = (game.characters or {}).get(character_id)
        if not char_def:
            raise HTTPException(status_code=404, detail=f"Character {character_id} not found")
        char_state = state.characters.get(character_id)

    if not char_state:
        raise HTTPException(status_code=404, detail=f"Character state for {character_id} not found")

    # Build character profile
    profile = {
        "id": character_id,
        "name": char_state.name,
        "age": getattr(char_def, "age", None),
        "gender": getattr(char_def, "gender", None),
        "pronouns": getattr(char_def, "pronouns", None),
        "personality": {
            "core_traits": getattr(char_def.personality, "core_traits", None) if hasattr(char_def, "personality") and char_def.personality else None,
            "quirks": getattr(char_def.personality, "quirks", None) if hasattr(char_def, "personality") and char_def.personality else None,
            "values": getattr(char_def.personality, "values", None) if hasattr(char_def, "personality") and char_def.personality else None,
            "fears": getattr(char_def.personality, "fears", None) if hasattr(char_def, "personality") and char_def.personality else None,
        } if hasattr(char_def, "personality") and char_def.personality else None,
        "appearance": getattr(char_def, "appearance", None),
        "dialogue_style": getattr(char_def, "dialogue_style", None),
        "gates": [
            {
                "id": gate_id,
                "allow": gate_value,
                "condition": None,  # Gates are boolean in runtime
                "acceptance": None,
                "refusal": None
            }
            for gate_id, gate_value in (char_state.gates or {}).items()
        ],
        "memories": [
            {"text": memory, "characters": [character_id], "day": state.day}
            for memory in (char_state.memory_log or [])
        ],
        "meters": {},
        "modifiers": [],
        "attire": char_state.clothing.outfit if char_state.clothing else None,
        "wardrobe_state": None,  # TODO: Extract from clothing_states if needed
        "inventory": dict(char_state.inventory.items),
        "wardrobe": {},  # TODO: Filter clothing items from inventory if needed
        "outfits": [],  # TODO: Get outfit definitions if needed
        "item_details": {},  # TODO: Get item definitions from game
        "present": character_id in state.present_characters,
        "location": state.current_location if character_id in state.present_characters else None
    }

    # Add meters (visible only)
    meter_defs = engine.runtime.index.player_meters if character_id == "player" else engine.runtime.index.template_meters
    if meter_defs:
        for meter_id, meter_def in meter_defs.items():
            if not getattr(meter_def, "visible", True):
                continue
            profile["meters"][meter_id] = {
                "value": char_state.meters.get(meter_id),
                "min": meter_def.min,
                "max": meter_def.max,
                "icon": getattr(meter_def, "icon", None),
                "visible": True
            }

    # Add modifiers
    active_mods = state.modifiers.get(character_id, [])
    profile["modifiers"] = [
        {
            "id": mod.get("id"),
            "description": None,  # TODO: Get from modifier definition
            "appearance": None
        }
        for mod in active_mods
    ]

    return profile


@router.get("/session/{session_id}/story-events")
async def get_story_events(session_id: str) -> StoryEventsResponse:
    """Get aggregated story events (character memories) for Story Events panel."""
    engine = _get_engine(session_id)
    state = engine.runtime.state_manager.state

    # Aggregate memories from all characters
    all_memories = []
    for char_id, char_state in state.characters.items():
        if not char_state.memory_log:
            continue
        for memory_text in char_state.memory_log:
            all_memories.append(CharacterMemory(
                text=memory_text,
                characters=[char_id],
                day=state.day  # All memories tagged with current day for now
            ))

    return StoryEventsResponse(memories=all_memories)
