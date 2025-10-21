"""
Builds prompts for the Writer and Checker AI models based on the game state.
"""

from __future__ import annotations

import json
from typing import Any

from app.core.state_manager import GameState
from app.core.clothing_manager import ClothingManager
from app.core.conditions import ConditionEvaluator
from app.models.characters import Character
from app.models.game import GameDefinition
from app.models.nodes import Node


class PromptBuilder:
    """Builds prompts for AI models."""

    MAX_MEMORY_ENTRIES = 10
    RECENT_NARRATIVE_COUNT = 2
    MEMORY_CUTOFF_OFFSET = 2

    def __init__(self, game_def: GameDefinition, clothing_manager: ClothingManager):
        self.game_def = game_def
        self.clothing_manager = clothing_manager
        self.characters_map: dict[str, Character] = {char.id: char for char in self.game_def.characters}

    # ------------------------------------------------------------------ #
    # Writer prompt
    # ------------------------------------------------------------------ #
    def build_writer_prompt(
        self,
        state: GameState,
        player_action: str,
        node: Node,
        recent_history: list[str],
        rng_seed: int | None = None,
    ) -> str:
        narration_rules = self.game_def.narration

        location = next(
            (loc for zone in self.game_def.zones for loc in zone.locations if loc.id == state.location_current), None
        )
        zone = next(
            (zone for zone in self.game_def.zones for loc in zone.locations if loc.id == state.location_current), None
        )
        privacy_level = location.privacy if location else "public"
        location_desc = (
            location.description if location and isinstance(location.description, str) else "An undescribed room."
        )

        world = getattr(self.game_def, "world", None)
        world_setting = world.get("setting", "A generic setting.") if isinstance(world, dict) else ""
        tone = world.get("tone", "A neutral tone.") if isinstance(world, dict) else ""

        player_inventory: list[str] = []
        if player_inv := state.inventory.get("player", {}):
            for item_id, count in player_inv.items():
                if count > 0:
                    item_def = next((item for item in self.game_def.items if item.id == item_id), None)
                    if item_def:
                        player_inventory.append(f"{item_def.name} (x{count})")

        arc_status = ""
        if state.active_arcs:
            arc_lines = []
            for arc_id, stage_id in state.active_arcs.items():
                arc = next((a for a in self.game_def.arcs if a.id == arc_id), None)
                if not arc:
                    continue
                stage = next((s for s in arc.stages if s.id == stage_id), None)
                if stage:
                    arc_lines.append(f"- {arc.name}: {stage.name}")
            if arc_lines:
                arc_status = "**Story Arcs:**\n" + "\n".join(arc_lines)

        time_str = f"Day {state.day}, {state.time_slot}"
        if state.time_hhmm:
            time_str += f" ({state.time_hhmm})"
        if state.weekday:
            time_str += f", {state.weekday.capitalize()}"

        character_cards = self._build_character_cards(state, rng_seed=rng_seed)

        beats_instructions = (
            "\n".join(f"- {beat}" for beat in node.beats) if node.beats else "No specific instructions for this scene."
        )

        memory_context = ""
        recent_context = ""

        if hasattr(state, "memory_log") and state.memory_log:
            memory_cutoff = max(0, len(state.memory_log) - self.MEMORY_CUTOFF_OFFSET)
            if memory_cutoff > 0:
                older_memories = state.memory_log[:memory_cutoff]
                if older_memories:
                    relevant_memories = older_memories[-self.MAX_MEMORY_ENTRIES:]
                    memory_bullets = "\n".join(f"- {m}" for m in relevant_memories)
                    memory_context = f"""
        **Key Events:**
        {memory_bullets}
        """

        if recent_history:
            recent_narratives = recent_history[-self.RECENT_NARRATIVE_COUNT:]
            recent_context = "\n...\n".join(recent_narratives) if len(recent_narratives) > 1 else recent_narratives[0]
        else:
            recent_context = "The story is just beginning."

        if memory_context:
            story_context = f"{memory_context}\n**Recent Scene:**\n{recent_context}"
        else:
            story_context = f"**Story So Far:**\n{recent_context}"

        system_prompt = f"""
        You are the PlotPlay Writer - a master storyteller for an adult interactive fiction game.
        Write from a **{narration_rules.pov} perspective** in the **{narration_rules.tense} tense**.
        Target length: **{narration_rules.paragraphs} paragraphs**.

        **CRITICAL RULES:**
        - Stay within the given scene, beats, and character details. Never introduce new elements.
        - Never explicitly mention game mechanics (items, points, meters, stats). Imply changes through narrative.
        - Respect consent boundaries. Use character refusal lines if an action is blocked.
        - Location privacy is {privacy_level}. Keep intimate actions appropriate to the setting.
        - Never speak for the player's internal thoughts or voice.
        - Keep dialogue consistent with each character's style as described.
        - This is a {node.type.value if node.type else 'scene'} node - pace accordingly.
        - Use the Key Events for factual continuity, but focus on the Recent Scene for tone and immediate context.
        """

        prompt = f"""
        {system_prompt.strip()}

        **Tone:** {tone}
        **World Setting:** {world_setting}
        **Zone:** {zone.name if zone else 'Unknown Area'}

        **Current Scene:** {node.title}
        **Location:** {location.name if location else state.location_current} - {location_desc}
        **Time:** {time_str}

        **Scene Instructions (Beats):**
        {beats_instructions}

        **Characters Present:**
        {character_cards if character_cards else "No one else is here."}

        **Player Inventory:** {', '.join(player_inventory) if player_inventory else 'Nothing of note'}

        {arc_status}

        {story_context}

        **Player's Action:** {player_action}

        Continue the narrative.
        """
        return "\n".join(line.strip() for line in prompt.split("\n"))

    # ------------------------------------------------------------------ #
    # Checker prompt
    # ------------------------------------------------------------------ #
    def build_checker_prompt(self, narrative: str, player_action: str, state: GameState) -> str:
        present_chars = [self.characters_map[cid] for cid in state.present_chars if cid in self.characters_map]

        player_meters = self.game_def.meters.player or {}
        valid_meters: dict[str, list[str]] = {"player": list(player_meters.keys())}

        for char in present_chars:
            template_meters = list((self.game_def.meters.template or {}).keys())
            char_specific_meters = list(char.meters.keys()) if char.meters else []
            valid_meters[char.id] = list(set(template_meters + char_specific_meters))

        valid_clothing_layers: dict[str, list[str]] = {}
        for char_id in ["player"] + list(state.present_chars):
            char_def = self.characters_map.get(char_id)
            if not char_def or not char_def.wardrobe:
                continue

            char_state = state.clothing_states.get(char_id)
            if char_state:
                outfit_id = char_state.get("current_outfit")
                outfit = next((o for o in char_def.wardrobe.outfits if o.id == outfit_id), None)
                if outfit:
                    valid_clothing_layers[char_id] = list(outfit.layers.keys())
            elif char_def.wardrobe.rules and char_def.wardrobe.rules.layer_order:
                valid_clothing_layers[char_id] = char_def.wardrobe.rules.layer_order

        valid_flags = list(self.game_def.flags.keys()) if self.game_def.flags else []
        valid_items = [item.id for item in self.game_def.items]

        prompt_payload = {
            "narrative": narrative,
            "player_action": player_action,
            "valid_meters": valid_meters,
            "valid_flags": valid_flags,
            "valid_items": valid_items,
            "valid_clothing_layers": valid_clothing_layers,
        }

        return json.dumps(prompt_payload, ensure_ascii=False)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _get_meter_threshold_label(self, char_id: str, meter_name: str, value: int) -> str:
        char_def = self.characters_map.get(char_id)
        meter_def = None

        if char_def and char_def.meters and meter_name in char_def.meters:
            meter_def = char_def.meters[meter_name]

        if char_id != "player":
            template_meters = self.game_def.meters.template or {}
            if meter_name in template_meters:
                meter_def = template_meters[meter_name]
        else:
            player_meters = self.game_def.meters.player or {}
            if meter_name in player_meters:
                meter_def = player_meters[meter_name]

        if meter_def and meter_def.thresholds:
            threshold_value = self._get_threshold_name(value, meter_def.thresholds)
            if threshold_value is not None:
                return threshold_value

        if value >= 80:
            return "very high"
        if value >= 60:
            return "high"
        if value >= 40:
            return "medium"
        if value >= 20:
            return "low"
        return "very low"

    @staticmethod
    def _get_threshold_name(value: int, thresholds: dict[str, list[int]]) -> str | None:
        for threshold_value in sorted(thresholds.keys(), reverse=True):
            threshold_range = thresholds[threshold_value]
            if isinstance(threshold_range, list) and len(threshold_range) == 2:
                if threshold_range[0] <= value <= threshold_range[1]:
                    return threshold_value
        return None

    def _build_character_cards(self, state: GameState, rng_seed: int | None = None) -> str:
        cards = []
        evaluator = ConditionEvaluator(state, rng_seed=rng_seed)

        for char_id in state.present_chars:
            char_def = self.characters_map.get(char_id)
            if not char_def:
                continue

            char_meters = state.meters.get(char_id, {})
            meter_parts = []
            for meter_name, value in char_meters.items():
                threshold_label = self._get_meter_threshold_label(char_id, meter_name, value)
                meter_parts.append(f"{meter_name.capitalize()}: {int(value)} ({threshold_label})")
            meter_str = ", ".join(meter_parts) if meter_parts else "No meters"

            active_modifiers = state.modifiers.get(char_id, [])
            modifier_str = f"Active Modifiers: {', '.join(mod['id'] for mod in active_modifiers) or 'None'}"

            effective_dialogue_style = char_def.dialogue_style or "neutral"
            modifiers_config = getattr(self.game_def, "modifiers", None)
            if active_modifiers and modifiers_config and getattr(modifiers_config, "library", None):
                for active_mod in active_modifiers:
                    modifier_id = active_mod.get("id")
                    if modifier_id in modifiers_config.library:
                        modifier_def = modifiers_config.library[modifier_id]
                        behavior = getattr(modifier_def, "behavior", None)
                        if behavior and getattr(behavior, "dialogue_style", None):
                            effective_dialogue_style = behavior.dialogue_style
                            break

            dialogue_style_str = f"Dialogue Style: {effective_dialogue_style}"

            allowed_behaviors: list[str] = []
            behaviors = getattr(char_def, "behaviors", None)
            gates = getattr(behaviors, "gates", None) if behaviors else None
            if gates:
                for gate in gates:
                    condition = gate.when
                    if gate.when_any:
                        condition = " or ".join(f"({c})" for c in gate.when_any)
                    elif gate.when_all:
                        condition = " and ".join(f"({c})" for c in gate.when_all)

                    if evaluator.evaluate(condition):
                        allowed_behaviors.append(gate.id)

            behavior_str = f"Will Accept: {', '.join(allowed_behaviors) or 'basic interactions'}"
            refusals = getattr(behaviors, "refusals", None) if behaviors else None
            refusal_line = getattr(refusals, "generic", None) if refusals else None
            refusal_str = f"Refusal Line (if pushed): \"{refusal_line or 'I am not comfortable with that.'}\""

            role = getattr(char_def, "role", None) or "character"
            pronouns = getattr(char_def, "pronouns", None)
            personality = getattr(char_def, "personality", None)
            personality_values: list[Any]
            if isinstance(personality, dict):
                personality_values = [v for v in personality.values() if v]
            elif hasattr(personality, "core_traits"):
                personality_values = list(personality.core_traits)
            else:
                personality_values = []

            card_lines = [
                f"- **{char_def.name} ({role})**",
                f"  - Pronouns: {', '.join(pronouns) if pronouns else 'not specified'}",
                f"  - Personality: {', '.join(personality_values) or 'reserved'}",
                f"  - {dialogue_style_str}",
                f"  - Current State: {meter_str}",
                f"  - {modifier_str}",
                f"  - Behavior: {behavior_str}",
                f"  - {refusal_str}",
                f"  - Wearing: {self.clothing_manager.get_character_appearance(char_id)}",
            ]
            cards.append("\n".join(card_lines))

        return "\n".join(cards)
