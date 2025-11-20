"""
Turn manager for the new PlotPlay runtime engine.

This module coordinates the canonical 15-step turn pipeline defined in
docs/turn_processing_algorithm.md. Each phase delegates to specialized
services (presence, modifiers, time, events, etc.) so the manager remains
focused on sequencing and cross-step data flow.
"""

from __future__ import annotations

from random import Random
from typing import AsyncIterator
import json
import math

from app.models.effects import (
    MeterChangeEffect,
    FlagSetEffect,
    InventoryAddEffect,
    InventoryRemoveEffect,
    InventoryTakeEffect,
    InventoryDropEffect,
    InventoryGiveEffect,
    InventoryPurchaseEffect,
    InventorySellEffect,
    MoveEffect,
    MoveToEffect,
    TravelToEffect,
    ApplyModifierEffect,
    RemoveModifierEffect,
    ClothingPutOnEffect,
    ClothingTakeOffEffect,
    ClothingStateEffect,
    ClothingSlotStateEffect,
    OutfitPutOnEffect,
    OutfitTakeOffEffect,
)
from app.models.nodes import NodeType
from app.runtime.context import TurnContext
from app.runtime.services.action_formatter import ActionFormatter
from app.runtime.services.presence import PresenceService
from app.runtime.services.actions import ActionService
from app.runtime.services.events import EventPipeline
from app.runtime.types import PlayerAction


class TurnManager:
    """
    Orchestrates a single player turn, emitting streaming events when needed.
    Currently implements the initialization + preparation phases; subsequent
    phases (effects, events, AI, etc.) will be ported in follow-up steps.
    """

    def __init__(self, runtime: "SessionRuntime") -> None:
        self.runtime = runtime
        self.logger = runtime.logger
        self.action_formatter = ActionFormatter(runtime)
        self.action_service = ActionService(runtime)
        self.presence_service = PresenceService(runtime)
        self.event_pipeline = EventPipeline(runtime)
        self.time_service = getattr(runtime, "time_service", None)
        self.modifier_service = getattr(runtime, "modifier_service", None)
        self.discovery_service = getattr(runtime, "discovery_service", None)
        self.choice_builder = getattr(runtime, "choice_builder", None)
        self.state_summary = getattr(runtime, "state_summary_service", None)
        self.ai_service = getattr(runtime, "ai_service", None)
        self.trade_service = getattr(runtime, "trade_service", None)

    async def run_turn(self, action: PlayerAction) -> AsyncIterator[dict]:
        ctx = self._initialize_context()
        self.runtime.current_context = ctx
        self._validate_node(ctx)
        self._update_presence(ctx)
        self._evaluate_gates(ctx)
        ctx.time_category_resolved = self._resolve_time_category(ctx, action)

        ctx.action_summary = self.action_formatter.format(
            action_type=action.action_type,
            action_text=action.action_text,
            choice_id=action.choice_id,
            item_id=action.item_id,
        )

        yield {"type": "action_summary", "content": ctx.action_summary}

        # Execute deterministic action effects before events/AI.
        self.action_service.execute(ctx, action)

        event_result = self.event_pipeline.process_events(ctx)
        ctx.event_choices.extend(event_result.choices)
        ctx.event_narratives.extend(event_result.narratives)
        ctx.events_fired.extend(event_result.events_fired)

        if not action.skip_ai and action.action_type in {"say", "do", "choice"} and self.ai_service:
            async for chunk in self._run_ai_phase(ctx, action):
                yield chunk

        self._apply_node_transitions(ctx)
        self._update_presence(ctx)
        self._update_modifiers()
        self._update_discoveries()
        self._advance_time(ctx)
        ctx.milestones_reached.extend(self.event_pipeline.process_arcs())

        ctx.choices = self.choice_builder.build(ctx.current_node, ctx.event_choices) if self.choice_builder else []
        state_summary = self.state_summary.build() if self.state_summary else self.runtime.state_manager.state.to_dict()

        narrative_parts = ctx.event_narratives.copy()
        if ctx.ai_narrative:
            narrative_parts.append(ctx.ai_narrative)
        if not narrative_parts:
            narrative_parts.append(ctx.action_summary)
        narrative = "\n\n".join(narrative_parts).strip()
        self.runtime.state_manager.state.narrative_history.append(narrative)

        result = {
            "session_id": self.runtime.session_id,
            "narrative": narrative,
            "choices": ctx.choices,
            "state_summary": state_summary,
            "action_summary": ctx.action_summary,
            "events_fired": ctx.events_fired,
            "milestones_reached": ctx.milestones_reached,
            "time_advanced": ctx.time_advanced_minutes > 0,
            "location_changed": self.runtime.state_manager.state.current_location != ctx.starting_location,
            "rng_seed": ctx.rng_seed,
        }

        yield {"type": "complete", **result}

    # ------------------------------------------------------------------
    # Internal helpers (ported from the legacy engine)
    # ------------------------------------------------------------------

    def _initialize_context(self) -> TurnContext:
        state = self.runtime.state_manager.state
        state.turn_count += 1

        rng_seed = self.runtime.turn_seed()
        rng = Random(rng_seed)
        state.rng_seed = rng_seed

        current_node = self.runtime.index.nodes.get(state.current_node)
        if not current_node:
            raise ValueError(f"Current node '{state.current_node}' not found.")

        snapshot = state.to_dict()

        if getattr(state, "current_visit_node", None) != current_node.id:
            state.current_visit_node = current_node.id
            state.current_visit_minutes = 0

        return TurnContext(
            turn_number=state.turn_count,
            rng_seed=rng_seed,
            rng=rng,
            current_node=current_node,
            snapshot_state=snapshot,
            starting_location=state.current_location,
        )

    def _validate_node(self, ctx: TurnContext) -> None:
        if ctx.current_node.type == NodeType.ENDING:
            raise ValueError("Cannot process action in an ending node.")

    def _update_presence(self, ctx: TurnContext) -> None:
        self.presence_service.refresh()

    def _evaluate_gates(self, ctx: TurnContext) -> None:
        active_gates: dict[str, dict[str, bool]] = {}
        evaluator = self.runtime.state_manager.create_evaluator()
        for character in self.runtime.index.characters.values():
            if not character.gates:
                continue
            gate_results = {}
            for gate in character.gates:
                gate_results[gate.id] = evaluator.evaluate_object_conditions(gate)
            active_gates[character.id] = gate_results
            char_state = self.runtime.state_manager.state.characters.get(character.id)
            if char_state is not None:
                char_state.gates = {gate_id: result for gate_id, result in gate_results.items() if result}

        ctx.condition_context["gates"] = active_gates
        ctx.active_gates = active_gates

    # ------------------------------------------------------------------
    # Turn phase helpers
    # ------------------------------------------------------------------
    def _resolve_time_category(self, ctx: TurnContext, action: PlayerAction) -> str | None:
        """Resolve time category and explicit overrides for the action."""
        time_config = self.runtime.game.time
        ctx.time_explicit_minutes = None
        ctx.time_apply_visit_cap = action.action_type in {"say", "do"}

        def _default_category() -> str:
            if action.action_type in {"say", "do"}:
                return time_config.defaults.conversation
            if action.action_type == "choice":
                return time_config.defaults.choice
            if action.action_type == "use":
                return time_config.defaults.default
            return time_config.defaults.default

        if action.action_type == "choice" and action.choice_id:
            choice = next((c for c in ctx.current_node.choices or [] if c.id == action.choice_id), None)
            if not choice:
                choice = next((c for c in ctx.current_node.dynamic_choices or [] if c.id == action.choice_id), None)
            if choice:
                if getattr(choice, "time_cost", None) is not None:
                    ctx.time_explicit_minutes = int(choice.time_cost)
                    ctx.time_apply_visit_cap = False
                    return None
                if getattr(choice, "time_category", None):
                    return choice.time_category

        if ctx.current_node.time_behavior:
            behavior = ctx.current_node.time_behavior
            if action.action_type in {"say", "do"} and behavior.conversation:
                return behavior.conversation
            if action.action_type == "choice" and behavior.choice:
                ctx.time_apply_visit_cap = False
                return behavior.choice
            if behavior.default:
                return behavior.default

        return _default_category()

    def _category_to_minutes(self, category: str | None) -> int:
        categories = self.runtime.game.time.categories or {}
        if category and category in categories:
            return int(categories[category])
        fallback = self.runtime.game.time.defaults.default
        return int(categories.get(fallback, categories.get("default", 5)))

    def _advance_time(self, ctx: TurnContext) -> None:
        if not self.time_service:
            return
        minutes = self._calculate_time_minutes(ctx)
        info = self.time_service.advance_minutes(minutes)
        ctx.time_advanced_minutes += info["minutes"]
        ctx.day_advanced = ctx.day_advanced or info.get("day_advanced", False)
        ctx.slot_advanced = ctx.slot_advanced or info.get("slot_advanced", False)

        if hasattr(self.modifier_service, "tick_durations"):
            self.modifier_service.tick_durations(self.runtime.state_manager.state, minutes=info["minutes"])
        if hasattr(self.time_service, "apply_meter_dynamics"):
            self.time_service.apply_meter_dynamics(
                day_advanced=info.get("day_advanced", False),
                slot_advanced=info.get("slot_advanced", False),
            )
        if hasattr(self.event_pipeline, "decrement_cooldowns"):
            self.event_pipeline.decrement_cooldowns()

    def _calculate_time_minutes(self, ctx: TurnContext) -> int:
        minutes = ctx.time_explicit_minutes if ctx.time_explicit_minutes is not None else self._category_to_minutes(ctx.time_category_resolved)
        minutes = self._apply_time_modifiers(minutes)

        if minutes <= 0:
            return 0

        if ctx.time_apply_visit_cap:
            cap = self._get_visit_cap(ctx.current_node)
            if cap is not None:
                state = self.runtime.state_manager.state
                spent = getattr(state, "current_visit_minutes", 0)
                remaining = max(0, cap - spent)
                minutes = min(minutes, remaining)
                state.current_visit_minutes = spent + minutes

        return max(0, minutes)

    def _get_visit_cap(self, node) -> int | None:
        node_cap = getattr(getattr(node, "time_behavior", None), "cap_per_visit", None) if node else None
        cap = node_cap if node_cap is not None else getattr(self.runtime.game.time.defaults, "cap_per_visit", None)
        if cap is None or cap <= 0:
            return None
        return int(cap)

    def _apply_time_modifiers(self, minutes: int) -> int:
        if minutes <= 0 or not self.modifier_service:
            return max(0, minutes)
        state = self.runtime.state_manager.state
        total_multiplier = 1.0
        player_modifiers = getattr(state, "modifiers", {}).get("player", [])
        library = getattr(self.modifier_service, "library", {})
        for mod in player_modifiers:
            mod_def = library.get(mod.get("id"))
            if mod_def and getattr(mod_def, "time_multiplier", None):
                total_multiplier *= mod_def.time_multiplier

        total_multiplier = max(0.5, min(2.0, total_multiplier))
        return max(0, int(math.floor(minutes * total_multiplier + 0.5)))

    def _update_modifiers(self) -> None:
        if hasattr(self.modifier_service, "update_modifiers_for_turn"):
            self.modifier_service.update_modifiers_for_turn(self.runtime.state_manager.state)

    def _update_discoveries(self) -> None:
        if self.discovery_service:
            self.discovery_service.refresh()

    def _apply_node_transitions(self, ctx: TurnContext) -> None:
        state = self.runtime.state_manager.state
        node = self.runtime.index.nodes.get(state.current_node)
        if not node:
            return
        transitions = getattr(node, "transitions", None) or getattr(node, "triggers", None)
        if not transitions:
            return
        evaluator = self.runtime.state_manager.create_evaluator()
        for transition in transitions:
            if evaluator.evaluate_object_conditions(transition):
                # Apply transition effects if present
                effects = getattr(transition, "on_select", None)
                if effects:
                    self.runtime.effect_resolver.apply_effects(effects)

                to_node = getattr(transition, "to", None)
                if to_node and to_node in self.runtime.index.nodes:
                    if node.on_exit:
                        self.runtime.effect_resolver.apply_effects(node.on_exit)
                    state.current_node = to_node
                    ctx.current_node = self.runtime.index.nodes[to_node]
                    state.nodes_history.append(to_node)
                    if ctx.current_node.on_enter:
                        self.runtime.effect_resolver.apply_effects(ctx.current_node.on_enter)
                return

    async def _run_ai_phase(self, ctx: TurnContext, action: PlayerAction) -> AsyncIterator[dict]:
        """Generate narrative + checker deltas via AI service."""
        state = self.runtime.state_manager.state
        location = self.runtime.index.locations.get(state.current_location)
        location_label = location.name if location and getattr(location, "name", None) else state.current_location

        writer_prompt = (
            f"Scene location: {location_label}.\n"
            f"Player action: {ctx.action_summary}\n"
            "Write the next short narrative beat (3-5 sentences)."
        )

        chunks: list[str] = []
        try:
            async for token in self.ai_service.generate_stream(writer_prompt, temperature=0.8, max_tokens=400):
                chunks.append(token)
                yield {"type": "narrative_chunk", "content": token}
        except Exception:  # fallback to one-shot
            response = await self.ai_service.generate(writer_prompt, temperature=0.8, max_tokens=400)
            chunks.append(response.content)

        ctx.ai_narrative = "".join(chunks).strip()

        checker_prompt = (
            "You are a strict state checker. Based on the player's action and the resulting scene, "
            "produce a JSON object with keys meters, flags, inventory, clothing, movement, modifiers, discoveries. "
            "Omit keys you don't need to change. Use numeric deltas where appropriate."
        )

        try:
            checker_response = await self.ai_service.generate(
                f"{checker_prompt}\nAction: {ctx.action_summary}\nScene: {ctx.ai_narrative}",
                json_mode=True,
                temperature=0.2,
                max_tokens=300,
            )
            ctx.checker_deltas = json.loads(checker_response.content)
            self._apply_checker_deltas(ctx)
        except Exception as exc:
            self.logger.debug("Checker failed or returned invalid JSON: %s", exc)

    def _apply_checker_deltas(self, ctx: TurnContext) -> None:
        """Translate checker JSON into concrete effects."""
        deltas = ctx.checker_deltas or {}
        if not isinstance(deltas, dict):
            return

        effects: list = []
        inventory_service = getattr(self.runtime, "inventory_service", None)

        meters_payload = deltas.get("meters")
        if isinstance(meters_payload, dict):
            for char_id, changes in meters_payload.items():
                if isinstance(changes, dict):
                    # simple mapping meter -> delta
                    for meter_id, delta in changes.items():
                        effects.append(MeterChangeEffect(target=char_id, meter=meter_id, op="add", value=delta))
                elif isinstance(changes, list):
                    for change in changes:
                        if not isinstance(change, dict):
                            continue
                        meter_id = change.get("meter")
                        value = change.get("value")
                        op = change.get("operation") or "add"
                        if op not in {"add", "subtract", "set", "multiply", "divide"}:
                            op = "add"
                        if meter_id is None or value is None:
                            continue
                        effects.append(MeterChangeEffect(target=char_id, meter=meter_id, op=op, value=value))

        flags_payload = deltas.get("flags")
        if isinstance(flags_payload, list):
            for change in flags_payload:
                if not isinstance(change, dict):
                    continue
                key = change.get("key")
                value = change.get("value")
                if key is not None:
                    effects.append(FlagSetEffect(key=key, value=value))
        elif isinstance(flags_payload, dict):
            for key, value in flags_payload.items():
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
                    continue
                item_type = inventory_service.get_item_type(item_id) if inventory_service else "item"

                if op == "add":
                    owner = change.get("owner") or change.get("to")
                    if owner:
                        effects.append(InventoryAddEffect(target=owner, item_type=item_type, item=item_id, count=count))
                elif op == "remove":
                    owner = change.get("owner") or change.get("from")
                    if owner:
                        effects.append(InventoryRemoveEffect(target=owner, item_type=item_type, item=item_id, count=count))
                elif op == "take":
                    owner = change.get("owner") or change.get("to") or "player"
                    effects.append(InventoryTakeEffect(target=owner, item_type=item_type, item=item_id, count=count))
                elif op == "drop":
                    owner = change.get("owner") or change.get("from") or "player"
                    effects.append(InventoryDropEffect(target=owner, item_type=item_type, item=item_id, count=count))
                elif op == "give":
                    source = change.get("from") or change.get("owner")
                    target = change.get("to")
                    if source and target:
                        effects.append(
                            InventoryGiveEffect(
                                source=source,
                                target=target,
                                item_type=item_type,
                                item=item_id,
                                count=count,
                            )
                        )
                elif op == "purchase":
                    buyer = change.get("buyer") or "player"
                    seller = change.get("seller")
                    price = change.get("price")
                    effects.append(
                        InventoryPurchaseEffect(
                            target=buyer,
                            source=seller or self.runtime.state_manager.state.current_location,
                            item_type=item_type,
                            item=item_id,
                            count=count,
                            price=price,
                        )
                    )
                elif op == "sell":
                    seller = change.get("seller") or "player"
                    buyer = change.get("buyer") or self.runtime.state_manager.state.current_location
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

        clothing_payload = deltas.get("clothing")
        if isinstance(clothing_payload, list):
            for change in clothing_payload:
                if not isinstance(change, dict):
                    continue
                target = change.get("character") or change.get("target")
                if not target:
                    continue
                action_type = (change.get("type") or "").lower()
                slot = change.get("slot")
                item = change.get("item")
                slot_state = change.get("state")

                if action_type == "put_on" and item:
                    effects.append(ClothingPutOnEffect(target=target, item=item, condition=slot_state))
                elif action_type == "take_off" and item:
                    effects.append(ClothingTakeOffEffect(target=target, item=item))
                elif action_type == "item_state" and item and slot_state:
                    effects.append(ClothingStateEffect(target=target, item=item, condition=slot_state))
                elif slot and slot_state:
                    effects.append(ClothingSlotStateEffect(target=target, slot=slot, condition=slot_state))

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
                    method = change.get("method") or "walk"
                    if location:
                        effects.append(TravelToEffect(location=location, method=method, with_characters=companions))

        discoveries_payload = deltas.get("discoveries")
        if isinstance(discoveries_payload, dict):
            state = self.runtime.state_manager.state
            for location_id in discoveries_payload.get("locations", []) or []:
                state.discovered_locations.add(location_id)
            for zone_id in discoveries_payload.get("zones", []) or []:
                state.discovered_zones.add(zone_id)
            for action_id in discoveries_payload.get("actions", []) or []:
                if action_id not in state.unlocked_actions:
                    state.unlocked_actions.append(action_id)
            for ending_id in discoveries_payload.get("endings", []) or []:
                if ending_id not in state.unlocked_endings:
                    state.unlocked_endings.append(ending_id)

        modifiers_payload = deltas.get("modifiers")
        if isinstance(modifiers_payload, dict):
            for addition in modifiers_payload.get("add", []) or []:
                if not isinstance(addition, dict):
                    continue
                modifier_id = addition.get("modifier")
                target = addition.get("target")
                duration = addition.get("duration")
                if modifier_id and target:
                    effects.append(ApplyModifierEffect(target=target, modifier_id=modifier_id, duration=duration))
            for removal in modifiers_payload.get("remove", []) or []:
                if not isinstance(removal, dict):
                    continue
                modifier_id = removal.get("modifier")
                target = removal.get("target")
                if modifier_id and target:
                    effects.append(RemoveModifierEffect(target=target, modifier_id=modifier_id))

        # Legacy support
        if not effects:
            if meter_changes := deltas.get("meter_changes"):
                for char_id, meters in meter_changes.items():
                    for meter, value in meters.items():
                        effects.append(MeterChangeEffect(target=char_id, meter=meter, op="add", value=value))
            if flag_changes := deltas.get("flag_changes"):
                for key, value in flag_changes.items():
                    effects.append(FlagSetEffect(key=key, value=value))
            if inventory_changes := deltas.get("inventory_changes"):
                for owner_id, items in inventory_changes.items():
                    for item_id, count in items.items():
                        if count > 0:
                            effects.append(InventoryAddEffect(target=owner_id, item_type="item", item=item_id, count=abs(count)))
                        else:
                            effects.append(InventoryRemoveEffect(target=owner_id, item_type="item", item=item_id, count=abs(count)))
            if clothing_changes := deltas.get("clothing_changes"):
                for char_id, items in clothing_changes.items():
                    for item_id, state_value in items.items():
                        effects.append(ClothingStateEffect(target=char_id, item=item_id, condition=state_value))

        if effects:
            self.runtime.effect_resolver.apply_effects(effects)
