import json
import re
from typing import Dict, Any, List, Optional
from app.core.state_manager import StateManager
from app.core.game_definition import GameDefinition
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
        self.dialogue_count = 0  # Track dialogue exchanges

    async def process_action(
            self,
            action_type: str,
            action_text: str,
            target: Optional[str] = None,
            choice_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a player action through the AI pipeline"""

        # Handle predefined choice
        if action_type == "choice" and choice_id:
            return await self._handle_predefined_choice(choice_id, action_text)

        # Handle movement separately
        if action_type == "do" and self._is_movement_action(action_text):
            return await self._handle_movement(action_text)

        # Get current node
        current_node = self._get_current_node()

        # Format action for AI based on type
        if action_type == "say":
            formatted_action = f'Say to {target or "everyone"}: "{action_text}"'
            self.dialogue_count += 1
        else:  # "do"
            formatted_action = action_text
            self.dialogue_count = 0  # Reset on action

        # Step 1: Generate narrative
        narrative = await self._generate_narrative(formatted_action, current_node)

        # Step 2: Extract state changes
        state_changes = await self._extract_state_changes(narrative, formatted_action, current_node)

        # Step 3: Validate and apply clothing changes
        if 'clothing_changes' in state_changes:
            validated_clothing = self.clothing_manager.process_ai_changes(
                narrative,
                state_changes['clothing_changes']
            )
            state_changes['clothing_changes'] = validated_clothing

        # Step 4: Apply state changes
        self._apply_state_changes(state_changes)

        # Step 5: Check for time advancement
        time_advanced = self._check_time_advancement(action_type)

        # Step 6: Generate choices
        choices = self._generate_choices(current_node)

        # Step 7: Check for scene transitions
        location_changed = False
        if 'location_change' in state_changes and state_changes['location_change']:
            location_changed = True

        next_node = self._check_transitions(current_node)
        if next_node:
            self.state_manager.state.current_node = next_node

        # Store narrative
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
            'appearances': appearance_info,
            'time_advanced': time_advanced,
            'location_changed': location_changed
        }

    def _is_movement_action(self, action_text: str) -> bool:
        """Check if action is about movement"""
        movement_patterns = [
            r'\b(go|walk|move|head|travel|enter|exit|leave)\s+(to|towards?|into|out)\b',
            r'\b(go|leave|exit)\s+(north|south|east|west|up|down)\b',
        ]
        action_lower = action_text.lower()
        return any(re.search(pattern, action_lower) for pattern in movement_patterns)

    async def _handle_movement(self, action_text: str) -> Dict[str, Any]:
        """Handle movement actions"""
        current_loc = self._get_location(self.state_manager.state.location_current)
        if not current_loc:
            return await self._generate_error_response("You're in an undefined location.")

        # Try to extract destination from action
        action_lower = action_text.lower()

        for connection in current_loc.get('connections', []):
            dest = connection['to']
            dest_loc = self._get_location(dest)
            if dest_loc:
                dest_name = dest_loc['name'].lower()
                if dest in action_lower or dest_name in action_lower:
                    # Move to this location
                    return await self._execute_movement(dest)

        # If no specific destination found, list options
        if current_loc.get('connections'):
            options = [self._get_location(c['to'])['name'] for c in current_loc['connections']]
            narrative = f"You look around for exits. You can go to: {', '.join(options)}"
        else:
            narrative = "There's nowhere to go from here."

        return {
            'narrative': narrative,
            'choices': self._generate_choices(self._get_current_node()),
            'current_state': self._get_state_summary(),
            'appearances': {},
            'time_advanced': False,
            'location_changed': False
        }

    async def _execute_movement(self, destination: str) -> Dict[str, Any]:
        """Execute movement to a new location"""
        old_location = self.state_manager.state.location_current

        # Update location
        self.state_manager.state.location_previous = old_location
        self.state_manager.state.location_current = destination

        # Clear NPCs from old location (they don't follow automatically)
        self.state_manager.state.present_chars = []

        # Check if any NPCs are in the new location based on their schedule
        self._update_npc_presence()

        # Generate description of new location
        new_loc = self._get_location(destination)
        time_slot = self.state_manager.state.time_slot

        description = new_loc.get('description', {})
        if isinstance(description, dict):
            loc_desc = description.get(time_slot, description.get('default', ''))
        else:
            loc_desc = str(description)

        narrative = f"You move to {new_loc['name']}. {loc_desc}"

        if self.state_manager.state.present_chars:
            chars = [self._get_character(c)['name'] for c in self.state_manager.state.present_chars]
            narrative += f"\n\n{', '.join(chars)} {'is' if len(chars) == 1 else 'are'} here."

        # Advance time for movement
        self._advance_time()

        return {
            'narrative': narrative,
            'choices': self._generate_choices(self._get_current_node()),
            'current_state': self._get_state_summary(),
            'appearances': {},
            'time_advanced': True,
            'location_changed': True
        }

    def _update_npc_presence(self):
        """Update which NPCs are present based on schedules"""
        current_time = self.state_manager.state.time_slot
        current_loc = self.state_manager.state.location_current

        for char in self.game_def.characters:
            char_id = char['id']
            schedule = char.get('schedule', {})

            if current_time in schedule:
                scheduled_loc = schedule[current_time].get('location')
                if scheduled_loc == current_loc:
                    if char_id not in self.state_manager.state.present_chars:
                        self.state_manager.state.present_chars.append(char_id)

    def _check_time_advancement(self, action_type: str) -> bool:
        """Check if time should advance"""
        state = self.state_manager.state
        config = self.game_def.config.get('game', {}).get('time_system', {})

        # Don't advance during dialogue unless it's been long
        if action_type == "say" and self.dialogue_count < 5:
            return False

        # Track significant actions
        state.actions_this_slot += 1

        # Check if we should advance
        actions_per_slot = config.get('actions_per_slot', 3)
        if state.actions_this_slot >= actions_per_slot:
            self._advance_time()
            return True

        return False

    def _advance_time(self):
        """Advance time to next slot"""
        state = self.state_manager.state
        time_slots = self.game_def.config['game']['time_system']['slots']

        current_idx = time_slots.index(state.time_slot)
        current_idx += 1

        if current_idx >= len(time_slots):
            current_idx = 0
            state.day += 1

        state.time_slot = time_slots[current_idx]
        state.actions_this_slot = 0
        self.dialogue_count = 0

        # Update NPC presence based on new time
        self._update_npc_presence()

    async def _handle_predefined_choice(self, choice_id: str, action_text: str) -> Dict[str, Any]:
        """Handle a predefined choice selection"""
        # This handles the quick action buttons
        if choice_id.startswith("move_"):
            destination = choice_id.replace("move_", "")
            return await self._execute_movement(destination)
        elif choice_id.startswith("talk_"):
            char_id = choice_id.replace("talk_", "")
            return await self.process_action("say", "Hello", target=char_id)
        else:
            # Treat as a "do" action
            return await self.process_action("do", action_text)

    def _generate_choices(self, node: Dict) -> List[Dict[str, str]]:
        """Generate available choices based on current state"""
        choices = []

        # Always add free-form options first
        choices.extend([
            {
                'id': 'custom_say',
                'text': '💬 Say something...',
                'type': 'custom_say',
                'custom': True
            },
            {
                'id': 'custom_do',
                'text': '✋ Do something...',
                'type': 'custom_do',
                'custom': True
            }
        ])

        # Add quick actions as suggestions
        choices.append({
            'id': 'divider',
            'text': '--- Quick Actions ---',
            'type': 'divider',
            'disabled': True
        })

        # Get node-specific choices
        if 'dynamic_choices' in node:
            for choice in node['dynamic_choices']:
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
                dest_loc = self._get_location(connection['to'])
                if dest_loc:
                    choices.append({
                        'id': f"move_{connection['to']}",
                        'text': f"🚶 Go to {dest_loc['name']}",
                        'type': 'movement'
                    })

        # Add character interactions
        for char_id in self.state_manager.state.present_chars:
            char = self._get_character(char_id)
            if char:
                choices.append({
                    'id': f"talk_{char_id}",
                    'text': f"💬 Talk to {char['name']}",
                    'type': 'dialogue'
                })

        return choices

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
        """Extract state changes using a Checker model"""

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
                    current = self.state_manager.get_path_value(path)
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
        """Get the current story node"""
        for node in self.game_def.nodes:
            if node['id'] == self.state_manager.state.current_node:
                return node

        # Return the default node if not found
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