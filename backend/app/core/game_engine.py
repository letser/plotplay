"""
PlotPlay main game engine. Handles game logic and state management.
"""

from typing import Any, Literal, cast

from app.engine import (
    SessionRuntime,
    TurnManager,
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
from app.core.conditions import ConditionEvaluator
from app.models.actions import GameAction
from app.models.characters import Character
from app.models.effects import (
    AnyEffect,
    InventoryChangeEffect,
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
from app.models.game import GameDefinition
from app.models.locations import Location, LocationPrivacy
from app.models.nodes import Node, Choice, NodeType
from app.services.ai_service import AIService
from app.engine.prompt_builder import PromptBuilder


class GameEngine:
    def __init__(self, game_def: GameDefinition, session_id: str):
        self.runtime = SessionRuntime(game_def, session_id)
        self.game_def = self.runtime.game
        self.session_id = session_id
        self.logger = self.runtime.logger
        self.state_manager = self.runtime.state_manager
        self.index = self.runtime.index

        self.ai_service = AIService()

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

        self.nodes_map: dict[str, Node] = dict(self.index.nodes)
        self.actions_map: dict[str, GameAction] = dict(self.index.actions)
        self.characters_map: dict[str, Character] = dict(self.index.characters)
        self.locations_map: dict[str, Location] = dict(self.index.locations)
        self.zones_map = dict(self.index.zones)
        self.items_map = dict(self.index.items)
        self.turn_meter_deltas: dict[str, dict[str, float]] = {}

        self.turn_manager = TurnManager(self)

        self.logger.info(f"GameEngine for session {session_id} initialized.")

    @property
    def base_seed(self) -> int | None:
        return self.runtime.base_seed

    @property
    def generated_seed(self) -> int | None:
        return self.runtime.generated_seed

    async def process_action(
            self,
            action_type: str,
            action_text: str | None = None,
            target: str | None = None,
            choice_id: str | None = None,
            item_id: str | None = None,
            skip_ai: bool = False,
    ) -> dict[str, Any]:
        return await self.turn_manager.process_action(
            action_type=action_type,
            action_text=action_text,
            target=target,
            choice_id=choice_id,
            item_id=item_id,
            skip_ai=skip_ai,
        )

    async def process_action_stream(
            self,
            action_type: str,
            action_text: str | None = None,
            target: str | None = None,
            choice_id: str | None = None,
            item_id: str | None = None,
            skip_ai: bool = False,
    ):
        """Process action with streaming narrative (async generator)."""
        async for chunk in self.turn_manager.process_action_stream(
            action_type=action_type,
            action_text=action_text,
            target=target,
            choice_id=choice_id,
            item_id=item_id,
            skip_ai=skip_ai,
        ):
            yield chunk

    async def generate_opening_scene_stream(self):
        """
        Generate opening scene narrative (Writer only, no Checker).
        Fast startup - just scene-setting prose based on start node.
        Uses start node beats if available for author control.
        """
        state = self.state_manager.state
        start_node = self._get_current_node()

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
            final_state = self._get_state_summary()

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

    def _update_discoveries(self):
        """Checks for and applies new location discoveries."""
        self.discovery.refresh()

    async def _handle_movement_choice(self, choice_id: str) -> dict[str, Any]:
        """Compatibility wrapper around the movement service."""
        return await self.movement.handle_choice(choice_id)

    async def _handle_movement(self, action_text: str) -> dict[str, Any]:
        """Compatibility wrapper around freeform movement handling."""
        return await self.movement.handle_freeform(action_text)

    def _is_movement_action(self, action_text: str) -> bool:
        return self.movement.is_movement_action(action_text)

    def _advance_time(self, minutes: int | None = None) -> dict[str, bool]:
        """Compatibility wrapper for legacy callers; prefer TimeService.advance."""
        info = self.time.advance(minutes)
        return {
            "day_advanced": info.day_advanced,
            "slot_advanced": info.slot_advanced,
            "minutes_passed": info.minutes_passed,
        }


    def _update_npc_presence(self):
        """
        Updates NPC presence based on schedules. Adds NPCs scheduled to be in the
        current location. This logic assumes schedules determine appearance, but will
        not remove characters who arrived by other means (e.g., following the player).
        """
        self.presence.refresh()

    def _reconcile_narrative(self, player_action: str, ai_narrative: str, deltas: dict,
                             target_char_id: str | None) -> str:
        return self.narrative.reconcile(player_action, ai_narrative, deltas, target_char_id)

    def _apply_ai_state_changes(self, deltas: dict):
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
                        legacy = InventoryChangeEffect(type="inventory_add", owner=owner, item=item_id, count=count)
                        effects.append(legacy)
                    case "remove":
                        owner = change.get("owner") or change.get("from")
                        if not owner:
                            continue
                        legacy = InventoryChangeEffect(type="inventory_remove", owner=owner, item=item_id, count=count)
                        effects.append(legacy)
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
                effect_type = cast(
                    Literal["inventory_add", "inventory_remove"],
                    "inventory_add" if items.get(list(items.keys())[0], 0) > 0 else "inventory_remove",
                )
                for item_id, count in items.items():
                    effect = InventoryChangeEffect(type=effect_type, owner=owner_id, item=item_id, count=abs(count))
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

    def _format_player_action(self, action_type, action_text, target, choice_id, item_id) -> str:
        return self.action_formatter.format(action_type, action_text, target, choice_id, item_id)

    def _check_and_apply_node_transitions(self):
        self.nodes.apply_transitions()

    async def _handle_predefined_choice(self, choice_id: str, event_choices: list[Choice]):
        # Check node and event choices
        handled = await self.nodes.handle_predefined_choice(choice_id, event_choices)
        if handled:
            return

    def apply_effects(self, effects: list[AnyEffect]):
        self.effect_resolver.apply_effects(effects)

    def _generate_choices(self, node: Node, event_choices: list[Choice]) -> list[dict[str, Any]]:
        return self.choices.build(node, event_choices)

    def _get_state_summary(self) -> dict[str, Any]:
        return self.state_summary.build()

    def _get_current_node(self) -> Node:
        node = self.nodes_map.get(self.state_manager.state.current_node)
        if not node: raise ValueError(f"FATAL: Current node '{self.state_manager.state.current_node}' not found.")
        return node

    def _get_character(self, char_id: str) -> Character | None:
        return self.characters_map.get(char_id)

    def _get_location(self, location_id: str) -> Location | None:
        return self.locations_map.get(location_id)

    def _process_meter_dynamics(self, time_advanced_info: dict[str, bool]):
        """Compatibility wrapper for meter decay."""
        time_info = TimeAdvance(
            day_advanced=time_advanced_info.get("day_advanced", False),
            slot_advanced=time_advanced_info.get("slot_advanced", False),
            minutes_passed=time_advanced_info.get("minutes_passed", 0),
        )
        self.time.apply_meter_dynamics(time_info)

    def _apply_meter_decay(self, decay_type: Literal["day", "slot"]):
        """Compatibility wrapper that defers to TimeService."""
        self.time.apply_meter_decay(decay_type)

    def _get_meter_def(self, char_id: str, meter_id: str) -> Any | None:
        """Helper to find the definition for a specific meter."""
        # Player meters live in the index for O(1) lookup
        if char_id == "player":
            return self.index.player_meters.get(meter_id)

        meter_def = self.index.template_meters.get(meter_id)

        char_def = self.characters_map.get(char_id)
        if not char_def or not char_def.meters:
            return meter_def

        meter_override = char_def.meters.get(meter_id)
        if meter_override is None:
            return meter_def

        if meter_def is None:
            return meter_override

        patch = meter_override.model_dump(
            exclude_unset=True,
            exclude_none=True,
            exclude_defaults=True,
        )
        return meter_def.model_copy(update=patch)

    def _get_turn_seed(self) -> int:
        """Generate a deterministic seed for the current turn."""
        return self.runtime.turn_seed()

    def _get_location_privacy(self, location_id: str | None = None) -> LocationPrivacy:
        """Get the privacy level of a location."""
        if location_id is None:
            location_id = self.state_manager.state.location_current

        location = self.locations_map.get(location_id)
        if location and hasattr(location, 'privacy'):
            return location.privacy
        return LocationPrivacy.LOW  # Default
