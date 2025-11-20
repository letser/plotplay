"""
PlotPlay main game engine. Handles game logic and state management.
"""

from dataclasses import dataclass, field
from random import Random
from typing import Any, Literal, cast
import asyncio
import json
import time

from app.engine import (
    SessionRuntime,
    EffectResolver,
    MovementService,
    TimeService,
    TimeAdvance,
    ChoiceService,
    EventPipeline,
    NodeService,
    StateSummaryService,
    ActionFormatter,
    PresenceService,
    DiscoveryService,
    NarrativeReconciler,
    InventoryService,
    ClothingService,
    ModifierService,
)
from app.engine.checker_status import CheckerStatusGenerator

from app.models.actions import Action
from app.models.characters import Character
from app.models.effects import (
    AnyEffect,
    InventoryAddEffect,
    InventoryRemoveEffect,
    InventoryTakeEffect,
    InventoryDropEffect,
    InventoryGiveEffect,
    InventoryPurchaseEffect,
    InventorySellEffect,
    MeterChangeEffect,
    FlagSetEffect,
    ClothingSlotStateEffect,
    ClothingStateEffect,
    ClothingPutOnEffect,
    ClothingTakeOffEffect,
    MoveEffect,
    MoveToEffect,
    TravelToEffect,
    ApplyModifierEffect,
    RemoveModifierEffect,
)
from app.models.game import GameDefinition, GameState
from app.models.locations import Location, LocationPrivacy
from app.models.nodes import Node, NodeChoice, NodeType
from app.services.ai_service import AIService
from app.engine.prompt_builder import PromptBuilder
from app.core.conditions import ConditionEvaluator


@dataclass
class TurnContext:
    """
    Context passed between turn phases.
    Accumulates all turn-related state changes and metadata.
    """
    # Turn identity
    turn_number: int
    rng_seed: int
    rng: Random

    # State tracking
    current_node: Node
    snapshot_state: dict  # Pre-turn snapshot for potential rollback

    # Gate evaluation
    active_gates: dict[str, dict[str, bool]] = field(default_factory=dict)  # {char_id: {gate_id: bool}}

    # Effect tracking
    meter_deltas: dict[str, dict[str, float]] = field(default_factory=dict)  # {char_id: {meter_id: delta}}
    pending_effects: list = field(default_factory=list)

    # Event tracking
    events_fired: list[str] = field(default_factory=list)
    event_choices: list[NodeChoice] = field(default_factory=list)
    event_narratives: list[str] = field(default_factory=list)

    # Arc tracking
    milestones_reached: list[str] = field(default_factory=list)
    arcs_advanced: list[str] = field(default_factory=list)

    # Time tracking
    time_category_resolved: str | None = None  # Resolved category for this action
    time_advanced_minutes: int = 0
    day_advanced: bool = False
    slot_advanced: bool = False

    # Narrative tracking
    narrative_parts: list[str] = field(default_factory=list)
    ai_narrative: str = ""

    # Final outputs
    choices: list[dict[str, Any]] = field(default_factory=list)
    action_summary: str = ""

    # Condition context (for DSL evaluation)
    condition_context: dict = field(default_factory=dict)


class GameEngine:
    def __init__(self, game_def: GameDefinition, session_id: str, ai_service: Any | None = None):
        self.runtime = SessionRuntime(game_def, session_id)
        self.game_def = self.runtime.game
        self.session_id = session_id
        self.logger = self.runtime.logger
        self.state_manager = self.runtime.state_manager
        self.index = self.runtime.index

        self.ai_service = ai_service if ai_service is not None else AIService()

        self.modifiers = ModifierService(self)
        self.effect_resolver = EffectResolver(self)
        self.clothing = ClothingService(self)
        self.inventory = InventoryService(self)
        self.movement = MovementService(self)
        self.time = TimeService(self)
        self.choices = ChoiceService(self)
        self.events = EventPipeline(self)
        self.nodes = NodeService(self)
        self.state_summary = StateSummaryService(self)
        self.action_formatter = ActionFormatter(self)
        self.presence = PresenceService(self)
        self.discovery = DiscoveryService(self)
        self.narrative = NarrativeReconciler(self)

        # PromptBuilder must be initialized AFTER clothing service
        self.prompt_builder = PromptBuilder(self.game_def, self)

        self.logger.info(f"GameEngine for session {session_id} initialized.")

    @property
    def state(self) -> GameState:
        return self.state_manager.state

    @property
    def base_seed(self) -> int | None:
        return self.runtime.base_seed

    @property
    def generated_seed(self) -> int | None:
        return self.runtime.generated_seed

    @property
    def evaluator(self) -> ConditionEvaluator:
        return self.state_manager.create_evaluator()

    async def process_action(
            self,
            action_type: str,
            action_text: str | None = None,
            target: str | None = None,
            choice_id: str | None = None,
            item_id: str | None = None,
            skip_ai: bool = False,
    ) -> dict[str, Any]:
        """Process action and return the final result (non-streaming)."""
        result = None
        async for event in self.process_action_stream(
            action_type=action_type,
            action_text=action_text,
            target=target,
            choice_id=choice_id,
            item_id=item_id,
            skip_ai=skip_ai,
        ):
            if event.get("type") == "complete":
                result = event
                break

        if not result:
            raise RuntimeError("No complete event received from turn processing")

        # Remove the 'type' field from a result
        result.pop("type", None)
        return result

    async def process_action_stream(
            self,
            action_type: str,
            action_text: str | None = None,
            target: str | None = None,
            choice_id: str | None = None,
            item_id: str | None = None,
            skip_ai: bool = False,
    ):
        """
        Unified turn processing pipeline with streaming support.

        Yields events during processing:
        - action_summary: Formatted player action
        - narrative_chunk: Streaming narrative from Writer AI (if AI enabled)
        - checker_status: Streaming Checker validation updates (if AI enabled)
        - complete: Final turn result with state summary and choices
        """
        # --- Core Setup (ALWAYS) ---
        ctx = self._initialize_turn_context()
        self._validate_current_node(ctx)
        self._update_character_presence(ctx)
        self._evaluate_character_gates(ctx)
        self._format_player_action(ctx, action_type, action_text, target, choice_id, item_id)

        # Yield action summary immediately
        yield {
            "type": "action_summary",
            "content": ctx.action_summary
        }

        # --- Action Effects (ALWAYS) ---
        await self._execute_action_effects(
            ctx, action_type, action_text, target, choice_id, item_id
        )

        # --- Events (ALWAYS) ---
        forced_transition = self._process_triggered_events(ctx)
        if forced_transition:
            # Early finalization
            state_summary = self._build_state_summary(ctx)
            result = self._build_turn_result(ctx, state_summary)
            yield {
                "type": "complete",
                **result
            }
            return

        # --- AI Generation (CONDITIONAL with STREAMING) ---
        if not skip_ai:
            # Generate narrative (WITH STREAMING)
            self.logger.info("=== Generating Narrative (Streaming) ===")
            state = self.state_manager.state

            writer_prompt = self.prompt_builder.build_writer_prompt(
                state=state,
                player_action=ctx.action_summary,
                node=ctx.current_node,
                recent_history=state.narrative_history,
                rng_seed=ctx.rng_seed,
            )

            self.logger.info("🎨 WRITER: Generating narrative...")
            self.logger.debug(f"Writer prompt: {len(writer_prompt)} chars")

            # Stream narrative chunks
            writer_start = time.time()
            accumulated_narrative = ""

            async for chunk in self.ai_service.generate_stream(writer_prompt):
                accumulated_narrative += chunk
                yield {
                    "type": "narrative_chunk",
                    "content": chunk
                }

            ctx.ai_narrative = accumulated_narrative
            writer_elapsed = time.time() - writer_start
            self.logger.info(f"⏱️  Writer completed in {writer_elapsed:.2f}s")

            # Extract state changes (WITH STATUS UPDATES)
            self.logger.info("=== Extracting State Changes (Streaming) ===")

            checker_prompt = self.prompt_builder.build_checker_prompt(
                ctx.ai_narrative,
                ctx.action_summary,
                state
            )

            self.logger.info("🔍 CHECKER: Validating state changes...")

            # Create status generator
            character_names = [char.name for char in self.game_def.characters if char.name]
            status_gen = CheckerStatusGenerator(character_names)

            # Emit initial status
            yield {
                "type": "checker_status",
                "message": status_gen.generate_message()
            }

            # Start Checker task
            checker_start = time.time()
            checker_task = asyncio.create_task(
                self.ai_service.generate(
                    checker_prompt,
                    model=self.ai_service.settings.checker_model,
                    system_prompt="""You are the PlotPlay Checker - a strict JSON extraction engine.
Extract ONLY concrete state changes and factual memories from the narrative.
Output ONLY valid JSON. Never add commentary, explanations, or markdown formatting.
Respect the provided response_contract schema exactly and keep every top-level key.
Focus on actions that happened, not dialogue or hypotheticals.""",
                    json_mode=True,
                    temperature=0.1,
                )
            )

            # Emit periodic status while waiting
            STATUS_TIMEOUT = 1.5
            while not checker_task.done():
                await asyncio.sleep(STATUS_TIMEOUT)
                if not checker_task.done():
                    yield {
                        "type": "checker_status",
                        "message": status_gen.generate_message("generic")
                    }

            # Get result
            checker_response = await checker_task
            checker_elapsed = time.time() - checker_start
            self.logger.info(f"⏱️  Checker completed in {checker_elapsed:.2f}s")

            # Parse deltas
            try:
                ctx.checker_deltas = json.loads(checker_response.content)

                # Emit context-aware completion message
                completion_contexts = []
                if ctx.checker_deltas.get("meter_changes"):
                    completion_contexts.append("meter")
                if ctx.checker_deltas.get("location_change"):
                    completion_contexts.append("location")
                if ctx.checker_deltas.get("clothing_changes"):
                    completion_contexts.append("clothing")
                if ctx.checker_deltas.get("memory"):
                    completion_contexts.append("memory")

                if completion_contexts:
                    import random
                    context_msg = status_gen.generate_message(random.choice(completion_contexts))
                else:
                    context_msg = status_gen.get_completion_message()

                yield {
                    "type": "checker_status",
                    "message": context_msg
                }

            except json.JSONDecodeError:
                self.logger.warning(f"Checker returned invalid JSON: {checker_response.content[:200]}")
                ctx.checker_deltas = {}

            # Apply AI-detected state changes
            self._apply_checker_deltas(ctx)

        # --- Post-Processing (ALWAYS) ---
        self._check_node_transitions(ctx)
        self._update_active_modifiers(ctx)
        self._update_discoveries(ctx)
        self._advance_time(ctx)
        self._process_arc_progression(ctx)
        self._build_available_choices(ctx)
        state_summary = self._build_state_summary(ctx)

        # Add final narrative to history
        all_narratives = ctx.event_narratives.copy()
        if ctx.ai_narrative:
            all_narratives.append(ctx.ai_narrative)
        final_narrative = "\n\n".join(all_narratives).strip()
        self.state_manager.state.narrative_history.append(final_narrative)

        # Build and yield final result
        result = self._build_turn_result(ctx, state_summary)
        yield {
            "type": "complete",
            **result
        }

    async def generate_opening_scene_stream(self):
        """
        Generate opening scene narrative (Writer only, no Checker).
        Fast startup - just scene-setting prose based on start node.
        Uses start node beats if available for author control.
        """
        state = self.state_manager.state
        start_node = self.get_current_node()

        # Initialize present characters from start node
        if start_node.characters_present:
            state.present_chars = [
                char for char in start_node.characters_present if char in self.characters_map
            ]

        # Build simple opening prompt
        # state.location is a LocationSnapshot with an id field
        location_id = state.location.id
        location = self.locations_map.get(location_id) if location_id else None
        location_desc = location.description if location else ""

        # Get present characters
        present_chars = [
            self.characters_map.get(char_id)
            for char_id in state.present_chars
            if char_id in self.characters_map
        ]

        # Build prompt for opening scene
        char_list = ", ".join([c.name for c in present_chars if c]) if present_chars else "nobody else"

        try:
            # Use beats from start node if available
            beats = ""
            if hasattr(start_node, 'beats') and start_node.beats:
                beats = "\n\nAuthor guidance:\n" + "\n".join(f"- {beat}" for beat in start_node.beats)

            location_name = location.name if location else 'Unknown'
            opening_prompt = f"""You are starting an interactive story. Set the opening scene.

Location: {location_name}
{location_desc}

Present: {char_list}

Write 2-3 short paragraphs establishing the scene. Focus on atmosphere and immediate surroundings.
Use second person ("you") and present tense.{beats}

Remember: This is just scene-setting. No need to describe player actions yet."""

            self.logger.info(f"Opening scene prompt: {opening_prompt[:200]}...")

            # Stream Writer output
            accumulated = ""
            async for chunk in self.ai_service.generate_stream(
                opening_prompt,
                temperature=0.8,
                max_tokens=400  # Shorter than normal turns
            ):
                accumulated += chunk
                yield {
                    "type": "narrative_chunk",
                    "content": chunk
                }

            # Generate choices from start node
            choices = self._generate_choices(start_node, [])

            # Build final state summary
            final_state = self.get_state_summary()

            self.logger.info(f"Opening scene generated: {len(accumulated)} chars")

            yield {
                "type": "complete",
                "narrative": accumulated,
                "choices": choices,
                "state_summary": final_state,
                "action_summary": "You arrive at the scene."
            }
        except Exception as e:
            self.logger.error(f"Error generating opening scene: {e}", exc_info=True)
            raise

    def update_discoveries(self):
        """Checks for and applies new location discoveries."""
        self.discovery.refresh()

    def reconcile_narrative(self, player_action: str, ai_narrative: str, deltas: dict,
                            target_char_id: str | None) -> str:
        return self.narrative.reconcile(player_action, ai_narrative, deltas, target_char_id)

    def apply_ai_state_changes(self, deltas: dict):
        if not deltas:
            return

        state = self.state_manager.state
        effects: list[AnyEffect] = []
        has_new_schema = any(
            key in deltas
            for key in ("meters", "flags", "inventory", "clothing", "movement", "discoveries", "modifiers")
        )

        # ------------------------------------------------------------------ #
        # New schema handling
        # ------------------------------------------------------------------ #
        meters_payload = deltas.get("meters")
        if isinstance(meters_payload, dict):
            for char_id, changes in meters_payload.items():
                if not isinstance(changes, list):
                    continue
                for change in changes:
                    if not isinstance(change, dict):
                        continue
                    meter_id = change.get("meter")
                    if not meter_id:
                        continue

                    op: Literal["add", "subtract", "set", "multiply", "divide"] | None = change.get("operation")
                    value = change.get("value")
                    delta = change.get("delta")

                    if delta is not None and isinstance(delta, (int, float)) and delta != 0:
                        op = "add" if delta > 0 else "subtract"
                        value = abs(delta)

                    if value is None and isinstance(delta, (int, float)):
                        value = abs(delta)
                        if delta < 0 and op is None:
                            op = "subtract"

                    if value is None:
                        continue

                    if op is None:
                        op = "add"

                    if op not in {"add", "subtract", "set", "multiply", "divide"}:
                        self.logger.warning("Checker proposed unknown meter operation '%s' for %s.%s", op, char_id, meter_id)
                        continue

                    try:
                        numeric_value = float(value)
                    except (TypeError, ValueError):
                        self.logger.warning("Checker meter change value invalid for %s.%s: %s", char_id, meter_id, value)
                        continue

                    effects.append(
                        MeterChangeEffect(
                            target=char_id,
                            meter=meter_id,
                            op=op,
                            value=numeric_value,
                        )
                    )

        flags_payload = deltas.get("flags")
        if isinstance(flags_payload, list):
            for change in flags_payload:
                if not isinstance(change, dict):
                    continue
                key = change.get("key")
                if not key:
                    continue
                value = change.get("value")
                effects.append(FlagSetEffect(key=key, value=value))

        inventory_payload = deltas.get("inventory")
        if isinstance(inventory_payload, list):
            for change in inventory_payload:
                if not isinstance(change, dict):
                    continue
                op = (change.get("op") or "").lower()
                item_id = change.get("item")
                if not op or not item_id:
                    continue
                raw_count = change.get("count", 1)
                try:
                    count = abs(int(raw_count))
                except (TypeError, ValueError):
                    self.logger.warning("Checker inventory count invalid for item '%s': %s", item_id, raw_count)
                    continue
                if count <= 0:
                    count = 1
                item_type = self.inventory.get_item_type(item_id) or "item"

                match op:
                    case "add":
                        owner = change.get("owner") or change.get("to")
                        if not owner:
                            continue
                        effects.append(
                            InventoryAddEffect(
                                target=owner,
                                item_type=item_type,
                                item=item_id,
                                count=count
                            )
                        )
                    case "remove":
                        owner = change.get("owner") or change.get("from")
                        if not owner:
                            continue
                        effects.append(
                            InventoryRemoveEffect(
                                target=owner,
                                item_type=item_type,
                                item=item_id,
                                count=count
                            )
                        )
                    case "take":
                        target = change.get("owner") or change.get("to")
                        if not target:
                            continue
                        effects.append(
                            InventoryTakeEffect(
                                target=target,
                                item_type=item_type,
                                item=item_id,
                                count=count,
                            )
                        )
                    case "drop":
                        owner = change.get("owner") or change.get("from")
                        if not owner:
                            continue
                        effects.append(
                            InventoryDropEffect(
                                target=owner,
                                item_type=item_type,
                                item=item_id,
                                count=count,
                            )
                        )
                    case "give":
                        source = change.get("from") or change.get("owner")
                        target = change.get("to")
                        if not source or not target:
                            continue
                        effects.append(
                            InventoryGiveEffect(
                                source=source,
                                target=target,
                                item_type=item_type,
                                item=item_id,
                                count=count,
                            )
                        )
                    case "purchase":
                        buyer = change.get("buyer") or change.get("owner") or "player"
                        seller = change.get("seller") or change.get("from") or self.state_manager.state.location_current
                        price = change.get("price")
                        effects.append(
                            InventoryPurchaseEffect(
                                target=buyer,
                                source=seller,
                                item_type=item_type,
                                item=item_id,
                                count=count,
                                price=price,
                            )
                        )
                    case "sell":
                        seller = change.get("seller") or change.get("owner") or "player"
                        buyer = change.get("buyer") or change.get("to") or state.location_current
                        price = change.get("price")
                        effects.append(
                            InventorySellEffect(
                                source=seller,
                                target=buyer,
                                item_type=item_type,
                                item=item_id,
                                count=count,
                                price=price,
                            )
                        )
                    case _:
                        self.logger.warning("Checker proposed unknown inventory op '%s'", op)

        clothing_payload = deltas.get("clothing")
        if isinstance(clothing_payload, list):
            for change in clothing_payload:
                if not isinstance(change, dict):
                    continue
                target = change.get("character")
                if not target:
                    continue
                action_type = (change.get("type") or "").lower()
                slot = change.get("slot")
                item = change.get("item")
                slot_state = change.get("state")

                if action_type == "put_on" and item:
                    effects.append(ClothingPutOnEffect(target=target, item=item, state=slot_state))
                elif action_type == "take_off" and item:
                    effects.append(ClothingTakeOffEffect(target=target, item=item))
                elif action_type == "item_state" and item and slot_state:
                    effects.append(ClothingStateEffect(target=target, item=item, state=slot_state))
                elif slot and slot_state:
                    effects.append(ClothingSlotStateEffect(target=target, slot=slot, state=slot_state))

        movement_payload = deltas.get("movement")
        if isinstance(movement_payload, list):
            for change in movement_payload:
                if not isinstance(change, dict):
                    continue
                move_type = (change.get("type") or "").lower()
                companions = change.get("with") or []

                if move_type == "move":
                    direction = change.get("direction")
                    if direction:
                        effects.append(MoveEffect(direction=direction, with_characters=companions))
                elif move_type == "move_to":
                    location = change.get("location")
                    if location:
                        effects.append(MoveToEffect(location=location, with_characters=companions))
                elif move_type == "travel_to":
                    location = change.get("location")
                    methods = self.game_def.movement.methods if self.game_def.movement else []
                    fallback_method = methods[0].name if methods else "walk"
                    method = change.get("method") or fallback_method
                    if location and method:
                        effects.append(TravelToEffect(location=location, method=method, with_characters=companions))

        discoveries_payload = deltas.get("discoveries")
        if isinstance(discoveries_payload, dict):
            if locations := discoveries_payload.get("locations"):
                for location_id in locations:
                    if location_id and location_id not in state.discovered_locations:
                        state.discovered_locations.append(location_id)
            if zones := discoveries_payload.get("zones"):
                for zone_id in zones:
                    if zone_id and zone_id not in state.discovered_zones:
                        state.discovered_zones.append(zone_id)
            if actions := discoveries_payload.get("actions"):
                for action_id in actions:
                    if action_id and action_id not in state.unlocked_actions:
                        state.unlocked_actions.append(action_id)
            if endings := discoveries_payload.get("endings"):
                for ending_id in endings:
                    if ending_id and ending_id not in state.unlocked_endings:
                        state.unlocked_endings.append(ending_id)
            if outfits := discoveries_payload.get("outfits"):
                if isinstance(outfits, dict):
                    for char_id, outfit_ids in outfits.items():
                        unlocked = state.unlocked_outfits.setdefault(char_id, [])
                        for outfit_id in outfit_ids or []:
                            if outfit_id and outfit_id not in unlocked:
                                unlocked.append(outfit_id)
                elif isinstance(outfits, list):
                    unlocked = state.unlocked_outfits.setdefault("player", [])
                    for outfit_id in outfits:
                        if outfit_id and outfit_id not in unlocked:
                            unlocked.append(outfit_id)
            if nodes := discoveries_payload.get("nodes"):
                for node_id in nodes:
                    if node_id and node_id not in state.visited_nodes:
                        state.visited_nodes.append(node_id)

        modifiers_payload = deltas.get("modifiers")
        if isinstance(modifiers_payload, dict):
            for addition in modifiers_payload.get("add", []) or []:
                if not isinstance(addition, dict):
                    continue
                modifier_id = addition.get("modifier")
                target = addition.get("target")
                if not modifier_id or not target:
                    continue
                duration = addition.get("duration")
                effects.append(
                    ApplyModifierEffect(
                        target=target,
                        modifier_id=modifier_id,
                        duration=duration,
                    )
                )
            for removal in modifiers_payload.get("remove", []) or []:
                if not isinstance(removal, dict):
                    continue
                modifier_id = removal.get("modifier")
                target = removal.get("target")
                if not modifier_id or not target:
                    continue
                effects.append(
                    RemoveModifierEffect(
                        target=target,
                        modifier_id=modifier_id,
                    )
                )

        if has_new_schema:
            if effects:
                self.effect_resolver.apply_effects(effects)
            return

        # ------------------------------------------------------------------ #
        # Legacy fallback for older checker payloads
        # ------------------------------------------------------------------ #
        if meter_changes := deltas.get("meter_changes"):
            for char_id, meters in meter_changes.items():
                for meter, value in meters.items():
                    self.effect_resolver.apply_meter_change(
                        MeterChangeEffect(target=char_id, meter=meter, op="add", value=value)
                    )
        if flag_changes := deltas.get("flag_changes"):
            for key, value in flag_changes.items():
                self.effect_resolver.apply_flag_set(FlagSetEffect(key=key, value=value))
        if inventory_changes := deltas.get("inventory_changes"):
            for owner_id, items in inventory_changes.items():
                for item_id, count in items.items():
                    if count > 0:
                        effect = InventoryAddEffect(target=owner_id, item_type="item", item=item_id, count=abs(count))
                    else:
                        effect = InventoryRemoveEffect(target=owner_id, item_type="item", item=item_id, count=abs(count))
                    self.inventory.apply_effect(effect)
        if clothing_changes := deltas.get("clothing_changes"):
            self.clothing.apply_ai_changes(clothing_changes)

    # ------------------------------------------------------------------ #
    # Deterministic helpers
    # ------------------------------------------------------------------ #
    def _describe_item(self, item_id: str) -> str:
        item_def = self.inventory.get_item_definition(item_id)
        if item_def and getattr(item_def, "name", None):
            return item_def.name
        return item_id

    def _describe_owner(self, owner_id: str | None) -> str:
        if not owner_id or owner_id == self.state_manager.state.location_current:
            current_location = self.locations_map.get(self.state_manager.state.location_current)
            return current_location.name if current_location else "the area"
        if owner_id == "player":
            return "you"
        if owner_id in self.characters_map:
            return self.characters_map[owner_id].name
        if owner_id in self.locations_map:
            return self.locations_map[owner_id].name
        return owner_id

    def purchase_item(
        self,
        buyer: str,
        seller: str | None,
        item_id: str,
        *,
        count: int = 1,
        price: float | None = None,
    ) -> tuple[bool, str]:
        item_type = self.inventory.get_item_type(item_id)
        if not item_type:
            return False, f"Item '{item_id}' is not available."

        state = self.state_manager.state
        buyer_inventory = state.inventory.get(buyer, {})
        before_count = buyer_inventory.get(item_id, 0)
        before_money = state.meters.get(buyer, {}).get("money") if buyer in state.meters else None

        effect = InventoryPurchaseEffect(
            target=buyer,
            source=seller or state.location_current,
            item_type=item_type,
            item=item_id,
            count=count,
            price=price,
        )
        self.effect_resolver.apply_effects([effect])

        after_count = state.inventory.get(buyer, {}).get(item_id, 0)
        after_money = state.meters.get(buyer, {}).get("money") if buyer in state.meters else None

        if after_count <= before_count:
            return False, "Purchase could not be completed."

        spent = None
        if before_money is not None and after_money is not None:
            spent = before_money - after_money

        seller_label = self._describe_owner(seller or state.location_current)
        item_label = self._describe_item(item_id)
        message = f"You purchase {count}x {item_label} from {seller_label}."
        if spent is not None:
            message += f" It costs {spent:.2f}."
        return True, message

    def sell_item(
        self,
        seller: str,
        buyer: str | None,
        item_id: str,
        *,
        count: int = 1,
        price: float | None = None,
    ) -> tuple[bool, str]:
        item_type = self.inventory.get_item_type(item_id)
        if not item_type:
            return False, f"Item '{item_id}' is not available."

        state = self.state_manager.state
        seller_inventory = state.inventory.get(seller, {})
        before_count = seller_inventory.get(item_id, 0)
        before_money = state.meters.get(seller, {}).get("money") if seller in state.meters else None

        effect = InventorySellEffect(
            source=seller,
            target=buyer or state.location_current,
            item_type=item_type,
            item=item_id,
            count=count,
            price=price,
        )
        self.effect_resolver.apply_effects([effect])

        after_count = state.inventory.get(seller, {}).get(item_id, 0)
        after_money = state.meters.get(seller, {}).get("money") if seller in state.meters else None

        if after_count >= before_count:
            return False, "Sale could not be completed."

        earned = None
        if before_money is not None and after_money is not None:
            earned = after_money - before_money

        buyer_label = self._describe_owner(buyer or state.location_current)
        item_label = self._describe_item(item_id)
        message = f"You sell {count}x {item_label} to {buyer_label}."
        if earned is not None:
            message += f" You receive {earned:.2f}."
        return True, message

    def give_item(
        self,
        source: str,
        target: str,
        item_id: str,
        *,
        count: int = 1,
    ) -> tuple[bool, str]:
        item_type = self.inventory.get_item_type(item_id)
        if not item_type:
            return False, f"Item '{item_id}' is not available."

        state = self.state_manager.state
        before_source = state.inventory.get(source, {}).get(item_id, 0)
        before_target = state.inventory.get(target, {}).get(item_id, 0)

        effect = InventoryGiveEffect(
            source=source,
            target=target,
            item_type=item_type,
            item=item_id,
            count=count,
        )
        self.effect_resolver.apply_effects([effect])

        after_source = state.inventory.get(source, {}).get(item_id, 0)
        after_target = state.inventory.get(target, {}).get(item_id, 0)

        if after_source >= before_source or after_target <= before_target:
            return False, "Gift could not be completed."

        item_label = self._describe_item(item_id)
        target_label = self._describe_owner(target)
        message = f"You hand {count}x {item_label} to {target_label}."
        return True, message

    def take_item(
        self,
        target: str,
        item_id: str,
        *,
        count: int = 1,
    ) -> tuple[bool, str]:
        item_type = self.inventory.get_item_type(item_id)
        if not item_type:
            return False, f"Item '{item_id}' is not available."

        state = self.state_manager.state
        location_id = state.location_current
        location_inventory = state.location_inventory.get(location_id, {})
        before_location = location_inventory.get(item_id, 0)
        before_target = state.inventory.get(target, {}).get(item_id, 0)

        effect = InventoryTakeEffect(
            target=target,
            item_type=item_type,
            item=item_id,
            count=count,
        )
        self.effect_resolver.apply_effects([effect])

        after_location = state.location_inventory.get(location_id, {}).get(item_id, 0)
        after_target = state.inventory.get(target, {}).get(item_id, 0)

        if before_location == after_location or after_target <= before_target:
            return False, "Nothing to take here."

        item_label = self._describe_item(item_id)
        location_label = self._describe_owner(location_id)
        message = f"You take {count}x {item_label} from {location_label}."
        return True, message

    def drop_item(
        self,
        source: str,
        item_id: str,
        *,
        count: int = 1,
    ) -> tuple[bool, str]:
        item_type = self.inventory.get_item_type(item_id)
        if not item_type:
            return False, f"Item '{item_id}' is not available."

        state = self.state_manager.state
        location_id = state.location_current
        before_source = state.inventory.get(source, {}).get(item_id, 0)
        before_location = state.location_inventory.get(location_id, {}).get(item_id, 0)

        effect = InventoryDropEffect(
            target=source,
            item_type=item_type,
            item=item_id,
            count=count,
        )
        self.effect_resolver.apply_effects([effect])

        after_source = state.inventory.get(source, {}).get(item_id, 0)
        after_location = state.location_inventory.get(location_id, {}).get(item_id, 0)

        if after_source >= before_source or after_location <= before_location:
            return False, "Drop could not be completed."

        item_label = self._describe_item(item_id)
        location_label = self._describe_owner(location_id)
        message = f"You drop {count}x {item_label} at {location_label}."
        return True, message

    def format_player_action(self, action_type, action_text, target, choice_id, item_id) -> str:
        return self.action_formatter.format(action_type, action_text, target, choice_id, item_id)

    def check_and_apply_node_transitions(self):
        self.nodes.apply_transitions()

    async def handle_predefined_choice(self, choice_id: str, event_choices: list[NodeChoice]):
        # Check node and event choices
        handled = await self.nodes.handle_predefined_choice(choice_id, event_choices)
        if handled:
            return

    def apply_effects(self, effects: list[AnyEffect]):
        self.effect_resolver.apply_effects(effects)

    def _generate_choices(self, node: Node, event_choices: list[NodeChoice]) -> list[dict[str, Any]]:
        return self.choices.build(node, event_choices)

    def get_state_summary(self) -> dict[str, Any]:
        return self.state_summary.build()

    def get_current_node(self) -> Node:
        node = self.index.nodes.get(self.state.current_node)
        if not node: raise ValueError(f"FATAL: Current node '{self.state_manager.state.current_node}' not found.")
        return node

    def _get_character(self, char_id: str) -> Character | None:
        return  self.index.characters.get(char_id)

    def _get_meter_def(self, char_id: str, meter_id: str):
        """Get meter definition for a character's meter."""
        # Check player meters
        if char_id == "player" and meter_id in self.index.player_meters:
            return self.index.player_meters[meter_id]

        # Check template meters for NPCs
        if char_id != "player" and meter_id in self.index.template_meters:
            return self.index.template_meters[meter_id]

        return None

    def get_location(self, location_id: str) -> Location | None:
        return self.index.locations.get(location_id)


    def get_turn_seed(self) -> int:
        """Generate a deterministic seed for the current turn."""
        return self.runtime.turn_seed()

    # ============================================================================
    # Turn Processing Pipeline - Clean Implementation
    # ============================================================================

    def _initialize_turn_context(self) -> TurnContext:
        """
        Initialize turn context with deterministic RNG seed and state snapshot.
        Increments turn counter and captures current node.
        """
        self.logger.info("=== Initializing Turn Context ===")

        state = self.state_manager.state
        state.turn_count += 1

        rng_seed = self.get_turn_seed()
        rng = Random(rng_seed)
        current_node = self.get_current_node()
        snapshot = state.to_dict()

        ctx = TurnContext(
            turn_number=state.turn_count,
            rng_seed=rng_seed,
            rng=rng,
            current_node=current_node,
            snapshot_state=snapshot,
        )

        self.logger.debug(f"Turn {ctx.turn_number} initialized with seed {rng_seed}")
        return ctx

    def _validate_current_node(self, ctx: TurnContext) -> None:
        """
        Validate that the current node allows action processing.
        Rejects actions if the game is in an ENDING node.
        """
        self.logger.info("=== Validating Current Node ===")

        if ctx.current_node.type == NodeType.ENDING:
            raise ValueError("Cannot process action in ENDING node")

        self.logger.debug(f"Node validation passed: {ctx.current_node.id}")

    def _update_character_presence(self, ctx: TurnContext) -> None:
        """
        Update character presence based on schedules.
        Refreshes which NPCs are present in the current location.
        """
        self.logger.info("=== Updating Character Presence ===")
        self.presence.refresh()
        self.logger.debug(f"Present characters: {self.state_manager.state.present_characters}")

    def _evaluate_character_gates(self, ctx: TurnContext) -> None:
        """
        Evaluate all character gates to determine active behaviors.
        Gates control character responses and interactions based on state.
        """
        self.logger.info("=== Evaluating Character Gates ===")

        active_gates = {}
        evaluator = self.state_manager.create_evaluator()

        for character in self.index.characters.values():
            if not character.gates:
                continue

            char_gates = {}
            for gate in character.gates:
                is_active = evaluator.evaluate_object_conditions(gate)
                char_gates[gate.id] = is_active

            active_gates[character.id] = char_gates

        ctx.active_gates = active_gates
        ctx.condition_context['gates'] = active_gates
        self.logger.debug(f"Active gates: {active_gates}")

    def _format_player_action(
        self,
        ctx: TurnContext,
        action_type: str,
        action_text: str | None,
        target: str | None,
        choice_id: str | None,
        item_id: str | None,
    ) -> None:
        """
        Format player action into human-readable summary for AI context and logs.
        Resolves references (choice IDs, character names, item names).
        """
        self.logger.info("=== Formatting Player Action ===")

        ctx.action_summary = self.action_formatter.format(
            action_type, action_text, target, choice_id, item_id
        )

        self.logger.debug(f"Action: {ctx.action_summary}")

    async def _execute_action_effects(
        self,
        ctx: TurnContext,
        action_type: str,
        action_text: str | None,
        target: str | None,
        choice_id: str | None,
        item_id: str | None,
    ) -> None:
        """
        Execute state changes associated with the chosen action.
        Handles choice effects, movement, inventory, and time category resolution.
        """
        self.logger.info("=== Executing Action Effects ===")

        # Resolve time category
        ctx.time_category_resolved = self._resolve_time_category(
            action_type, choice_id, ctx.current_node, ctx.event_choices
        )

        # Handle choice effects
        if action_type == "choice" and choice_id:
            await self.handle_predefined_choice(choice_id, ctx.event_choices)
            ctx.current_node = self.get_current_node()

        self.logger.debug(f"Action effects executed, time category: {ctx.time_category_resolved}")

    def _resolve_time_category(
        self,
        action_type: str,
        choice_id: str | None,
        node: Node,
        event_choices: list[NodeChoice],
    ) -> str:
        """Resolve the time category for an action."""
        time_config = self.game_def.time

        # Check for choice-specific overrides
        if choice_id:
            choice = None
            for c in (node.choices or []):
                if c.id == choice_id:
                    choice = c
                    break
            if not choice:
                for c in event_choices:
                    if c.id == choice_id:
                        choice = c
                        break

            if choice:
                if hasattr(choice, 'time_cost') and choice.time_cost is not None:
                    return f"explicit:{choice.time_cost}m"

                if hasattr(choice, 'time_category') and choice.time_category:
                    return choice.time_category

        # Check node-level overrides
        if node.time_behavior:
            if action_type in ["say", "do"]:
                if node.time_behavior.conversation:
                    return node.time_behavior.conversation
            elif action_type == "choice":
                if node.time_behavior.choice:
                    return node.time_behavior.choice

            if node.time_behavior.default:
                return node.time_behavior.default

        # Use global defaults
        if action_type in ["say", "do"]:
            return time_config.defaults.conversation
        elif action_type == "choice":
            return time_config.defaults.choice
        elif action_type == "move":
            return time_config.defaults.movement
        else:
            return time_config.defaults.default

    def _process_triggered_events(self, ctx: TurnContext) -> bool:
        """
        Check for and trigger events based on current state conditions.
        Returns True if a forced node transition occurred (early exit).
        """
        self.logger.info("=== Processing Triggered Events ===")

        event_result = self.events.process_events(ctx.rng_seed)

        ctx.event_choices.extend(event_result.choices)
        ctx.event_narratives.extend(event_result.narratives)

        forced_transition = False
        self.logger.debug(f"Events processed: {len(event_result.choices)} choices, {len(event_result.narratives)} narratives")

        return forced_transition

    def _apply_checker_deltas(self, ctx: TurnContext) -> None:
        """
        Apply state changes extracted by Checker AI from narrative.
        Handles meters, flags, inventory, clothing, movement, modifiers, and memories.
        """
        self.logger.info("=== Applying Checker Deltas ===")

        if not hasattr(ctx, 'checker_deltas'):
            ctx.checker_deltas = {}

        self.apply_ai_state_changes(ctx.checker_deltas)

        if "memory" in ctx.checker_deltas:
            self._extract_memories(ctx)

        self.logger.debug("Checker deltas applied")

    def _extract_memories(self, ctx: TurnContext) -> None:
        """Extract and validate memories from Checker deltas."""
        state = self.state_manager.state
        memories = ctx.checker_deltas.get("memory", [])

        if not isinstance(memories, list):
            return

        valid_memories = []
        for memory in memories[:2]:
            if isinstance(memory, dict) and "text" in memory:
                cleaned_text = memory["text"].strip()
                if 10 < len(cleaned_text) < 200:
                    characters = memory.get("characters", [])

                    valid_chars = [
                        char_id for char_id in characters
                        if char_id == "player" or char_id in self.characters_map
                    ]

                    if len(characters) > 0 and len(valid_chars) == 0:
                        self.logger.warning(
                            f"Memory has invalid character IDs: {characters}. "
                            f"Accepting with empty character list."
                        )

                    valid_memories.append({
                        "text": cleaned_text,
                        "characters": valid_chars,
                        "day": state.time.day,
                    })
                else:
                    self.logger.warning(f"Skipped invalid memory text length: {cleaned_text[:50]}...")
            else:
                self.logger.warning(f"Skipped invalid memory format: {memory}")

        state.memory_log.extend(valid_memories)
        state.memory_log = state.memory_log[-20:]

        if valid_memories:
            self.logger.debug(f"Extracted {len(valid_memories)} memories")

    def _check_node_transitions(self, ctx: TurnContext) -> None:
        """
        Check for and apply automatic node transitions based on conditions.
        Updates current node if transition occurs.
        """
        self.logger.info("=== Checking Node Transitions ===")

        self.nodes.check_auto_transitions()
        ctx.current_node = self.get_current_node()

        self.logger.debug(f"Node transitions complete, current node: {ctx.current_node.id}")

    def _update_active_modifiers(self, ctx: TurnContext) -> None:
        """
        Update time-based and condition-based modifiers.
        Activates/deactivates modifiers based on when conditions.
        """
        self.logger.info("=== Updating Active Modifiers ===")

        self.modifiers.update_modifiers_for_turn(
            self.state_manager.state,
            rng_seed=ctx.rng_seed
        )

        self.logger.debug("Modifiers auto-activation checked")

    def _update_discoveries(self, ctx: TurnContext) -> None:
        """
        Mark zones, locations, and other content as discovered based on conditions.
        Unlocks new areas, actions, and endings.
        """
        self.logger.info("=== Updating Discoveries ===")

        self.discovery.update_discoveries(self.state_manager.state)

        self.logger.debug("Discoveries updated")

    def _advance_time(self, ctx: TurnContext) -> None:
        """
        Progress game time and apply time-based state changes.
        Handles day/slot rollover, modifier duration ticking, meter decay, and event cooldowns.
        """
        self.logger.info("=== Advancing Time ===")

        time_cost_minutes = self._resolve_time_cost_minutes(
            ctx.time_category_resolved,
            ctx.current_node,
        )

        self.logger.debug(f"Time cost resolved: {time_cost_minutes} minutes (category: {ctx.time_category_resolved})")

        time_info = self.time.advance(minutes=time_cost_minutes)

        ctx.time_advanced_minutes = time_info.minutes_passed
        ctx.day_advanced = time_info.day_advanced
        ctx.slot_advanced = time_info.slot_advanced

        if hasattr(self.modifiers, 'tick_durations'):
            self.modifiers.tick_durations(
                self.state_manager.state,
                minutes=time_info.minutes_passed
            )
        else:
            self.logger.warning("ModifierService.tick_durations() not implemented yet")

        self.time.apply_meter_dynamics(time_info)

        if hasattr(self.events, 'decrement_cooldowns'):
            self.events.decrement_cooldowns()
        else:
            self.logger.debug("Event cooldown decrement not implemented yet")

        self.logger.info(
            f"Time advanced by {time_info.minutes_passed} minutes "
            f"(day: {time_info.day_advanced}, slot: {time_info.slot_advanced})"
        )

    def _resolve_time_cost_minutes(
        self,
        category: str,
        node: Node,
    ) -> int:
        """Convert time category to actual minutes."""
        time_config = self.game_def.time
        state = self.state_manager.state

        if category and category.startswith("explicit:"):
            minutes_str = category.replace("explicit:", "").replace("m", "")
            return int(minutes_str)

        if category and category in time_config.categories:
            minutes = time_config.categories[category]
        else:
            default_category = time_config.defaults.default
            minutes = time_config.categories.get(default_category, 5)
            self.logger.warning(
                f"Unknown time category '{category}', using default: {minutes}m"
            )

        # Visit cap handling (placeholder for future enhancement)
        if node and hasattr(node, 'time_behavior') and node.time_behavior:
            cap = node.time_behavior.cap_per_visit
        else:
            cap = time_config.defaults.cap_per_visit

        return minutes

    def _process_arc_progression(self, ctx: TurnContext) -> None:
        """
        Check for and advance story arcs based on milestone conditions.
        Applies arc stage effects and tracks progression history.
        """
        self.logger.info("=== Processing Arc Progression ===")

        self.events.process_arcs(ctx.rng_seed)

        self.logger.debug("Arcs processed")

    def _build_available_choices(self, ctx: TurnContext) -> None:
        """
        Generate the list of choices available to the player for the next turn.
        Includes node choices, event choices, movement options, and unlocked actions.
        """
        self.logger.info("=== Building Available Choices ===")

        ctx.choices = self.choices.build_choices(
            ctx.current_node,
            ctx.event_choices
        )

        self.logger.debug(f"Built {len(ctx.choices)} choices")

    def _build_state_summary(self, ctx: TurnContext) -> dict:
        """
        Create a snapshot of game state for API response and frontend display.
        Includes meters, flags, inventory, clothing, time, and present characters.
        """
        self.logger.info("=== Building State Summary ===")

        state_summary = self.get_state_summary()

        self.logger.debug("State summary built")

        return state_summary

    def _build_turn_result(self, ctx: TurnContext, state_summary: dict) -> dict[str, Any]:
        """
        Build final turn result for API response.
        Combines all narratives and collects turn metadata.
        """
        all_narratives = ctx.event_narratives.copy()
        if ctx.ai_narrative:
            all_narratives.append(ctx.ai_narrative)

        final_narrative = "\n\n".join(all_narratives).strip()

        return {
            "narrative": final_narrative,
            "choices": ctx.choices,
            "state_summary": state_summary,
            "action_summary": ctx.action_summary,
            "events_fired": ctx.events_fired,
            "milestones_reached": ctx.milestones_reached,
        }

    # ============================================================================
    # Helper Methods
    # ============================================================================

    def _get_location_privacy(self, location_id: str | None = None) -> LocationPrivacy:
        """Get the privacy level of a location."""
        if location_id is None:
            location_id = self.state_manager.state.location_current

        location = self.locations_map.get(location_id)
        if location and hasattr(location, 'privacy'):
            return location.privacy
        return LocationPrivacy.LOW  # Default
