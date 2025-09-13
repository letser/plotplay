import json
from typing import Dict, Any, List, Optional
from app.core.state_manager import GameState
from app.core.game_loader import GameDefinition


class PromptBuilder:
    """Builds prompts for AI models"""

    def __init__(self, game_def: GameDefinition, clothing_manager=None):
        self.game_def = game_def
        self.clothing_manager = clothing_manager

    def build_writer_prompt(
                self,
                state: GameState,
                player_action: str,
                node: Dict[str, Any],
                recent_history: List[str]
        ) -> str:
            """Build prompt for narrative generation with clothing awareness"""

            # Get world context
            world_setting = self.game_def.world.get('world', {}).get('setting', '')
            tone = self.game_def.world.get('world', {}).get('tone', '')

            # Build character states
            char_states = self._build_character_states(state)

            # Get location description
            location = self._get_location(state.location_current)
            location_desc = location.get('description', {}).get('default', '') if location else ''

            # Build appearance descriptions with clothing
            appearances = self._build_appearance_descriptions(state)

            # Get clothing-specific instructions
            clothing_instructions = self._get_clothing_instructions(state)

            # Recent context
            recent_context = "\n".join(recent_history[-3:]) if recent_history else "Story beginning"

            # Check if NSFW content is allowed
            nsfw_level = self.game_def.config.get('game', {}).get('nsfw_level', 'none')
            nsfw_instructions = self._get_nsfw_instructions(nsfw_level, node)

            prompt = f"""You are the narrator for an interactive fiction game.

    WORLD SETTING: {world_setting}
    TONE: {tone}
    CURRENT LOCATION: {state.location_current} - {location_desc}
    TIME: Day {state.day}, {state.time_slot}

    CHARACTERS PRESENT:
    {chr(10).join(appearances) if appearances else "No other characters present"}

    CHARACTER STATES:
    {char_states}

    {clothing_instructions}

    RECENT CONTEXT:
    {recent_context}

    PLAYER ACTION: "{player_action}"

    INSTRUCTIONS:
    - Write 2-3 paragraphs continuing the scene
    - Include sensory details and environmental atmosphere
    - Show character reactions based on their personality and current state
    - When describing clothing changes, be specific about what items are affected
    - Maintain continuity with current clothing states
    {nsfw_instructions}
    - End with a clear moment for the next player choice
    - DO NOT write player dialogue or actions beyond what was specified

    Continue the scene:"""

            return prompt

    def build_checker_prompt(
                self,
                narrative: str,
                player_action: str,
                state: GameState,
                node: Dict[str, Any]
        ) -> str:
            """Build prompt for state extraction including clothing"""

            current_meters = {
                char_id: meters
                for char_id, meters in state.meters.items()
                if char_id in state.present_chars
            }

            # Get current clothing states for context
            clothing_context = {}
            if self.clothing_manager:
                for char_id in state.present_chars:
                    clothing_context[char_id] = self.clothing_manager.get_clothing_context(char_id)

            prompt = f"""Analyze this game narrative for state changes.

    PLAYER ACTION: "{player_action}"

    NARRATIVE OUTPUT:
    "{narrative}"

    CURRENT CHARACTER METERS:
    {json.dumps(current_meters, indent=2)}

    CURRENT CLOTHING STATES:
    {json.dumps(clothing_context, indent=2)}

    CURRENT FLAGS:
    {json.dumps(state.flags, indent=2)}

    Extract the following information and return as JSON:

    1. meter_changes: Changes to character meters based on the narrative
       Format: {{"character_id": {{"meter": change_amount}}}}
       Example: {{"emma": {{"trust": 5, "attraction": -3}}}}

    2. flag_changes: New flags to set based on events
       Format: {{"flag_name": value}}
       Example: {{"first_kiss": true, "emma_angry": true}}

    3. clothing_changes: Any clothing state changes described in the narrative
       For each character, identify:
       - removed: Items completely taken off (jacket, shirt, pants, etc.)
       - displaced: Items moved/disheveled but not removed (pushed up, pulled aside, loosened)
       - added: Items put back on or newly worn

       Format: {{"character_id": {{"removed": ["layer"], "displaced": ["layer"], "added": ["layer"]}}}}
       Layer names: outer, top, bottom, dress, underwear_top, underwear_bottom, feet

       Example: {{"alex": {{"removed": ["feet", "outer"], "displaced": ["top"], "added": []}}}}

       Important: Only report clothing changes that are explicitly described or clearly implied in the narrative.

    4. location_change: If the location changed
       Format: {{"new_location": "location_id"}} or null

    5. player_intent: Categorize the player's action
       Options: "flirt", "intimate", "aggressive", "investigate", "help", "casual", "neutral"

    6. content_flags: Content warnings in the narrative
       Format: ["violence", "intimacy", "profanity"] or []

    7. emotional_tone: Overall emotional result
       Options: "positive", "negative", "tense", "romantic", "passionate", "neutral"

    8. intimacy_escalation: Did physical intimacy increase?
       Format: boolean (true/false)

    Return ONLY valid JSON:"""

            return prompt

    def _build_appearance_descriptions(self, state: GameState) -> List[str]:
        """Build character appearance descriptions with clothing"""
        descriptions = []

        for char_id in state.present_chars:
            char = self._get_character(char_id)
            if not char:
                continue

            appearance = char.get('appearance', {}).get('base', {})

            # Get clothing description
            if self.clothing_manager:
                clothing_desc = self.clothing_manager.get_character_appearance(char_id)
                intimacy = self.clothing_manager.get_intimacy_level(char_id)
            else:
                clothing_desc = "dressed normally"
                intimacy = "none"

            # Build full description
            desc_parts = [f"{char['name']}:"]

            # Physical appearance
            if appearance.get('height'):
                desc_parts.append(appearance['height'])
            if appearance.get('build'):
                desc_parts.append(appearance['build'])
            if appearance.get('hair'):
                desc_parts.append(appearance['hair'])

            # Check for body state modifiers (arousal, exhaustion, etc.)
            body_state = self._get_body_state_modifiers(char, state.meters.get(char_id, {}))
            if body_state:
                desc_parts.append(f"({body_state})")

            # Clothing
            desc_parts.append(f"Currently wearing: {clothing_desc}")

            # Add intimacy context if relevant
            if intimacy != "none":
                desc_parts.append(f"[Intimacy level: {intimacy}]")

            descriptions.append(" ".join(desc_parts))

        return descriptions

    def _get_clothing_instructions(self, state: GameState) -> str:
        """Get specific instructions about clothing continuity"""
        if not self.clothing_manager:
            return ""

        instructions = []
        for char_id in state.present_chars:
            context = self.clothing_manager.get_clothing_context(char_id)
            if context['removed']:
                instructions.append(
                    f"{self._get_character_name(char_id)} has already removed: {', '.join(context['removed'])}")
            if context['displaced']:
                instructions.append(
                    f"{self._get_character_name(char_id)} has displaced: {', '.join(context['displaced'])}")

        if instructions:
            return "CLOTHING CONTINUITY:\n" + "\n".join(instructions)
        return ""


    def _build_character_states(self, state: GameState) -> str:
        """Build character state descriptions"""
        states = []

        for char_id in state.present_chars:
            char = self._get_character(char_id)
            if not char:
                continue

            meters = state.meters.get(char_id, {})

            # Determine mood based on meters
            mood = self._determine_mood(char, meters)

            # Determine available behaviors
            behaviors = self._get_available_behaviors(char, state)

            state_desc = f"""{char['name']}:
- Mood: {mood}
- Trust: {meters.get('trust', 0)}/100 ({self._describe_level(meters.get('trust', 0))})
- Attraction: {meters.get('attraction', 0)}/100 ({self._describe_level(meters.get('attraction', 0))})
- Arousal: {meters.get('arousal', 0)}/100 ({self._describe_level(meters.get('arousal', 0))})
- Energy: {meters.get('energy', 100)}/100
- Will accept: {', '.join(behaviors) if behaviors else 'casual interaction only'}"""

            states.append(state_desc)

        return "\n\n".join(states) if states else "No characters to track"

    def _build_appearance_descriptions(self, state: GameState) -> List[str]:
        """Build character appearance descriptions"""
        descriptions = []

        for char_id in state.present_chars:
            char = self._get_character(char_id)
            if not char:
                continue

            appearance = char.get('appearance', {}).get('base', {})
            clothing_state = state.clothing_states.get(char_id, {})

            # Basic appearance
            desc = f"{char['name']}: {appearance.get('height', '')}, {appearance.get('build', '')}. "
            desc += f"{appearance.get('hair', '')}. "

            # Current outfit
            if clothing_state:
                visible_clothes = self._describe_visible_clothing(clothing_state)
                desc += f"Wearing: {visible_clothes}"

            descriptions.append(desc)

        return descriptions

    def _describe_visible_clothing(self, clothing_state: Dict) -> str:
        """Describe what clothing is currently visible"""
        layers = clothing_state.get('layers', {})
        removed = clothing_state.get('removed', [])
        displaced = clothing_state.get('displaced', [])

        visible = []
        for layer_name, item in layers.items():
            if layer_name not in removed:
                if layer_name in displaced:
                    visible.append(f"{item} (disheveled)")
                else:
                    visible.append(str(item))

        return ", ".join(visible) if visible else "nothing"

    def _determine_mood(self, char: Dict, meters: Dict) -> str:
        """Determine character mood from meters"""
        arousal = meters.get('arousal', 0)
        attraction = meters.get('attraction', 0)
        trust = meters.get('trust', 0)
        energy = meters.get('energy', 100)

        if energy < 20:
            return "exhausted"
        elif arousal >= 70:
            return "passionate"
        elif arousal >= 40 and attraction >= 50:
            return "flirty"
        elif attraction >= 60:
            return "affectionate"
        elif trust < 20:
            return "guarded"
        elif trust >= 60:
            return "comfortable"
        else:
            return "neutral"

    def _get_available_behaviors(self, char: Dict, state: GameState) -> List[str]:
        """Get list of behaviors character will accept"""
        behaviors = []
        char_id = char['id']
        meters = state.meters.get(char_id, {})

        # Check each behavior condition
        char_behaviors = char.get('behaviors', [])
        for behavior in char_behaviors:
            if self._check_behavior_condition(behavior.get('conditions'), state, char_id):
                behaviors.append(behavior['id'].replace('_', ' '))

        return behaviors

    def _check_behavior_condition(self, conditions: Any, state: GameState, char_id: str) -> bool:
        """Check if behavior conditions are met"""
        if conditions == "always" or conditions is None:
            return True

        # Simple implementation - expand as needed
        if isinstance(conditions, dict):
            if 'all' in conditions:
                # Would need proper condition evaluator here
                return True

        return False

    def _describe_level(self, value: float) -> str:
        """Describe a meter level"""
        if value >= 80:
            return "very high"
        elif value >= 60:
            return "high"
        elif value >= 40:
            return "moderate"
        elif value >= 20:
            return "low"
        else:
            return "very low"

    def _get_nsfw_instructions(self, nsfw_level: str, node: Dict) -> str:
        """Get content instructions based on NSFW level"""
        if node.get('nsfw'):
            if nsfw_level == 'explicit':
                return "\n- Include explicit adult content as appropriate for the scene\n- Focus on consent and emotional connection\n- Use mature but tasteful language"
            elif nsfw_level == 'suggestive':
                return "\n- Keep intimate content suggestive but not explicit\n- Imply rather than describe explicit acts\n- Focus on emotional tension and attraction"

        return "\n- Keep content appropriate and non-sexual"

    def _get_character(self, char_id: str) -> Optional[Dict]:
        """Get character definition by ID"""
        for char in self.game_def.characters:
            if char['id'] == char_id:
                return char
        return None

    def _get_location(self, location_id: str) -> Optional[Dict]:
        """Get location definition by ID"""
        for loc in self.game_def.locations:
            if loc['id'] == location_id:
                return loc
        return None