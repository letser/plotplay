"""
Spec-compliant prompt builder for Writer and Checker AI models.

This module implements Section 20 (AI Contracts) of the PlotPlay specification,
constructing the Turn Context Envelope with all required fields:
- Game metadata
- Time context (day, slot, time_hhmm, weekday)
- Location context (zone, id, privacy)
- Node metadata (id, type, title, beats)
- Player inventory snapshot
- Character cards with full context (meters, gates, refusals, thresholds, outfit, modifiers)
- Recent dialogue/history
- Player action
- UI choices

Character cards follow the spec format (lines 2512-2525):
- id, summary, meters, thresholds, outfit, modifiers, dialogue_style, gates, refusals

Writer/Checker prompts follow spec templates (lines 2498-2510).
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.runtime.session import SessionRuntime
    from app.runtime.context import TurnContext
    from app.models.game import Character, MeterDefinition


class PromptBuilder:
    """
    Builds spec-compliant AI prompts with full turn context envelope.

    Responsibilities:
    - Build character cards with meters, gates, refusals, thresholds
    - Build turn context envelope with game/time/location/player data
    - Build Writer prompt following spec template
    - Build Checker prompt with full schema guidance
    """

    def __init__(self, runtime: "SessionRuntime"):
        self.runtime = runtime
        self.game = runtime.game
        self.state_manager = runtime.state_manager
        self.index = runtime.index

    def build_writer_prompt(
        self,
        ctx: "TurnContext",
        action_summary: str,
    ) -> str:
        """
        Build Writer prompt following spec template (lines 2498-2503).

        Includes:
        - Spec template with POV/tense/paragraph guidance
        - Full turn context envelope
        - Character cards
        - Recent history
        - Player action
        """
        state = self.state_manager.state
        node = ctx.current_node

        # Get POV/tense from game config
        pov = getattr(self.game, "pov", "second")  # Default: "you"
        tense = getattr(self.game, "tense", "present")  # Default: present tense
        paragraphs = 2  # Default: 2 short paragraphs

        # Build turn context envelope
        context_envelope = self._build_turn_context_envelope(ctx, action_summary)

        # Build character cards
        character_cards = self._build_character_cards_section(state, ctx)

        # Get node beats if available
        node_beats = ""
        if node and hasattr(node, "beats") and node.beats:
            node_beats = f"\nNode beats: {', '.join(node.beats)}"

        # Spec template (lines 2498-2503)
        template = f"""You are the PlotPlay Writer. POV: {pov}. Tense: {tense}. Write {paragraphs} short paragraph(s) max.
Never describe state changes (items, money, clothes). Use refusal lines if a gate blocks.
Keep dialogue natural. Stay within beats and character cards.

{context_envelope}

{character_cards}
{node_beats}

Player action: {action_summary}

Write the next narrative beat ({paragraphs} paragraphs max)."""

        return template

    def build_checker_prompt(
        self,
        ctx: "TurnContext",
        action_summary: str,
        ai_narrative: str,
    ) -> str:
        """
        Build optimized Checker prompt.

        Compact format focused on essentials:
        - Current state (location, time, present characters only)
        - Character behaviors for consent checks
        - Delta format rules
        - Memory system (character memories + optional narrative summary)
        """
        from app.core.settings import GameSettings

        state = self.state_manager.state
        settings = GameSettings()

        # Build mini character cards showing behavior guidance (same as Writer sees)
        behavior_cards = self._build_behavior_cards_for_checker(state, ctx)

        # Determine if we should request narrative summary this turn
        request_summary = state.ai_turns_since_summary >= settings.memory_summary_interval

        # Build memory instructions
        memory_instructions = """- character_memories: {{"<char_id>": "Brief interaction summary"}}
  → Only for present characters with significant interactions
  → Examples: "Discussed coffee preferences", "Shared personal story about family"
  → Skip for trivial/movement actions"""

        if request_summary:
            # Include narrative summary request
            narratives_count = min(len(state.narrative_history), settings.memory_summary_interval)
            memory_instructions += f"""
- narrative_summary: "2-4 paragraph story summary"
  → Synthesize previous summary + last {narratives_count} narratives into flowing story
  → Focus on key events, character development, relationship changes
  → Keep 200-400 words total"""

        # Compact template
        template = f"""PlotPlay Checker - extract justified state deltas from narrative.

Action: {action_summary}
Scene: {ai_narrative}

Context:
- Location: {state.current_location} ({state.current_zone}, privacy={state.current_privacy.value if state.current_privacy else 'low'})
- Time: Day {state.time.day}, {state.time.slot}, {state.time.time_hhmm}
- Present: {', '.join(state.present_characters)}

Character behaviors (consent/boundaries):
{behavior_cards}

Output JSON with deltas only:
- meters: {{"<char_id>.<meter>": "+5"}} (use +N/-N for deltas, =N for set)
- flags: {{"<flag>": true}}
- inventory/clothing/movement: [] (only if scene shows it)
{memory_instructions}

Safety: Does the scene violate any stated character behaviors above?
  → Set {{"safety": {{"ok": false}}}} if ANY behavior is violated, otherwise {{"safety": {{"ok": true}}}}

Output strict JSON (no comments):"""

        return template

    def _build_turn_context_envelope(
        self,
        ctx: "TurnContext",
        action_summary: str,
    ) -> str:
        """
        Build turn context envelope (spec lines 2412-2436).

        Includes:
        - Game metadata
        - Time context
        - Location context (with privacy)
        - Node metadata
        - Player inventory
        """
        state = self.state_manager.state
        node = ctx.current_node
        location = self.index.locations.get(state.current_location)

        # Game metadata
        game_meta = f"Game: {self.game.meta.id}"
        if hasattr(self.game.meta, "version"):
            game_meta += f" (v{self.game.meta.version})"

        # Time context
        time_ctx = (
            f"Time: Day {state.time.day}, {state.time.slot}, "
            f"{state.time.time_hhmm}, {state.time.weekday}"
        )

        # Location context with privacy
        location_name = location.name if location and hasattr(location, "name") else state.current_location
        privacy_value = state.current_privacy.value if state.current_privacy else "low"
        location_ctx = (
            f"Location: {location_name} (zone: {state.current_zone}, "
            f"privacy: {privacy_value})"
        )

        # Node metadata
        node_title = getattr(node, "title", node.id) if node else "Unknown"
        node_type = getattr(node, "type", "scene") if node else "scene"
        node_ctx = f"Node: {node.id} - \"{node_title}\" (type: {node_type})"

        # Player inventory snapshot
        player_inventory = state.inventory.get("player", {})
        inventory_items = []
        if hasattr(player_inventory, "items"):
            inventory_items.extend([f"{k}:{v}" for k, v in player_inventory.items.items() if v > 0])
        if hasattr(player_inventory, "clothing"):
            inventory_items.extend([f"{k}(clothing)" for k in player_inventory.clothing.keys()])
        inventory_ctx = f"Player inventory: {{{', '.join(inventory_items)}}}" if inventory_items else "Player inventory: {}"

        # Present characters
        present_ctx = f"Present characters: {', '.join(state.present_characters)}"

        # New memory system: narrative summary + recent narratives
        from app.core.settings import GameSettings
        settings = GameSettings()

        # Get narrative summary (if exists)
        summary_ctx = ""
        if state.narrative_summary:
            summary_ctx = f"Story so far:\n{state.narrative_summary}\n"

        # Recent narratives (last N in full)
        recent_count = settings.memory_summary_interval
        recent_narratives = state.narrative_history[-recent_count:] if state.narrative_history else []

        if recent_narratives:
            recent_ctx = "Recent scene:\n" + "\n...\n".join(recent_narratives)
        else:
            recent_ctx = "Story is just beginning."

        # Combine summary and recent narratives
        if summary_ctx:
            story_context = f"{summary_ctx}\n{recent_ctx}"
        else:
            story_context = recent_ctx

        envelope = f"""{game_meta}
{time_ctx}
{location_ctx}
{node_ctx}
{inventory_ctx}
{present_ctx}

{story_context}"""

        return envelope

    def _build_character_cards_section(
        self,
        state,
        ctx: "TurnContext",
    ) -> str:
        """
        Build character cards section with all spec-required fields.

        Includes both player and NPC cards using the same structure.
        """
        cards = []

        for char_id in state.present_characters:
            card = self._build_character_card(char_id, state, ctx)
            if card:
                cards.append(card)

        if not cards:
            return "Character cards: (none present)"

        return "Character cards:\n" + "\n\n".join(cards)

    def _build_character_card(
        self,
        char_id: str,
        state,
        ctx: "TurnContext",
    ) -> str | None:
        """
        Build a single character card for AI context.

        Uses same structure for player and NPCs, skipping undefined fields.
        Includes:
        - Current appearance (auto-generated from clothing states)
        - Meters with threshold labels
        - Behavior guidance (gates with acceptance/refusal text)
        - Modifier mixins (free text)
        - Inventory items (by name)
        """
        # Handle player card
        if char_id == "player":
            return self._build_player_card(state, ctx)

        # NPC cards require character definition
        char_def = self.index.characters.get(char_id)
        if not char_def:
            return None

        char_state = state.characters.get(char_id)
        card_lines = [f"card:"]
        card_lines.append(f'  id: "{char_id}"')
        card_lines.append(f'  name: "{char_def.name}"')

        # Appearance (current from clothing, or static fallback)
        current_appearance = self._build_current_appearance(char_id, char_def, state)
        if current_appearance:
            card_lines.append(f'  appearance: "{current_appearance}"')
        else:
            # Fallback to static appearance if no clothing state
            appearance = getattr(char_def, "appearance", None)
            if appearance:
                card_lines.append(f'  appearance: "{appearance}"')

        # Personality (if defined)
        personality = getattr(char_def, "personality", None)
        if personality:
            card_lines.append(f'  personality: "{personality}"')

        # Meters with thresholds
        meters_state = char_state.meters if char_state else {}
        meter_lines = []
        template_meters = self.index.template_meters or {}

        for meter_id, meter_def in template_meters.items():
            if meter_id in meters_state:
                value = meters_state[meter_id]
                threshold_label = self._get_threshold_label(meter_def, value)
                meter_lines.append(f"{meter_id}: {value}/{meter_def.max} ({threshold_label})")

        if meter_lines:
            meters_str = ", ".join(meter_lines)
            card_lines.append(f"  meters: {{{meters_str}}}")

        # Dialogue style (if defined)
        dialogue_style = getattr(char_def, "dialogue_style", None)
        if dialogue_style:
            card_lines.append(f'  dialogue_style: "{dialogue_style}"')

        # Behavior guidance from gates (acceptance/refusal text)
        behavior_texts = self._build_behavior_guidance(char_id, char_def, ctx)
        if behavior_texts:
            behavior_str = " | ".join(behavior_texts)
            card_lines.append(f'  behavior: "{behavior_str}"')

        # Modifier mixins (free text)
        mixin_texts = self._build_modifier_mixins(char_id, state)
        if mixin_texts:
            mixins_str = " | ".join(mixin_texts)
            card_lines.append(f'  modifiers: "{mixins_str}"')

        return "\n".join(card_lines)

    def _build_player_card(self, state, ctx: "TurnContext") -> str:
        """Build player character card with same structure as NPCs."""
        card_lines = [f"card:"]
        card_lines.append(f'  id: "player"')
        card_lines.append(f'  name: "You"')

        # Appearance (from clothing state if available)
        current_appearance = self._build_current_appearance("player", None, state)
        if current_appearance:
            card_lines.append(f'  appearance: "{current_appearance}"')

        # Player meters (if any defined)
        player_meters = state.meters.get("player", {})
        player_meter_defs = self.index.player_meters or {}
        meter_lines = []

        for meter_id, meter_def in player_meter_defs.items():
            if meter_id in player_meters:
                value = player_meters[meter_id]
                threshold_label = self._get_threshold_label(meter_def, value)
                meter_lines.append(f"{meter_id}: {value}/{meter_def.max} ({threshold_label})")

        if meter_lines:
            meters_str = ", ".join(meter_lines)
            card_lines.append(f"  meters: {{{meters_str}}}")

        return "\n".join(card_lines)

    def _build_current_appearance(self, char_id: str, char_def, state) -> str:
        """
        Auto-generate current appearance from clothing states.

        Compiles free-text descriptions from clothing items based on their condition
        (intact, opened, displaced, removed).
        """
        # Get character's clothing state
        clothing_state = state.clothing_states.get(char_id)
        if not clothing_state:
            return ""

        appearance_parts = []

        # Handle both dict and ClothingState object formats
        clothing_items_dict = None
        if isinstance(clothing_state, dict):
            # Dict format: {"outfit": "...", "items": {"jeans": "intact", ...}}
            clothing_items_dict = clothing_state.get("items", {})
        elif hasattr(clothing_state, "items"):
            # ClothingState object format
            clothing_items_dict = clothing_state.items

        if not clothing_items_dict:
            return ""

        # Build description from each clothing item's look.{condition}
        for item_id, condition in clothing_items_dict.items():
            clothing_item = self.index.clothing.get(item_id)
            if not clothing_item or not hasattr(clothing_item, "look"):
                continue

            # Get the look description for this condition
            look = clothing_item.look
            condition_str = condition.value if hasattr(condition, "value") else str(condition)

            # Map condition to look field
            description = None
            if condition_str == "intact" and hasattr(look, "intact"):
                description = look.intact
            elif condition_str == "opened" and hasattr(look, "opened"):
                description = look.opened
            elif condition_str == "displaced" and hasattr(look, "displaced"):
                description = look.displaced
            elif condition_str == "removed" and hasattr(look, "removed"):
                description = look.removed

            if description:
                appearance_parts.append(description)

        return ", ".join(appearance_parts) if appearance_parts else ""

    def _build_behavior_cards_for_checker(self, state, ctx: "TurnContext") -> str:
        """
        Build mini character cards for Checker showing behavior guidance.

        Shows the same behavior text that Writer sees, allowing Checker to validate
        whether the scene violates any stated character behaviors.
        """
        cards = []

        for char_id in state.present_characters:
            if char_id == "player":
                continue  # Skip player, behaviors are for NPCs

            char_def = self.index.characters.get(char_id)
            if not char_def:
                continue

            # Get behavior guidance (same as Writer sees)
            behavior_texts = self._build_behavior_guidance(char_id, char_def, ctx)
            if not behavior_texts:
                continue

            # Mini card with just ID and behaviors
            behavior_str = " | ".join(behavior_texts)
            cards.append(f'{char_id}: "{behavior_str}"')

        if not cards:
            return "(no behavior constraints defined)"

        return "\n".join(cards)

    def _build_behavior_guidance(self, char_id: str, char_def, ctx: "TurnContext") -> list[str]:
        """
        Build behavior guidance from gates (Way 1: show applicable text).

        For active gates, show acceptance text.
        For inactive gates, show refusal text.
        Skip gates with no applicable text.
        """
        behavior_texts = []
        gates_dict = ctx.active_gates.get(char_id, {})

        if not char_def.gates:
            return behavior_texts

        for gate in char_def.gates:
            gate_id = gate.id
            is_active = gates_dict.get(gate_id, False)

            if is_active:
                # Gate is active - show acceptance text if available
                acceptance_text = getattr(gate, "acceptance", None)
                if acceptance_text:
                    behavior_texts.append(acceptance_text)
            else:
                # Gate is inactive - show refusal text if available
                refusal_text = getattr(gate, "refusal", None)
                if refusal_text:
                    behavior_texts.append(refusal_text)

        return behavior_texts

    def _build_modifier_mixins(self, char_id: str, state) -> list[str]:
        """
        Build free-text modifier mixins.

        Extracts mixins (free text) from active modifiers, not IDs.
        """
        mixin_texts = []

        if char_id not in state.modifiers:
            return mixin_texts

        for mod_state in state.modifiers[char_id]:
            mod_id = mod_state.get("id")
            if not mod_id:
                continue

            # Get modifier definition
            mod_def = self.index.modifiers.get(mod_id)
            if not mod_def:
                continue

            # Extract mixins (free text)
            mixins = getattr(mod_def, "mixins", None)
            if mixins:
                mixin_texts.extend(mixins)

        return mixin_texts

    def _build_inventory_list(self, char_id: str, state) -> list[str]:
        """
        Build inventory list with item names (not IDs).

        Includes both regular items and clothing items.
        """
        inventory_items = []

        # Get character's inventory state
        char_inventory = state.inventory.get(char_id, {})

        # Regular items
        if hasattr(char_inventory, "items"):
            for item_id, quantity in char_inventory.items.items():
                if quantity > 0:
                    item_def = self.index.items.get(item_id)
                    if item_def:
                        item_name = getattr(item_def, "name", item_id)
                        if quantity > 1:
                            inventory_items.append(f"{item_name} (x{quantity})")
                        else:
                            inventory_items.append(item_name)

        # Clothing items (not worn, just carried)
        if hasattr(char_inventory, "clothing"):
            for clothing_id in char_inventory.clothing:
                clothing_item = self.index.clothing.get(clothing_id)
                if clothing_item:
                    clothing_name = getattr(clothing_item, "name", clothing_id)
                    inventory_items.append(clothing_name)

        return inventory_items

    def _get_threshold_label(self, meter_def: "MeterDefinition", value: int | float) -> str:
        """
        Get the threshold label for a meter value.

        Supports dict[str, MeterThreshold] format where thresholds have min/max ranges.
        Example: energy=48 with thresholds {'tired': (0-29), 'normal': (30-69), 'energized': (70-100)}
        returns "normal"
        """
        if not hasattr(meter_def, "thresholds") or not meter_def.thresholds:
            return "none"

        # Find which threshold range the value falls into
        for label, threshold in meter_def.thresholds.items():
            if hasattr(threshold, "min") and hasattr(threshold, "max"):
                # New format: MeterThreshold with min/max
                if threshold.min <= value <= threshold.max:
                    return label
            else:
                # Fallback: if threshold is just a value, not an object
                # (shouldn't happen with current spec, but be safe)
                continue

        return "none"

    def _format_gates_for_checker(self, active_gates: dict[str, dict[str, bool]]) -> str:
        """Format gates for Checker prompt."""
        if not active_gates:
            return "(no gates defined)"

        lines = []
        for char_id, gates in active_gates.items():
            active = [g for g, v in gates.items() if v]
            blocked = [g for g, v in gates.items() if not v]
            lines.append(f"{char_id}: allow=[{', '.join(active)}], deny=[{', '.join(blocked)}]")

        return "\n".join(lines)

    def _format_state_snapshot(self, state) -> str:
        """Format state snapshot for Checker (compact version)."""
        # Compact version showing key state elements
        return f"""Meters: {self._compact_meters(state.meters)}
Flags: {dict(list(state.flags.items())[:5])}...
Inventory: player={self._compact_inventory(state.inventory.get('player', {}))}
Clothing: {self._compact_clothing(state.clothing_states)}
Modifiers: {self._compact_modifiers(state.modifiers)}"""

    def _compact_meters(self, meters: dict) -> str:
        """Compact meter display."""
        items = []
        for char_id, char_meters in list(meters.items())[:2]:  # First 2 characters
            meter_str = ", ".join(f"{k}:{v}" for k, v in list(char_meters.items())[:3])
            items.append(f"{char_id}=[{meter_str}]")
        return "{" + ", ".join(items) + "...}"

    def _compact_inventory(self, inv) -> str:
        """Compact inventory display."""
        if hasattr(inv, "items"):
            items = [f"{k}:{v}" for k, v in list(inv.items.items())[:3] if v > 0]
            return "{" + ", ".join(items) + ("..." if len(inv.items) > 3 else "") + "}"
        return "{}"

    def _compact_clothing(self, clothing_states: dict) -> str:
        """Compact clothing display."""
        items = []
        for char_id, clothing in list(clothing_states.items())[:2]:
            if hasattr(clothing, "outfit") and clothing.outfit:
                items.append(f"{char_id}={clothing.outfit}")
        return "{" + ", ".join(items) + "}"

    def _compact_modifiers(self, modifiers: dict) -> str:
        """Compact modifiers display."""
        items = []
        for char_id, mods in list(modifiers.items())[:2]:
            mod_ids = [m.get("id") for m in mods[:2] if m.get("id")]
            if mod_ids:
                items.append(f"{char_id}=[{', '.join(mod_ids)}]")
        return "{" + ", ".join(items) + "}"
