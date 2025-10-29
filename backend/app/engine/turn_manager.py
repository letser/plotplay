"""Turn orchestration for PlotPlay sessions."""

from __future__ import annotations

import json
import asyncio
from typing import Any, TYPE_CHECKING

from app.models.effects import InventoryChangeEffect
from app.models.nodes import NodeType
from app.engine.checker_status import CheckerStatusGenerator

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
        skip_ai: bool = False,
    ) -> dict[str, Any]:
        engine = self.engine

        engine.logger.info("--- Turn Start ---")
        engine.turn_meter_deltas = {}
        state = engine.state_manager.state
        current_node = engine.get_current_node()

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

        turn_seed = engine.get_turn_seed()

        event_result = engine.events.process_events(turn_seed)
        event_choices = list(event_result.choices)
        event_narratives = list(event_result.narratives)

        if action_type == "choice" and choice_id:
            await engine._handle_predefined_choice(choice_id, event_choices)
            # Recapture current node after choice effects (which may include goto)
            current_node = engine.get_current_node()
            # Update present_chars from the new node if it specifies characters
            if current_node.characters_present:
                state.present_chars = [
                    char for char in current_node.characters_present if char in engine.characters_map
                ]
                engine.logger.info(
                    f"Updated present characters after choice to node '{current_node.id}': {state.present_chars}"
                )

        engine.events.process_arcs(turn_seed)

        state_deltas = {}
        narrative_from_ai = ""

        if not skip_ai:
            import time

            writer_prompt = engine.prompt_builder.build_writer_prompt(
                state,
                player_action_str,
                current_node,
                state.narrative_history,
                rng_seed=engine.get_turn_seed(),
            )

            engine.logger.info("🎨 WRITER: Generating narrative...")
            engine.logger.info(f"Writer Prompt:\n{writer_prompt}")

            writer_start = time.time()
            narrative_from_ai = (await engine.ai_service.generate(writer_prompt)).content
            writer_elapsed = time.time() - writer_start
            engine.logger.info(f"⏱️  Writer completed in {writer_elapsed:.2f}s")

            checker_prompt = engine.prompt_builder.build_checker_prompt(
                narrative_from_ai, player_action_str, state
            )

            engine.logger.info("🔍 CHECKER: Validating state changes...")
            engine.logger.info(f"Checker Prompt:\n{checker_prompt}")

            checker_start = time.time()
            checker_response = await engine.ai_service.generate(
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
            checker_elapsed = time.time() - checker_start
            engine.logger.info(f"⏱️  Checker completed in {checker_elapsed:.2f}s")

            engine.logger.info(f"Writer Response:\n{narrative_from_ai}")
            engine.logger.info(f"Checker Response:\n{checker_response.content}")

            try:
                state_deltas = json.loads(checker_response.content)

                if "memory" in state_deltas:
                    memories = state_deltas.get("memory", [])
                    if isinstance(memories, list):
                        valid_memories = []
                        for memory in memories[:2]:  # Limit to 2 memories per turn
                            # Handle both old string format and new dict format
                            if isinstance(memory, str):
                                # Legacy string format - convert to structured format
                                cleaned = memory.strip()
                                if 10 < len(cleaned) < 200:
                                    valid_memories.append({
                                        "text": cleaned,
                                        "characters": [],  # No character info in legacy format
                                        "day": state.day,
                                    })
                                else:
                                    engine.logger.warning(f"Skipped invalid memory text length: {cleaned[:50]}...")
                            elif isinstance(memory, dict) and "text" in memory:
                                # New structured format with character tags
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
            reconciled_narrative = engine._reconcile_narrative(
                player_action_str, narrative_from_ai, state_deltas, target
            )
            engine._apply_ai_state_changes(state_deltas)
        else:
            reconciled_narrative = ""

        if action_type == "use" and item_id:
            item_effects = engine.inventory.use_item("player", item_id)
            engine.apply_effects(item_effects)

        action_summary: str | None = None

        engine._check_and_apply_node_transitions()
        engine.modifiers.update_modifiers_for_turn(state, rng_seed=engine.get_turn_seed())
        engine._update_discoveries()

        time_info = engine.time.advance()
        engine.modifiers.tick_durations(state, time_info.minutes_passed)
        engine.time.apply_meter_dynamics(time_info)
        engine.events.decrement_cooldowns()

        final_node = engine.get_current_node()
        choices = engine._generate_choices(final_node, event_choices)
        action_summary = engine.state_summary.build_action_summary(player_action_str)

        base_narrative = reconciled_narrative or action_summary
        final_narrative = "\n\n".join([*event_narratives, base_narrative]).strip()
        state.narrative_history.append(final_narrative)

        final_state_summary = engine._get_state_summary()
        engine.logger.info("--- Turn End ---")

        return {
            "narrative": final_narrative,
            "choices": choices,
            "current_state": final_state_summary,
            "action_summary": action_summary,
        }

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

        if current_node.type == NodeType.ENDING:
            engine.logger.warning("Attempted to process action in an ENDING node. Halting turn.")
            yield {
                "type": "complete",
                "narrative": "The story has concluded.",
                "choices": [],
                "state_summary": engine._get_state_summary(),
                "action_summary": None
            }
            return

        if current_node.characters_present:
            state.present_chars = [
                char for char in current_node.characters_present if char in engine.characters_map
            ]
            engine.logger.info(
                f"Set present characters from node '{current_node.id}': {state.present_chars}"
            )

        player_action_str = engine._format_player_action(action_type, action_text, target, choice_id, item_id)
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
                "narrative": result["narrative"],
                "choices": result["choices"],
                "state_summary": result["current_state"],
                "action_summary": result.get("action_summary")
            }
            return
        if action_type == "do" and action_text and movement.is_movement_action(action_text):
            result = await movement.handle_freeform(action_text)
            yield {
                "type": "complete",
                "narrative": result["narrative"],
                "choices": result["choices"],
                "state_summary": result["current_state"],
                "action_summary": result.get("action_summary")
            }
            return

        turn_seed = engine.get_turn_seed()

        event_result = engine.events.process_events(turn_seed)
        event_choices = list(event_result.choices)
        event_narratives = list(event_result.narratives)

        if action_type == "choice" and choice_id:
            await engine._handle_predefined_choice(choice_id, event_choices)
            # Recapture current node after choice effects (which may include goto)
            current_node = engine.get_current_node()
            # Update present_chars from the new node if it specifies characters
            if current_node.characters_present:
                state.present_chars = [
                    char for char in current_node.characters_present if char in engine.characters_map
                ]
                engine.logger.info(
                    f"Updated present characters after choice to node '{current_node.id}': {state.present_chars}"
                )

        engine.events.process_arcs(turn_seed)

        state_deltas = {}
        narrative_from_ai = ""
        accumulated_narrative = ""

        # Stream the Writer output
        if not skip_ai:
            import time

            writer_prompt = engine.prompt_builder.build_writer_prompt(
                state,
                player_action_str,
                current_node,
                state.narrative_history,
                rng_seed=engine.get_turn_seed(),
            )

            engine.logger.info("🎨 WRITER: Generating narrative...")
            engine.logger.info(f"Writer Prompt:\n{writer_prompt}")

            # Stream narrative chunks
            writer_start = time.time()
            async for chunk in engine.ai_service.generate_stream(writer_prompt):
                accumulated_narrative += chunk
                yield {
                    "type": "narrative_chunk",
                    "content": chunk
                }

            writer_elapsed = time.time() - writer_start
            engine.logger.info(f"⏱️  Writer completed in {writer_elapsed:.2f}s")

            narrative_from_ai = accumulated_narrative
            engine.logger.info(f"Writer Response:\n{narrative_from_ai}")

            # Now run Checker with complete narrative + emit fun status messages
            checker_prompt = engine.prompt_builder.build_checker_prompt(
                narrative_from_ai, player_action_str, state
            )

            engine.logger.info("🔍 CHECKER: Validating state changes...")
            engine.logger.info(f"Checker Prompt:\n{checker_prompt}")

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
                await asyncio.sleep(0.8)  # First message after 800ms
                while True:
                    yield {
                        "type": "checker_status",
                        "message": status_gen.generate_message("generic")
                    }
                    await asyncio.sleep(0.8)

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
            status_count = 0
            while not checker_task.done():
                await asyncio.sleep(1.5)  # Increased from 0.8s to 1.5s
                if not checker_task.done():
                    status_count += 1
                    # Vary the messages
                    if status_count == 1:
                        msg = status_gen.generate_message("generic")
                    else:
                        msg = status_gen.generate_message("generic")

                    yield {
                        "type": "checker_status",
                        "message": msg
                    }

            # Get Checker result
            checker_response = await checker_task
            checker_elapsed = time.time() - checker_start
            engine.logger.info(f"⏱️  Checker completed in {checker_elapsed:.2f}s")

            engine.logger.info(f"Checker Response:\n{checker_response.content}")

            try:
                state_deltas = json.loads(checker_response.content)

                # Emit context-aware completion message based on what changed
                completion_contexts = []
                if state_deltas.get("meter_changes"):
                    completion_contexts.append("meter")
                if state_deltas.get("location_change"):
                    completion_contexts.append("location")
                if state_deltas.get("clothing_changes"):
                    completion_contexts.append("clothing")
                if state_deltas.get("memory"):
                    completion_contexts.append("memory")

                # Pick one context for completion message
                if completion_contexts:
                    context_msg = status_gen.generate_message(completion_contexts[0])
                else:
                    context_msg = status_gen.get_completion_message()

                yield {
                    "type": "checker_status",
                    "message": context_msg
                }


                if "memory" in state_deltas:
                    memories = state_deltas.get("memory", [])
                    if isinstance(memories, list):
                        valid_memories = []
                        for memory in memories[:2]:  # Limit to 2 memories per turn
                            # Handle both old string format and new dict format
                            if isinstance(memory, str):
                                # Legacy string format - convert to structured format
                                cleaned = memory.strip()
                                if 10 < len(cleaned) < 200:
                                    valid_memories.append({
                                        "text": cleaned,
                                        "characters": [],  # No character info in legacy format
                                        "day": state.day,
                                    })
                                else:
                                    engine.logger.warning(f"Skipped invalid memory text length: {cleaned[:50]}...")
                            elif isinstance(memory, dict) and "text" in memory:
                                # New structured format with character tags
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
            reconciled_narrative = engine._reconcile_narrative(
                player_action_str, narrative_from_ai, state_deltas, target
            )
            engine._apply_ai_state_changes(state_deltas)
        else:
            reconciled_narrative = ""

        if action_type == "use" and item_id:
            item_effects = engine.inventory.use_item("player", item_id)
            engine.apply_effects(item_effects)

        engine._check_and_apply_node_transitions()
        engine.modifiers.update_modifiers_for_turn(state, rng_seed=engine.get_turn_seed())
        engine._update_discoveries()

        time_info = engine.time.advance()
        engine.modifiers.tick_durations(state, time_info.minutes_passed)
        engine.time.apply_meter_dynamics(time_info)
        engine.events.decrement_cooldowns()

        final_node = engine.get_current_node()
        choices = engine._generate_choices(final_node, event_choices)

        base_narrative = reconciled_narrative or action_summary
        final_narrative = "\n\n".join([*event_narratives, base_narrative]).strip()
        state.narrative_history.append(final_narrative)

        final_state_summary = engine._get_state_summary()
        engine.logger.info("--- Turn End (Streaming) ---")

        # Send final state update
        yield {
            "type": "complete",
            "narrative": final_narrative,
            "choices": choices,
            "state_summary": final_state_summary,
            "action_summary": action_summary
        }
