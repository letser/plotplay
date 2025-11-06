"""Turn orchestration for PlotPlay sessions."""

from __future__ import annotations

import json
import asyncio
import random
from typing import Any, TYPE_CHECKING

from app.models.effects import InventoryChangeEffect
from app.models.nodes import NodeType
from app.engine.checker_status import CheckerStatusGenerator

if TYPE_CHECKING:
    from app.core.game_engine import GameEngine


class TurnManager:
    """Coordinates a single turn using the legacy GameEngine helpers."""
    STATUS_TIMEOUT = 1.5

    def __init__(self, engine: "GameEngine"):
        self.engine = engine

    async def process_action(
        self,
        action_type: str,
        action_text: str | None = None,
        target: str | None = None,
        choice_id: str | None = None,
        item_id: str | None = None,
        skip_ai: bool = False,
    ) -> dict[str, Any]:

        final_result = None
        async for event in self.process_action_stream(
                action_type=action_type,
                action_text=action_text,
                target=target,
                choice_id=choice_id,
                item_id=item_id,
                skip_ai=skip_ai):

            if event.get("type") == "complete":
                final_result = event["result"]

        return final_result



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
        engine = self.engine

        engine.logger.info("--- Turn Start (Streaming) ---")
        engine.turn_meter_deltas = {}
        state = engine.state_manager.state
        current_node = engine.get_current_node()

        turn_seed = engine.get_turn_seed()

        # Interrupt if the ending node is reached
        if current_node.type == NodeType.ENDING:
            engine.logger.warning("Attempted to process action in an ENDING node. Halting turn.")
            yield {
                "type": "complete",
                "narrative": "The story has concluded.",
                "choices": [],
                "state_summary": engine.get_state_summary(),
                "action_summary": None
            }
            return

        # Populate characters from node
        if current_node.characters_present:
            state.present_chars = [
                char for char in current_node.characters_present if char in engine.characters_map
            ]
            engine.logger.info(
                f"Set present characters from node '{current_node.id}': {state.present_chars}"
            )

        # Build player action text
        player_action_str = engine.format_player_action(action_type, action_text, target, choice_id, item_id)
        engine.logger.info(f"Player Action: {player_action_str}")

        # Send action summary immediately
        action_summary = engine.state_summary.build_action_summary(player_action_str)
        yield {
            "type": "action_summary",
            "content": action_summary
        }

        # Handle movement
        movement = engine.movement
        if choice_id and (choice_id.startswith("move_") or choice_id.startswith("travel_")):
            result = await movement.handle_choice(choice_id)
            yield {
                "type": "complete",
                "narrative": result.get("narrative"),
                "choices": result.get("choices"),
                "state_summary": result.get("current_state"),
                "action_summary": result.get("action_summary")
            }
            return

        # Handle freeform movement action (e.g. "go north")
        if action_type == "do" and action_text and movement.is_movement_action(action_text):
            result = await movement.handle_freeform(action_text)
            yield {
                "type": "complete",
                "narrative": result.get("narrative"),
                "choices": result.get("choices"),
                "state_summary": result.get("current_state"),
                "action_summary": result.get("action_summary")
            }
            return

        # Process events
        event_result = engine.events.process_events(turn_seed)
        event_choices = list(event_result.choices)
        event_narratives = list(event_result.narratives)

        if action_type == "choice" and choice_id:
            await engine.handle_predefined_choice(choice_id, event_choices)
            # Recapture the current node after choice effects (which may include goto)
            current_node = engine.get_current_node()
            # Update present_chars from the new node if it specifies characters
            if current_node.characters_present:
                state.present_chars = [
                    char for char in current_node.characters_present if char in engine.characters_map
                ]
                engine.logger.info(
                    f"Updated present characters after choice to node '{current_node.id}': {state.present_chars}"
                )

        # Process arcs
        engine.events.process_arcs(turn_seed)

        state_deltas = {}
        narrative_from_ai = ""
        accumulated_narrative = ""

        # Invoke Writer abd stream output
        if not skip_ai:
            import time

            writer_prompt = engine.prompt_builder.build_writer_prompt(
                state=state,
                player_action=player_action_str,
                node=current_node,
                recent_history=state.narrative_history,
                rng_seed=engine.get_turn_seed(),
            )

            engine.logger.info("🎨 WRITER: Generating narrative...")
            engine.logger.debug(f"Writer Prompt:\n{writer_prompt}")

            # Stream narrative chunks
            writer_start = time.time()
            async for chunk in engine.ai_service.generate_stream(writer_prompt):
                accumulated_narrative += chunk
                yield {
                    "type": "narrative_chunk",
                    "content": chunk
                }
            writer_elapsed = time.time() - writer_start

            narrative_from_ai = accumulated_narrative

            engine.logger.info(f"⏱️  Writer completed in {writer_elapsed:.2f}s")
            engine.logger.debug(f"Writer Response:\n{narrative_from_ai}")

            # Now run Checker with a complete narrative and emit fun status messages
            checker_prompt = engine.prompt_builder.build_checker_prompt(
                narrative_from_ai, player_action_str, state
            )

            engine.logger.info("🔍 CHECKER: Validating state changes...")
            engine.logger.debug(f"Checker Prompt:\n{checker_prompt}")

            # Create status generator
            character_names = [char.name for char in engine.game_def.characters if char.name]
            status_gen = CheckerStatusGenerator(character_names)

            # Emit initial status message
            yield {
                "type": "checker_status",
                "message": status_gen.generate_message()
            }

            # Run Checker with periodic status updates
            async def emit_periodic_status():
                """Emit status messages every 800ms while Checker runs."""
                await asyncio.sleep(self.STATUS_TIMEOUT)
                while True:
                    yield {
                        "type": "checker_status",
                        "message": status_gen.generate_message("generic")
                    }
                    await asyncio.sleep(self.STATUS_TIMEOUT)

            # Start Checker task
            checker_start = time.time()
            checker_task = asyncio.create_task(
                engine.ai_service.generate(
                    checker_prompt,
                    model=engine.ai_service.settings.checker_model,
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
            while not checker_task.done():
                await asyncio.sleep(self.STATUS_TIMEOUT)
                if not checker_task.done():
                    msg = status_gen.generate_message("generic")
                    yield {
                        "type": "checker_status",
                        "message": msg
                    }

            # Get Checker result
            checker_response = await checker_task
            checker_elapsed = time.time() - checker_start
            engine.logger.info(f"⏱️  Checker completed in {checker_elapsed:.2f}s")
            engine.logger.debug(f"Checker Response:\n{checker_response.content}")

            try:
                state_deltas = json.loads(checker_response.content)

                # Emit a context-aware completion message based on what changed
                completion_contexts = []
                if state_deltas.get("meter_changes"):
                    completion_contexts.append("meter")
                if state_deltas.get("location_change"):
                    completion_contexts.append("location")
                if state_deltas.get("clothing_changes"):
                    completion_contexts.append("clothing")
                if state_deltas.get("memory"):
                    completion_contexts.append("memory")

                # Pick one context for a completion message
                if completion_contexts:
                    context_msg = status_gen.generate_message(random.choice(completion_contexts))
                else:
                    context_msg = status_gen.get_completion_message()

                yield {
                    "type": "checker_status",
                    "message": context_msg
                }

                # Extract and save memories
                if "memory" in state_deltas:
                    memories = state_deltas.get("memory", [])
                    if isinstance(memories, list):
                        valid_memories = []
                        for memory in memories[:2]:  # Limit to 2 memories per turn
                            if isinstance(memory, dict) and "text" in memory:
                                cleaned_text = memory["text"].strip()
                                if 10 < len(cleaned_text) < 200:
                                    characters = memory.get("characters", [])
                                    # Validate character IDs exist in the game
                                    valid_chars = [
                                        char_id for char_id in characters
                                        if char_id == "player" or char_id in engine.characters_map
                                    ]
                                    if len(characters) > 0 and len(valid_chars) == 0:
                                        engine.logger.warning(
                                            f"Memory has invalid character IDs: {characters}. "
                                            f"Accepting with empty character list."
                                        )
                                    valid_memories.append({
                                        "text": cleaned_text,
                                        "characters": valid_chars,
                                        "day": state.day,
                                    })
                                else:
                                    engine.logger.warning(f"Skipped invalid memory text length: {cleaned_text[:50]}...")
                            else:
                                engine.logger.warning(f"Skipped invalid memory format: {memory}")

                        state.memory_log.extend(valid_memories)
                        state.memory_log = state.memory_log[-20:]  # Keep last 20 memories

                        if valid_memories:
                            engine.logger.debug(f"Extracted memories: {valid_memories}")

            except json.JSONDecodeError:
                engine.logger.warning(
                    f"Checker AI returned invalid JSON. Content: {checker_response.content}"
                )

        # Process give action
        if action_type == "give" and item_id and target:
            if target not in state.present_chars:
                engine.logger.warning(f"Player tried to give item to '{target}' who is not present.")
            else:
                item_def = engine.inventory.item_defs.get(item_id)
                if item_def and item_def.can_give:
                    engine.apply_effects(getattr(item_def, "gift_effects", []))
                    hook_effects = engine.inventory.apply_effect(
                        InventoryChangeEffect(
                            type="inventory_remove", owner="player", item=item_id, count=1
                        )
                    )
                    if hook_effects:
                        engine.apply_effects(hook_effects)
                    engine.logger.info(f"Player gave item '{item_id}' to '{target}'.")
                else:
                    engine.logger.warning(f"Player tried to give non-giftable item '{item_id}'.")

        if not skip_ai:
            engine.apply_ai_state_changes(state_deltas)

        if action_type == "use" and item_id:
            item_effects = engine.inventory.use_item("player", item_id)
            engine.apply_effects(item_effects)

        engine.check_and_apply_node_transitions()
        engine.modifiers.update_modifiers_for_turn(state, rng_seed=engine.get_turn_seed())
        engine.update_discoveries()

        time_info = engine.time.advance()
        engine.modifiers.tick_durations(state, time_info.minutes_passed)
        engine.time.apply_meter_dynamics(time_info)
        engine.events.decrement_cooldowns()

        final_node = engine.get_current_node()
        choices = engine._generate_choices(final_node, event_choices)

        base_narrative =narrative_from_ai or action_summary
        final_narrative = "\n\n".join([*event_narratives, base_narrative]).strip()
        state.narrative_history.append(final_narrative)

        final_state_summary = engine.get_state_summary()
        engine.logger.info("--- Turn End (Streaming) ---")

        # Send final state update
        yield {
            "type": "complete",
            "narrative": final_narrative,
            "choices": choices,
            "state_summary": final_state_summary,
            "action_summary": action_summary
        }
