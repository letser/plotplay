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

    async def run_turn(self, action: PlayerAction) -> AsyncIterator[dict]:
        ctx = self._initialize_context()
        self._validate_node(ctx)
        self._update_presence(ctx)
        self._evaluate_gates(ctx)
        ctx.time_category_resolved = self._resolve_time_category(action)

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

        self._advance_time(ctx)
        self._update_modifiers()
        self._update_discoveries()
        self._apply_node_transitions(ctx)

        ctx.choices = self.choice_builder.build(ctx.current_node, ctx.event_choices) if self.choice_builder else []
        state_summary = self.state_summary.build() if self.state_summary else self.runtime.state_manager.state.to_dict()

        narrative_parts = ctx.event_narratives.copy()
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

        ctx.condition_context["gates"] = active_gates

    # ------------------------------------------------------------------
    # Turn phase helpers
    # ------------------------------------------------------------------
    def _resolve_time_category(self, action: PlayerAction) -> str:
        defaults = self.runtime.game.time.defaults
        if action.action_type in {"say", "do"}:
            return getattr(defaults, "conversation", "default")
        if action.action_type == "choice":
            return getattr(defaults, "choice", "default")
        return getattr(defaults, "default", "default")

    def _category_to_minutes(self, category: str | None) -> int:
        categories = self.runtime.game.time.categories or {}
        if category and category in categories:
            return int(categories[category])
        return int(categories.get("default", 5))

    def _advance_time(self, ctx: TurnContext) -> None:
        if not self.time_service:
            return
        minutes = ctx.time_explicit_minutes or self._category_to_minutes(ctx.time_category_resolved)
        info = self.time_service.advance_minutes(minutes)
        ctx.time_advanced_minutes = info["minutes"]
        ctx.day_advanced = info["day_advanced"]
        ctx.slot_advanced = info["slot_advanced"]

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
            if evaluator.evaluate(getattr(transition, "when", None)):
                if transition.to in self.runtime.index.nodes:
                    state.current_node = transition.to
                    ctx.current_node = self.runtime.index.nodes[transition.to]
                    return
