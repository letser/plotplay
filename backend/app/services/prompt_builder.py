"""
Builds prompts for the Writer and Checker AI models based on the game state.
"""
import json
from app.core.state_manager import GameState
from app.models.game import GameDefinition
from app.models.node import Node
from app.core.clothing_manager import ClothingManager
from app.models.character import Character
from app.core.conditions import ConditionEvaluator


class PromptBuilder:
    """Builds prompts for AI models."""

    def __init__(self, game_def: GameDefinition, clothing_manager: ClothingManager):
        self.game_def = game_def
        self.clothing_manager = clothing_manager
        self.characters_map: dict[str, Character] = {char.id: char for char in self.game_def.characters}

    def build_writer_prompt(self, state: GameState, player_action: str, node: Node,
                            recent_history: list[str], rng_seed: int | None = None) -> str:
        """Enhanced writer prompt with hybrid memory/narrative context."""

        narration_rules = self.game_def.narration

        # Get location and zone
        location = next((loc for zone in self.game_def.zones
                         for loc in zone.locations
                         if loc.id == state.location_current), None)
        zone = next((zone for zone in self.game_def.zones
                     for loc in zone.locations
                     if loc.id == state.location_current), None)
        privacy_level = location.privacy if location else "public"
        location_desc = location.description if location and isinstance(location.description,
                                                                        str) else "An undescribed room."

        # Get world settings from game_def
        world_setting = self.game_def.world.get("setting", "A generic setting.") if self.game_def.world else ""
        tone = self.game_def.world.get("tone", "A neutral tone.") if self.game_def.world else ""

        # Get player inventory for context
        player_inventory = []
        if player_inv := state.inventory.get("player", {}):
            for item_id, count in player_inv.items():
                if count > 0:
                    item_def = next((item for item in self.game_def.items if item.id == item_id), None)
                    if item_def:
                        player_inventory.append(f"{item_def.name} (x{count})")

        # Build arc context string
        arc_status = ""
        if state.active_arcs:
            arc_lines = []
            for arc_id, stage_id in state.active_arcs.items():
                arc = next((a for a in self.game_def.arcs if a.id == arc_id), None)
                if arc:
                    stage = next((s for s in arc.stages if s.id == stage_id), None)
                    if stage:
                        arc_lines.append(f"- {arc.name}: {stage.name}")
            if arc_lines:
                arc_status = "**Story Arcs:**\n" + "\n".join(arc_lines)

        # Format time with a clock if available
        time_str = f"Day {state.day}, {state.time_slot}"
        if state.time_hhmm:
            time_str += f" ({state.time_hhmm})"
        if state.weekday:
            time_str += f", {state.weekday.capitalize()}"

        # Build character cards (existing method)
        character_cards = self._build_character_cards(state, rng_seed=rng_seed)

        # Format beats
        beats_instructions = "\n".join(
            f"- {beat}" for beat in node.beats) if node.beats else "No specific instructions for this scene."

        # Format recent context
        # Old implementation with 3 recent narratives:
        #recent_context = "\n".join(recent_history[-3:]) if recent_history else "The story is just beginning."

        # Build hybrid context: Memory plus Recent Narrative
        memory_context = ""
        recent_context = ""

        # Memory summaries for older events (if we have more than 2 turns of history)
        if hasattr(state, 'memory_log') and state.memory_log:
            # Use memories that are older than the recent narrative we'll include
            memory_cutoff = max(0, len(state.memory_log) - 2)  # Skip last 2 turns worth of memories
            if memory_cutoff > 0:
                older_memories = state.memory_log[:memory_cutoff]
                if older_memories:
                    # Take the last 8-10 memories for context
                    relevant_memories = older_memories[-10:]
                    memory_bullets = "\n".join(f"- {m}" for m in relevant_memories)
                    memory_context = f"""
        **Key Events:**
        {memory_bullets}
        """

        # Recent narrative for immediate context and tone continuity (last 2 turns)
        if recent_history:
            # Use the last 2 narratives for dialogue/tone continuity
            recent_narratives = recent_history[-2:]
            if len(recent_narratives) > 1:
                recent_context = "\n...\n".join(recent_narratives)
            else:
                recent_context = recent_narratives[0]
        else:
            recent_context = "The story is just beginning."

        # Combine memory and recent narrative
        story_context = ""
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
        return "\n".join(line.strip() for line in prompt.split('\n'))

    def build_checker_prompt(self, narrative: str, player_action: str, state: GameState) -> str:
        """Checker prompt with state changes and memory extraction."""

        present_chars = [self.characters_map[cid] for cid in state.present_chars if cid in self.characters_map]

        # Create a valid meters list
        valid_meters = {"player": list(self.game_def.meters.get("player", {}).keys())}
        for char in present_chars:
            template_meters = list(self.game_def.meters.get("character_template", {}).keys())
            char_specific_meters = list(char.meters.keys()) if char.meters else []
            valid_meters[char.id] = list(set(template_meters + char_specific_meters))

        # Create valid clothing layers per character
        valid_clothing_layers = {}
        for char_id in ["player"] + list(state.present_chars):
            char_def = self.characters_map.get(char_id)
            if char_def and char_def.wardrobe:
                # Get layer names from current outfit
                char_state = state.clothing_states.get(char_id)
                if char_state:
                    outfit_id = char_state.get('current_outfit')
                    outfit = next((o for o in char_def.wardrobe.outfits if o.id == outfit_id), None)
                    if outfit:
                        valid_clothing_layers[char_id] = list(outfit.layers.keys())
                # Or use layer order if defined
                elif char_def.wardrobe.rules and char_def.wardrobe.rules.layer_order:
                    valid_clothing_layers[char_id] = char_def.wardrobe.rules.layer_order

        valid_flags = list(self.game_def.flags.keys()) if self.game_def.flags else []
        valid_items = [item.id for item in self.game_def.items]

        # Get location for context hints
        location = next((loc for zone in self.game_def.zones
                         for loc in zone.locations
                         if loc.id == state.location_current), None)

        # Build context hints
        context_hints = f"""
        **Context Hints:**
        - Location Privacy: {location.privacy if location else 'public'}
        - Time of Day: {state.time_slot}
        - Active Modifiers: {json.dumps({char_id: [mod['id'] for mod in mods]
                                         for char_id, mods in state.modifiers.items() if mods})}
        """

        prompt = f"""
        You are a strict data extraction engine. Analyze the narrative and extract ONLY concrete state changes.

        **CRITICAL INSTRUCTIONS:**
        1. **Analyze ACTIONS, not dialogue:** Extract only from physical actions happening NOW.
        2. **IGNORE stories/memories:** Skip backstory, hypotheticals, or past/future references.
        3. **BE CONSERVATIVE:** If uncertain, DO NOT report a change. No emotional inference without clear evidence.
        4. **Use Valid IDs ONLY:** Use only the exact IDs provided below.
        5. **OUTPUT FORMAT:** Return ONLY the JSON object with these keys: meter_changes, flag_changes, inventory_changes, clothing_changes
        6. **Meter changes:** Only report if narrative CLEARLY shows emotional/physical change through actions or strong reactions.
        7. **Clothing:** Only valid layers can be changed. Check the Valid Clothing Layers list.
        8. **Memory:** Add 1-2 brief factual summaries of notable events from this turn.

        **Player's Action:** "{player_action}"
        **Narrative to Analyze:** "{narrative}"

        {context_hints}

        **Current State Context:**
        - Meters: {json.dumps(state.meters)}
        - Flags: {json.dumps(state.flags)}
        - Current Inventory: {json.dumps(state.inventory)}

        **Valid Game Entities (Use ONLY these IDs):**
        - Valid Meters: {json.dumps(valid_meters)}
        - Valid Flags: {json.dumps(valid_flags)}
        - Valid Items: {json.dumps(valid_items)}
        - Valid Clothing Layers: {json.dumps(valid_clothing_layers)}

        **JSON Extraction Schema:**
        {{
          "meter_changes": {{ "character_id": {{ "meter_name": +/-value }} }},
          "flag_changes": {{ "flag_name": new_value }},
          "inventory_changes": {{ "owner_id": {{ "item_id": +/-count }} }},
          "clothing_changes": {{ "character_id": {{ "removed": ["layer_name"], "displaced": ["layer_name"] }} }},
          "memory": ["Brief factual summary of key events (1-2 sentences max)"]
        }}

        For memory field: Focus on actions taken, emotional changes, agreements made, items given/received.
        Good examples: "Emma shared her phone number with you", "You rejected Alex's invitation, hurting their feelings"

        Respond with ONLY a valid JSON object. No text before or after the JSON.
        """
        return "\n".join(line.strip() for line in prompt.split('\n'))

    def _get_meter_threshold_label(self, char_id: str, meter_name: str, value: int) -> str:
        """Get the threshold label for a meter value."""
        # Check character-specific meter thresholds
        char_def = self.characters_map.get(char_id)
        if char_def and char_def.meters and meter_name in char_def.meters:
            meter_def = char_def.meters[meter_name]
            if meter_def.thresholds:
                for threshold_value in sorted(meter_def.thresholds.keys(), reverse=True):
                    if value >= threshold_value:
                        return meter_def.thresholds[threshold_value]

        # Check template meter thresholds
        if char_id != "player":
            template_meters = self.game_def.meters.get("character_template", {})
            if meter_name in template_meters:
                meter_def = template_meters[meter_name]
                if meter_def.thresholds:
                    for threshold_value in sorted(meter_def.thresholds.keys(), reverse=True):
                        if value >= threshold_value:
                            return meter_def.thresholds[threshold_value]
        else:
            # Check player meters
            player_meters = self.game_def.meters.get("player", {})
            if meter_name in player_meters:
                meter_def = player_meters[meter_name]
                if meter_def.thresholds:
                    for threshold_value in sorted(meter_def.thresholds.keys(), reverse=True):
                        if value >= threshold_value:
                            return meter_def.thresholds[threshold_value]

        # Default labels based on percentage
        if value >= 80:
            return "very high"
        elif value >= 60:
            return "high"
        elif value >= 40:
            return "medium"
        elif value >= 20:
            return "low"
        else:
            return "very low"

    def _build_character_cards(self, state: GameState, rng_seed: int | None = None) -> str:
        """Constructs the 'character card' summaries for the prompt."""
        cards = []
        evaluator = ConditionEvaluator(state, state.present_chars, rng_seed=rng_seed)

        for char_id in state.present_chars:
            char_def = self.characters_map.get(char_id)
            if not char_def: continue

            # --- Dynamic Meters ---
            char_meters = state.meters.get(char_id, {})
            meter_parts = []
            for meter_name, value in char_meters.items():
                threshold_label = self._get_meter_threshold_label(char_id, meter_name, value)
                meter_parts.append(f"{meter_name.capitalize()}: {int(value)} ({threshold_label})")
            meter_str = ", ".join(meter_parts) if meter_parts else "No meters"

            # --- Active Modifiers ---
            active_modifiers = state.modifiers.get(char_id, [])
            modifier_str = f"Active Modifiers: {', '.join(mod['id'] for mod in active_modifiers) or 'None'}"

            # --- Dialogue Style ---
            effective_dialogue_style = char_def.dialogue_style or "neutral"
            if active_modifiers and self.game_def.modifier_system:
                for active_mod in active_modifiers:
                    modifier_id = active_mod.get('id')
                    if modifier_id in self.game_def.modifier_system.library:
                        modifier_def = self.game_def.modifier_system.library[modifier_id]
                        if modifier_def.behavior and modifier_def.behavior.dialogue_style:
                            effective_dialogue_style = modifier_def.behavior.dialogue_style
                            break

            dialogue_style_str = f"Dialogue Style: {effective_dialogue_style}"

            # --- Resolve Consent Gates ---
            allowed_behaviors = []
            if char_def.behaviors and char_def.behaviors.gates:
                for gate in char_def.behaviors.gates:
                    condition = gate.when
                    if gate.when_any:
                        condition = " or ".join(f"({c})" for c in gate.when_any)
                    elif gate.when_all:
                        condition = " and ".join(f"({c})" for c in gate.when_all)

                    if evaluator.evaluate(condition):
                        allowed_behaviors.append(gate.id)

            behavior_str = f"Will Accept: {', '.join(allowed_behaviors) or 'basic interactions'}"
            refusal_str = f"Refusal Line (if pushed): \"{char_def.behaviors.refusals.generic if char_def.behaviors and char_def.behaviors.refusals else 'I am not comfortable with that.'}\""

            # --- Assemble Card ---
            card_lines = [
                f"- **{char_def.name} ({char_def.role or 'character'})**",
                f"  - Pronouns: {', '.join(char_def.pronouns) if char_def.pronouns else 'not specified'}",
                f"  - Personality: {', '.join(char_def.personality.core_traits if char_def.personality else [])}",
                f"  - {dialogue_style_str}",
                f"  - Current State: {meter_str}",
                f"  - {modifier_str}",
                f"  - Behavior: {behavior_str}",
                f"  - {refusal_str}",
                f"  - Wearing: {self.clothing_manager.get_character_appearance(char_id)}"
            ]
            cards.append("\n".join(card_lines))

        return "\n".join(cards)