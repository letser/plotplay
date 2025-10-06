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

    def build_writer_prompt(
        self,
        state: GameState,
        player_action: str,
        node: Node,
        recent_history: list[str],
        rng_seed: int | None = None,
    ) -> str:
        """Builds the main prompt for the narrative Writer AI."""

        narration_rules = self.game_def.narration
        location = next((loc for zone in self.game_def.zones for loc in zone.locations if loc.id == state.location_current), None)
        location_desc = location.description if location and isinstance(location.description, str) else "An undescribed room."
        privacy_level = location.privacy if location else "public"

        system_prompt = f"""
        You are the PlotPlay Writer - a master storyteller for an adult interactive fiction game.
        Write from a **{narration_rules.pov} perspective** in the **{narration_rules.tense} tense**, 
        up to **{narration_rules.paragraphs} paragraphs**.

        **CRITICAL RULES:**
        - Stay within the given scene and character details. Use only the provided beats and characters.
        - Never introduce new characters or unrelated events.
        - Never explicitly mention game mechanics (items, points, meters). Imply changes through narrative.
        - Respect consent boundaries. Use character refusal lines if an action is blocked.
        - Location privacy is {privacy_level}. Keep intimate actions appropriate to the setting.
        - Never speak for the player's internal thoughts or voice.
        """

        world_setting = self.game_def.world.get("setting", "A generic setting.") if self.game_def.world else ""
        tone = self.game_def.world.get("tone", "A neutral tone.") if self.game_def.world else ""

        character_cards = self._build_character_cards(state, rng_seed=rng_seed)

        # Format the beats for inclusion in the prompt
        beats_instructions = "\n".join(f"- {beat}" for beat in node.beats) if node.beats else "No specific instructions for this scene."

        recent_context = "\n".join(recent_history[-3:]) if recent_history else "The story is just beginning."

        prompt = f"""
        {system_prompt.strip()}

        **Tone:** {tone}
        **World Setting:** {world_setting}
        
        **Current Scene:** {node.title}
        **Location:** {location.name if location else state.location_current} - {location_desc}
        **Time:** Day {state.day}, {state.time_slot}

        **Scene Instructions (Beats):**
        {beats_instructions}

        **Characters Present:**
        {character_cards if character_cards else "No one else is here."}

        **Story So Far:**
        ...{recent_context}

        **Player's Action:** {player_action}

        Continue the narrative.
        """
        return "\n".join(line.strip() for line in prompt.split('\n'))

    def build_checker_prompt(
            self,
            narrative: str,
            player_action: str,
            state: GameState,
    ) -> str:
        """Builds the prompt for the state-extracting Checker AI."""

        present_chars = [self.characters_map[cid] for cid in state.present_chars if cid in self.characters_map]

        # Create a more precise list of valid meters for the current characters
        valid_meters = {"player": list(self.game_def.meters.get("player", {}).keys())}
        for char in present_chars:
            template_meters = list(self.game_def.meters.get("character_template", {}).keys())
            char_specific_meters = list(char.meters.keys()) if char.meters else []
            valid_meters[char.id] = list(set(template_meters + char_specific_meters))

        valid_flags = list(self.game_def.flags.keys()) if self.game_def.flags else []
        valid_items = [item.id for item in self.game_def.items]

        prompt = f"""
        You are a strict data extraction engine. Analyze the narrative and extract ONLY concrete state changes.

        **CRITICAL INSTRUCTIONS:**
        1. **Analyze ACTIONS, not dialogue:** Extract only from physical actions happening NOW.
        2. **IGNORE stories/memories:** Skip backstory, hypotheticals, or past/future references.
        3. **BE CONSERVATIVE:** If uncertain, DO NOT report a change. No emotional inference without clear evidence.
        4. **Use Valid IDs ONLY:** Use only the exact IDs provided below.
        5. **OUTPUT FORMAT:** Return ONLY the JSON object with these keys: meter_changes, flag_changes, inventory_changes, clothing_changes

        **Player's Action:** "{player_action}"
        **Narrative to Analyze:** "{narrative}"
        
        **Current State Context:**
        - Meters: {json.dumps(state.meters)}
        - Flags: {json.dumps(state.flags)}

        **Valid Game Entities (Use ONLY these IDs):**
        - Valid Meters: {json.dumps(valid_meters)}
        - Valid Flags: {json.dumps(valid_flags)}
        - Valid Items: {json.dumps(valid_items)}

        **JSON Extraction Schema:**
        {{
          "meter_changes": {{ "character_id": {{ "meter_name": +/-change_value }} }},
          "flag_changes": {{ "flag_name": new_value }},
          "inventory_changes": {{ "owner_id": {{ "item_id": +/-change_value }} }},
          "clothing_changes": {{ "character_id": {{ "removed": ["layer_name"], "displaced": ["layer_name"] }} }}
        }}

        Respond ONLY with a single, valid JSON object.
        """
        return "\n".join(line.strip() for line in prompt.split('\n'))

    def _build_character_cards(self, state: GameState, rng_seed: int | None = None) -> str:
        """Constructs the 'character card' summaries for the prompt."""
        cards = []
        evaluator = ConditionEvaluator(state, state.present_chars, rng_seed=rng_seed)

        for char_id in state.present_chars:
            char_def = self.characters_map.get(char_id)
            if not char_def: continue

            # --- Dynamic Meters ---
            char_meters = state.meters.get(char_id, {})
            meter_str = ", ".join(f"{name.capitalize()}({int(value)})" for name, value in char_meters.items())

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
                            # The first modifier with dialogue_style wins
                            effective_dialogue_style = modifier_def.behavior.dialogue_style
                            break

            dialogue_style_str = f"Dialogue Style: {effective_dialogue_style}"

            # --- Resolve Consent Gates ---
            allowed_behaviors = []
            if char_def.behaviors and char_def.behaviors.gates:
                for gate in char_def.behaviors.gates:
                    # Combine the different condition types into one evaluatable string
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