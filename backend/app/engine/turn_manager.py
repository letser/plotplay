"""Turn orchestration for PlotPlay sessions."""

from __future__ import annotations

import json
from typing import Any, TYPE_CHECKING

from app.models.effects import InventoryChangeEffect
from app.models.nodes import NodeType

if TYPE_CHECKING:
    from app.core.game_engine import GameEngine


class TurnManager:
    """Coordinates a single turn using the legacy GameEngine helpers."""

    def __init__(self, engine: "GameEngine"):
        self.engine = engine

    async def process_action(
        self,
        action_type: str,
        action_text: str | None = None,
        target: str | None = None,
        choice_id: str | None = None,
        item_id: str | None = None,
    ) -> dict[str, Any]:
        engine = self.engine

        engine.logger.info("--- Turn Start ---")
        engine.turn_meter_deltas = {}
        state = engine.state_manager.state
        current_node = engine._get_current_node()

        if current_node.type == NodeType.ENDING:
            engine.logger.warning("Attempted to process action in an ENDING node. Halting turn.")
            return {
                "narrative": "The story has concluded.",
                "choices": [],
                "current_state": engine._get_state_summary(),
            }

        if current_node.characters_present:
            state.present_chars = [
                char for char in current_node.characters_present if char in engine.characters_map
            ]
            engine.logger.info(
                f"Set present characters from node '{current_node.id}': {state.present_chars}"
            )

        player_action_str = engine._format_player_action(action_type, action_text, target, choice_id, item_id)
        engine.logger.info(f"Player Action: {player_action_str}")

        movement = engine.movement
        if choice_id and (choice_id.startswith("move_") or choice_id.startswith("travel_")):
            return await movement.handle_choice(choice_id)
        if action_type == "do" and action_text and movement.is_movement_action(action_text):
            return await movement.handle_freeform(action_text)

        turn_seed = engine._get_turn_seed()

        event_result = engine.events.process_events(turn_seed)
        event_choices = list(event_result.choices)
        event_narratives = list(event_result.narratives)

        if action_type == "choice" and choice_id:
            await engine._handle_predefined_choice(choice_id, event_choices)

        engine.events.process_arcs(turn_seed)

        writer_prompt = engine.prompt_builder.build_writer_prompt(
            state,
            player_action_str,
            current_node,
            state.narrative_history,
            rng_seed=engine._get_turn_seed(),
        )
        narrative_from_ai = (await engine.ai_service.generate(writer_prompt)).content

        checker_prompt = engine.prompt_builder.build_checker_prompt(
            narrative_from_ai, player_action_str, state
        )
        checker_response = await engine.ai_service.generate(
            checker_prompt,
            model=engine.ai_service.settings.checker_model,
            system_prompt="""You are the PlotPlay Checker - a strict JSON extraction engine. 
        Extract ONLY concrete state changes and factual memories from the narrative.
        Output ONLY valid JSON. Never add commentary, explanations, or markdown formatting.
        Focus on actions that happened, not dialogue or hypotheticals.""",
            json_mode=True,
            temperature=0.1,
        )

        state_deltas = {}
        try:
            state_deltas = json.loads(checker_response.content)
            engine.logger.info(f"State Deltas Parsed: {json.dumps(state_deltas, indent=2)}")

            if "memory" in state_deltas:
                memories = state_deltas.get("memory", [])
                if isinstance(memories, list):
                    valid_memories = []
                    for memory in memories[:2]:
                        if memory and isinstance(memory, str):
                            cleaned = memory.strip()
                            if 10 < len(cleaned) < 200:
                                valid_memories.append(cleaned)
                            else:
                                engine.logger.warning(f"Skipped invalid memory: {cleaned[:50]}...")

                    state.memory_log.extend(valid_memories)
                    state.memory_log = state.memory_log[-20:]

                    if valid_memories:
                        engine.logger.info(f"Extracted memories: {valid_memories}")

        except json.JSONDecodeError:
            engine.logger.warning(
                f"Checker AI returned invalid JSON. Content: {checker_response.content}"
            )

        if action_type == "give" and item_id and target:
            if target not in state.present_chars:
                engine.logger.warning(f"Player tried to give item to '{target}' who is not present.")
            else:
                item_def = engine.inventory.item_defs.get(item_id)
                if item_def and item_def.can_give:
                    engine.apply_effects(item_def.gift_effects)
                    engine.inventory.apply_effect(
                        InventoryChangeEffect(
                            type="inventory_remove", owner="player", item=item_id, count=1
                        )
                    )
                    engine.logger.info(f"Player gave item '{item_id}' to '{target}'.")
                else:
                    engine.logger.warning(f"Player tried to give non-giftable item '{item_id}'.")

        reconciled_narrative = engine._reconcile_narrative(
            player_action_str, narrative_from_ai, state_deltas, target
        )
        engine._apply_ai_state_changes(state_deltas)
        final_narrative = "\n\n".join(event_narratives + [reconciled_narrative])
        state.narrative_history.append(final_narrative)

        if action_type == "use" and item_id:
            item_effects = engine.inventory.use_item("player", item_id)
            engine.apply_effects(item_effects)

        engine._check_and_apply_node_transitions()
        engine.modifiers.update_modifiers_for_turn(state, rng_seed=engine._get_turn_seed())
        engine._update_discoveries()

        time_info = engine.time.advance()
        engine.modifiers.tick_durations(state, time_info.minutes_passed)
        engine.time.apply_meter_dynamics(time_info)
        engine.events.decrement_cooldowns()

        final_node = engine._get_current_node()
        choices = engine._generate_choices(final_node, event_choices)
        final_state_summary = engine._get_state_summary()
        engine.logger.info(f"End of Turn State: {json.dumps(final_state_summary, indent=2)}")
        engine.logger.info("--- Turn End ---")

        return {"narrative": final_narrative, "choices": choices, "current_state": final_state_summary}
