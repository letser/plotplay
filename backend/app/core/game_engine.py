import json
from typing import Dict, Any, List, Optional
from app.core.state_manager import StateManager, GameState
from core.game_definition import GameDefinition
from app.core.clothing_manager import ClothingManager
from app.services.ai_service import AIService
from app.services.prompt_builder import PromptBuilder


class GameEngine:
    """Main game engine with AI integration"""

    def __init__(self, game_def: GameDefinition):
        self.game_def = game_def
        self.state_manager = StateManager(game_def)
        self.clothing_manager = ClothingManager(game_def)
        self.ai_service = AIService()
        self.prompt_builder = PromptBuilder(game_def, self.clothing_manager)
        self.narrative_history: List[str] = []

    async def process_action(
            self,
            action_type: str,
            action_text: str,
            target: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a player action through the AI pipeline"""

        # Get current node
        current_node = self._get_current_node()

        # Step 1: Generate narrative with Writer model
        narrative = await self._generate_narrative(action_text, current_node)

        # Step 2: Extract state changes with Checker model (including clothing)
        state_changes = await self._extract_state_changes(narrative, action_text, current_node)

        # Step 3: Validate and apply clothing changes
        if 'clothing_changes' in state_changes:
            validated_clothing = self.clothing_manager.process_ai_changes(
                narrative,
                state_changes['clothing_changes']
            )
            state_changes['clothing_changes'] = validated_clothing

        # Step 4: Apply all state changes
        self._apply_state_changes(state_changes)

        # Step 5: Generate available choices
        choices = self._generate_choices(current_node)

        # Step 6: Check for scene transitions
        next_node = self._check_transitions(current_node)
        if next_node:
            self.state_manager.state.current_node = next_node

        # Store narrative in history
        self.narrative_history.append(narrative)
        if len(self.narrative_history) > 10:
            self.narrative_history.pop(0)

        # Get appearance info
        appearance_info = {}
        for char_id in self.state_manager.state.present_chars:
            appearance_info[char_id] = {
                'clothing': self.clothing_manager.get_character_appearance(char_id),
                'intimacy_level': self.clothing_manager.get_intimacy_level(char_id)
            }

        return {
            'narrative': narrative,
            'choices': choices,
            'state_changes': state_changes,
            'current_state': self._get_state_summary(),
            'appearances': appearance_info
        }

    async def _generate_narrative(self, action: str, node: Dict) -> str:
        """Generate narrative using Writer model"""

        prompt = self.prompt_builder.build_writer_prompt(
            state=self.state_manager.state,
            player_action=action,
            node=node,
            recent_history=self.narrative_history
        )

        settings = self.ai_service.settings
        response = await self.ai_service.generate(
            prompt=prompt,
            model=settings.writer_model,
            temperature=settings.writer_temperature,
            max_tokens=settings.writer_max_tokens,
            system_prompt="You are a creative narrative writer for an interactive fiction game. Create immersive, engaging prose that respects character personalities and game state."
        )

        return response.content

    async def _extract_state_changes(
            self,
            narrative: str,
            action: str,
            node: Dict
    ) -> Dict[str, Any]:
        """Extract state changes using Checker model"""

        prompt = self.prompt_builder.build_checker_prompt(
            narrative=narrative,
            player_action=action,
            state=self.state_manager.state,
            node=node
        )

        settings = self.ai_service.settings
        response = await self.ai_service.generate(
            prompt=prompt,
            model=settings.checker_model,
            temperature=settings.checker_temperature,
            max_tokens=settings.checker_max_tokens,
            system_prompt="You are a precise state tracker for a game engine. Extract exact state changes from narratives and return valid JSON only.",
            json_mode=True
        )

        try:
            # Parse JSON response
            changes = json.loads(response.content)
            return changes
        except json.JSONDecodeError:
            # Fallback to regex extraction if JSON fails
            return self._fallback_extraction(response.content)

    def _apply_state_changes(self, changes: Dict[str, Any]) -> None:
        """Apply extracted state changes to game state"""

        # Apply meter changes
        if 'meter_changes' in changes:
            for char_id, meters in changes['meter_changes'].items():
                for meter, value in meters.items():
                    path = f"meters.{char_id}.{meter}"
                    current = self.state_manager._get_path_value(path)
                    new_value = max(0, min(100, current + value))  # Cap between 0-100
                    self.state_manager._set_path_value(path, new_value)

        # Apply flag changes
        if 'flag_changes' in changes:
            for flag, value in changes['flag_changes'].items():
                self.state_manager.state.flags[flag] = value

        # Clothing changes are already applied by clothing_manager.process_ai_changes()

        # Apply location change
        if 'location_change' in changes and changes['location_change']:
            new_loc = changes['location_change'].get('new_location')
            if new_loc:
                self.state_manager.state.location_previous = self.state_manager.state.location_current
                self.state_manager.state.location_current = new_loc

    def _generate_choices(self, node: Dict) -> List[Dict[str, str]]:
        """Generate available choices based on current state"""

        choices = []

        # Get node-specific choices
        if 'dynamic_choices' in node:
            for choice in node['dynamic_choices']:
                # Check conditions
                if self._check_condition(choice.get('conditions', 'always')):
                    choices.append({
                        'id': choice.get('id', 'choice'),
                        'text': choice['prompt'],
                        'type': 'node_choice'
                    })

        # Add location-based choices
        current_location = self._get_location(self.state_manager.state.location_current)
        if current_location:
            # Movement options
            for connection in current_location.get('connections', []):
                choices.append({
                    'id': f"move_{connection['to']}",
                    'text': f"Go to {connection['to']}",
                    'type': 'movement'
                })

            # Location actions
            for action in current_location.get('available_actions', []):
                choices.append({
                    'id': f"action_{action}",
                    'text': action.replace('_', ' ').capitalize(),
                    'type': 'location_action'
                })

        # Add character interactions
        for char_id in self.state_manager.state.present_chars:
            char = self._get_character(char_id)
            if char:
                choices.append({
                    'id': f"talk_{char_id}",
                    'text': f"Talk to {char['name']}",
                    'type': 'dialogue'
                })

        # Always have at least one choice
        if not choices:
            choices.append({
                'id': 'continue',
                'text': 'Continue',
                'type': 'default'
            })

        return choices

    def _check_transitions(self, node: Dict) -> Optional[str]:
        """Check if conditions are met for scene transition"""

        if 'exit_conditions' in node:
            for condition in node['exit_conditions']:
                if self._check_condition(condition.get('trigger')):
                    return condition.get('goto')

        return None

    def _check_condition(self, condition: Any) -> bool:
        """Simple condition checker"""
        # TODO: Integrate with proper ConditionEvaluator
        if condition == 'always' or condition is None:
            return True
        return False

    def _get_state_summary(self) -> Dict[str, Any]:
        """Get summary of current game state"""
        return {
            'day': self.state_manager.state.day,
            'time': self.state_manager.state.time_slot,
            'location': self.state_manager.state.location_current,
            'present_characters': self.state_manager.state.present_chars,
            'meters': {
                char_id: meters
                for char_id, meters in self.state_manager.state.meters.items()
                if char_id in self.state_manager.state.present_chars
            },
            'inventory': dict(self.state_manager.state.inventory)
        }

    def _fallback_extraction(self, text: str) -> Dict[str, Any]:
        """Fallback extraction if JSON parsing fails"""
        return {
            'meter_changes': {},
            'flag_changes': {},
            'clothing_changes': {},
            'location_change': None,
            'player_intent': 'neutral',
            'content_flags': [],
            'emotional_tone': 'neutral'
        }

    def _get_current_node(self) -> Dict:
        """Get current story node"""
        for node in self.game_def.nodes:
            if node['id'] == self.state_manager.state.current_node:
                return node

        # Return default node if not found
        return {
            'id': 'default',
            'type': 'interactive',
            'description': 'You are here.'
        }

    def _get_character(self, char_id: str) -> Optional[Dict]:
        """Get character by ID"""
        for char in self.game_def.characters:
            if char['id'] == char_id:
                return char
        return None

    def _get_location(self, location_id: str) -> Optional[Dict]:
        """Get location by ID"""
        for loc in self.game_def.locations:
            if loc['id'] == location_id:
                return loc
        return None