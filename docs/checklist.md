# PlotPlay Engine Implementation Checklist

**Version:** 1.0
**Last Updated:** 2025-11-21
**Purpose:** Verify that the PlotPlay engine implements all required features from the specification and turn algorithm.

---

## 1. Game Loading & Validation

### 1.1 Game Package Loading
- [ ] Load primary `game.yaml` manifest
- [ ] Process `includes` list in order
- [ ] Merge included files into main manifest
- [ ] Support all recognized root keys (meta, narration, start, meters, flags, time, economy, items, wardrobe, characters, zones, movement, nodes, modifiers, actions, events, arcs)
- [ ] Reject unknown root keys with clear error
- [ ] Enforce max include depth = 1 (no nested includes)
- [ ] Validate all file paths are within game folder (no `..`, no absolute paths)

### 1.2 Game Validation
- [ ] Validate meta section (id, title, version, authors, nsfw_allowed)
- [ ] Validate narration section (pov, tense, paragraphs)
- [ ] Validate start section (location, node, day, time)
- [ ] Verify game ID matches folder name
- [ ] Check unique IDs within each section (characters, items, nodes, events, arcs, zones, locations)
- [ ] Validate all cross-references resolve (node targets, item IDs, location IDs, zone IDs, character IDs)
- [ ] Verify start node and start location exist
- [ ] Validate time configuration sanity
- [ ] Detect and report circular references

---

## 2. Expression DSL & Conditions

### 2.1 DSL Parser
- [ ] Parse boolean operators (and, or, not)
- [ ] Parse comparison operators (==, !=, <, <=, >, >=, in)
- [ ] Parse arithmetic operators (+, -, *, /)
- [ ] Parse literals (boolean, number, string, list)
- [ ] Parse path expressions (dotted and bracketed)
- [ ] Parse function calls
- [ ] Handle operator precedence correctly
- [ ] Support parentheses for grouping
- [ ] Enforce string literals use double quotes only

### 2.2 DSL Evaluation
- [ ] Implement short-circuit evaluation for and/or
- [ ] Handle truthiness correctly (false, 0, "", [] are falsey)
- [ ] Safe path resolution (missing paths → null, no exceptions)
- [ ] Division by zero returns false with warning
- [ ] Type checking for operations
- [ ] Enforce length and nesting caps

### 2.3 Built-in Functions
- [ ] `has(owner, item_id)` - check all inventory categories
- [ ] `has_item(owner, item_id)` - check items only
- [ ] `has_clothing(owner, item_id)` - check clothing only
- [ ] `has_outfit(owner, outfit_id)` - check outfit inventory
- [ ] `knows_outfit(owner, outfit_id)` - check outfit recipe known
- [ ] `can_wear_outfit(owner, outfit_id)` - check all items available
- [ ] `wears_outfit(owner, outfit_id)` - check currently wearing
- [ ] `wears(owner, item_id)` - check wearing clothing item
- [ ] `npc_present(npc_id)` - check NPC in current location
- [ ] `discovered(zone_or_location_id)` - check discovery state
- [ ] `unlocked(category, id)` - check unlock state
- [ ] `rand(p)` - deterministic random with probability
- [ ] `min(a, b)`, `max(a, b)`, `abs(x)` - math functions
- [ ] `clamp(x, lo, hi)` - clamp value
- [ ] `get(path_string, default)` - safe nested lookup

### 2.4 Condition Context
- [ ] Provide time variables (day, slot, time_hhmm, weekday)
- [ ] Provide location variables (id, zone, privacy)
- [ ] Provide node.id and turn counter
- [ ] Provide characters and present lists
- [ ] Provide meters namespace (meters.char.meter)
- [ ] Provide flags namespace (flags.flag_id)
- [ ] Provide modifiers namespace (modifiers.char_id)
- [ ] Provide inventory namespace (inventory.char.category.item)
- [ ] Provide clothing namespace (clothing.char.outfit, clothing.char.items.item)
- [ ] Provide gates namespace (gates.char.gate_id)
- [ ] Provide arcs namespace (arcs.arc_id.stage, arcs.arc_id.history)
- [ ] Provide discovered namespace (zones, locations)
- [ ] Provide unlocked namespace (endings, actions)

---

## 3. Meters System

### 3.1 Meter Definition & Loading
- [ ] Load player meters from `meters.player`
- [ ] Load NPC template meters from `meters.template`
- [ ] Apply template meters to all NPCs
- [ ] Allow NPC-specific meter overrides
- [ ] Validate min < max
- [ ] Validate default within [min, max]
- [ ] Parse threshold labels (non-overlapping, ordered)
- [ ] Load visibility settings (visible, hidden_until)
- [ ] Load decay settings (decay_per_day, decay_per_slot)
- [ ] Load delta_cap_per_turn

### 3.2 Meter Operations
- [ ] Apply meter_change effects (add, subtract, set, multiply, divide)
- [ ] Respect min/max bounds when respect_caps=true
- [ ] Apply delta_cap_per_turn when cap_per_turn=true
- [ ] Apply decay_per_day on day rollover
- [ ] Apply decay_per_slot on slot change
- [ ] Expose meter values in condition context
- [ ] Support meter format hints (integer, percent, currency)

---

## 4. Flags System

### 4.1 Flag Definition & Loading
- [ ] Load flags with type (bool, number, string)
- [ ] Validate default matches type
- [ ] Load visibility settings (visible, reveal_when)
- [ ] Load allowed_values for validation
- [ ] Initialize all flags with default values

### 4.2 Flag Operations
- [ ] Apply flag_set effects
- [ ] Validate value against allowed_values
- [ ] Expose flags in condition context
- [ ] Support flag visibility rules

---

## 5. Time & Calendar System

### 5.1 Time Configuration
- [ ] Load time categories (named duration mappings)
- [ ] Load time defaults (conversation, choice, movement, default, cap_per_visit)
- [ ] Load calendar settings (week_days, start_day)
- [ ] Load slots_enabled flag
- [ ] Load slot_windows if slots enabled
- [ ] Validate slot windows non-overlapping

### 5.2 Time Resolution
- [ ] Priority 1: Explicit time_cost override
- [ ] Priority 2: time_category override
- [ ] Priority 3: Contextual fallback (choice/action/movement defaults)
- [ ] Priority 4: Node-level time_behavior override
- [ ] Priority 5: Global time.defaults

### 5.3 Time Modifiers
- [ ] Collect all active modifier time_multiplier values
- [ ] Stack multipliers multiplicatively
- [ ] Clamp final multiplier to [0.5, 2.0]
- [ ] Apply modifiers to conversation turns
- [ ] Apply modifiers to choices and actions
- [ ] Apply modifiers to local movement
- [ ] Apply modifiers to zone travel ONLY if method.active=true
- [ ] Round result to nearest minute

### 5.4 Visit Cap
- [ ] Track time_spent_in_node per visit
- [ ] Apply cap_per_visit to conversation and default actions
- [ ] Bypass cap for explicit choice/action time costs
- [ ] Reset cap on node transition

### 5.5 Time Advancement
- [ ] Add resolved minutes to current_minutes
- [ ] Recalculate HH:MM format
- [ ] Derive active slot from current_minutes
- [ ] Handle day rollover at 1440 minutes
- [ ] Increment day counter on rollover
- [ ] Update weekday on rollover
- [ ] Trigger day-end effects before normalization
- [ ] Trigger day-start effects after normalization

### 5.6 Zone Travel Time
- [ ] Calculate time from distance * time_cost (if time_cost set)
- [ ] Calculate time from (distance / speed) * 60 (if speed set)
- [ ] Calculate time from distance * category_table[category] (if category set)

---

## 6. Economy System

### 6.1 Economy Configuration
- [ ] Load economy.enabled flag
- [ ] Load starting_money, max_money, currency_name, currency_symbol
- [ ] Auto-generate money meter when enabled
- [ ] Disable purchase mechanics when disabled

### 6.2 Economy Operations
- [ ] Validate sufficient funds for purchases
- [ ] Deduct money on purchase
- [ ] Add money on sale
- [ ] Respect max_money cap
- [ ] Apply shop multiplier_sell and multiplier_buy

---

## 7. Items System

### 7.1 Item Definition & Loading
- [ ] Load item definitions with all properties
- [ ] Validate unique item IDs
- [ ] Load item value, stackable, droppable flags
- [ ] Load consumable, can_give flags
- [ ] Load lock conditions (locked, when/when_all/when_any)
- [ ] Load effects (on_get, on_lost, on_use, on_give)

### 7.2 Item Operations
- [ ] Add items to inventory (inventory_add)
- [ ] Remove items from inventory (inventory_remove)
- [ ] Take items from location (inventory_take)
- [ ] Drop items at location (inventory_drop)
- [ ] Give items between characters (inventory_give)
- [ ] Consume items (apply on_use effects, decrement count)
- [ ] Trigger on_get effects when acquired
- [ ] Trigger on_lost effects when removed
- [ ] Trigger on_give effects when gifted

---

## 8. Clothing System

### 8.1 Wardrobe Definition & Loading
- [ ] Load wardrobe.slots ordered list
- [ ] Load clothing items with occupies and conceals
- [ ] Load clothing look descriptions per condition
- [ ] Load can_open flag
- [ ] Load outfit definitions with items mapping
- [ ] Load grant_items flag for outfits
- [ ] Load lock conditions for clothing and outfits
- [ ] Load effects (on_get, on_lost, on_put_on, on_take_off)

### 8.2 Clothing Operations
- [ ] Put on clothing item (clothing_put_on)
- [ ] Take off clothing item (clothing_take_off)
- [ ] Set clothing condition (clothing_state: intact/opened/displaced/removed)
- [ ] Set slot condition (clothing_slot_state)
- [ ] Put on outfit (outfit_put_on) - apply all items
- [ ] Take off outfit (outfit_take_off) - remove all items
- [ ] Track clothing condition per character
- [ ] Enforce slot occupancy rules
- [ ] Handle multi-slot items (e.g., dresses)

### 8.3 Clothing Queries
- [ ] `wears(char, item)` - check wearing (condition != removed)
- [ ] `wears_outfit(char, outfit)` - check all items worn
- [ ] `has_clothing(char, item)` - check inventory
- [ ] `has_outfit(char, outfit)` - check outfit in inventory
- [ ] `knows_outfit(char, outfit)` - check outfit recipe known
- [ ] `can_wear_outfit(char, outfit)` - check all items available

---

## 9. Shopping System

### 9.1 Shop Definition & Loading
- [ ] Load shop definitions attached to locations or characters
- [ ] Load shop inventory (items, clothing, outfits)
- [ ] Load shop conditions (when, can_buy, can_sell)
- [ ] Load shop multipliers (multiplier_sell, multiplier_buy)
- [ ] Load resell flag

### 9.2 Shop Operations
- [ ] Validate shop is open (when condition)
- [ ] Purchase items (inventory_purchase effect)
- [ ] Sell items (inventory_sell effect)
- [ ] Calculate final price with multipliers
- [ ] Deduct money from buyer
- [ ] Add money to seller
- [ ] Update shop inventory
- [ ] Handle resell logic (add sold items back to shop if resell=true)

---

## 10. Locations & Zones

### 10.1 Zone & Location Loading
- [ ] Load zone definitions with name, summary, privacy
- [ ] Load location definitions within zones
- [ ] Load access rules (discovered, hidden_until_discovered, discovered_when)
- [ ] Load lock conditions (locked, when/when_all/when_any)
- [ ] Load zone connections (to, exceptions, methods, distance)
- [ ] Load location connections (to, direction, locked, when/when_all/when_any)
- [ ] Load zone entrances and exits lists
- [ ] Load location inventory
- [ ] Load zone/location time_cost or time_category

### 10.2 Movement Operations
- [ ] Move in direction (move effect) - find connection by direction
- [ ] Move to location within zone (move_to effect)
- [ ] Travel between zones (travel_to effect)
- [ ] Validate location/zone access (not locked, conditions met)
- [ ] Validate connection access (not locked, conditions met)
- [ ] Check NPC willingness to follow (movement.willing_zones, willing_locations)
- [ ] Calculate movement time (local vs zone travel)
- [ ] Update state.current_location
- [ ] Handle entrances/exits if movement.use_entry_exit=true

### 10.3 Discovery
- [ ] Mark zones discovered when entering
- [ ] Mark locations discovered when entering
- [ ] Evaluate discovered_when conditions
- [ ] Update state.discovered_zones
- [ ] Update state.discovered_locations
- [ ] Hide undiscovered zones/locations if hidden_until_discovered=true

---

## 11. Characters System

### 11.1 Character Definition & Loading
- [ ] Load character definitions (id, name, age, gender, pronouns)
- [ ] Load personality, appearance, dialogue_style
- [ ] Apply template meters to NPCs
- [ ] Load character-specific meter overrides
- [ ] Load gates definitions
- [ ] Load character wardrobe overrides
- [ ] Load initial clothing state (outfit, items)
- [ ] Load character inventory
- [ ] Load character shop (if merchant)
- [ ] Load schedule rules
- [ ] Load movement willingness rules (willing_zones, willing_locations)
- [ ] Load lock conditions for characters

### 11.2 Character Gates
- [ ] Evaluate gate conditions (when/when_all/when_any)
- [ ] Store active gates per character
- [ ] Provide acceptance text when gate active
- [ ] Provide refusal text when gate inactive
- [ ] Expose gates in condition context (gates.char.gate_id)
- [ ] Pass gate info to Writer via character cards
- [ ] Pass gate info to Checker for enforcement

### 11.3 Character Presence
- [ ] Evaluate character schedules each turn
- [ ] Update state.present_characters list
- [ ] Check schedule conditions (when/when_all/when_any)
- [ ] Match schedule location against current location
- [ ] Expose present characters in condition context

---

## 12. Effects System

### 12.1 Effect Execution
- [ ] Validate effect type is recognized
- [ ] Evaluate effect guard conditions (when/when_all/when_any)
- [ ] Skip effects when guard is false
- [ ] Apply effects in order
- [ ] Validate effect targets exist
- [ ] Log warnings for invalid effects

### 12.2 Effect Types - State Changes
- [ ] meter_change (add, subtract, set, multiply, divide)
- [ ] flag_set

### 12.3 Effect Types - Inventory
- [ ] inventory_add
- [ ] inventory_remove
- [ ] inventory_take
- [ ] inventory_drop
- [ ] inventory_give

### 12.4 Effect Types - Shopping
- [ ] inventory_purchase
- [ ] inventory_sell

### 12.5 Effect Types - Clothing
- [ ] clothing_put_on
- [ ] clothing_take_off
- [ ] clothing_state
- [ ] clothing_slot_state
- [ ] outfit_put_on
- [ ] outfit_take_off

### 12.6 Effect Types - Movement & Time
- [ ] move (direction-based)
- [ ] move_to (location within zone)
- [ ] travel_to (between zones)
- [ ] advance_time

### 12.7 Effect Types - Flow Control
- [ ] goto (force node transition)
- [ ] conditional (then/otherwise branches)
- [ ] random (weighted choices)

### 12.8 Effect Types - Modifiers
- [ ] apply_modifier
- [ ] remove_modifier

### 12.9 Effect Types - Unlocks
- [ ] unlock (items, clothing, outfits, zones, locations, actions, endings)
- [ ] lock (items, clothing, outfits, zones, locations, actions, endings)

---

## 13. Modifiers System

### 13.1 Modifier Definition & Loading
- [ ] Load modifier definitions with id, group, priority
- [ ] Load activation conditions (when/when_all/when_any)
- [ ] Load duration defaults
- [ ] Load mixins, dialogue_style overrides
- [ ] Load gate constraints (disallow_gates, allow_gates)
- [ ] Load meter clamps (clamp_meters)
- [ ] Load time_multiplier
- [ ] Load hooks (on_enter, on_exit effects)
- [ ] Load stacking rules per group (highest, lowest, all)

### 13.2 Modifier Auto-Activation
- [ ] Evaluate modifier when conditions each turn
- [ ] Activate modifiers when conditions become true
- [ ] Deactivate modifiers when conditions become false
- [ ] Trigger on_enter effects when activated
- [ ] Trigger on_exit effects when deactivated

### 13.3 Modifier Manual Application
- [ ] Apply modifier via apply_modifier effect
- [ ] Set duration from effect or modifier default
- [ ] Remove modifier via remove_modifier effect

### 13.4 Modifier Stacking
- [ ] Sort modifiers by priority within group
- [ ] Apply stacking rules (highest, lowest, all)
- [ ] Remove conflicting modifiers based on stacking rule

### 13.5 Modifier Duration
- [ ] Track modifier duration in minutes
- [ ] Tick duration down when time advances
- [ ] Remove expired modifiers
- [ ] Trigger on_exit effects on expiration

### 13.6 Modifier Effects
- [ ] Apply disallow_gates (disable gates)
- [ ] Apply allow_gates (force gates)
- [ ] Apply clamp_meters (enforce temporary bounds)
- [ ] Apply time_multiplier to time costs
- [ ] Expose active modifiers in condition context

---

## 14. Actions System

### 14.1 Action Definition & Loading
- [ ] Load global action definitions
- [ ] Load action unlock conditions (when/when_all/when_any)
- [ ] Load action effects
- [ ] Load action categories

### 14.2 Action Availability
- [ ] Check action is unlocked
- [ ] Evaluate action when conditions
- [ ] Include available actions in choices list
- [ ] Apply action effects when chosen

---

## 15. Nodes System

### 15.1 Node Definition & Loading
- [ ] Load node definitions (id, type, beats)
- [ ] Load node types (scene, hub, ending)
- [ ] Load node entry_effects
- [ ] Load node choices with conditions
- [ ] Load node transitions with conditions
- [ ] Load node time_behavior overrides
- [ ] Load node preconditions

### 15.2 Node Validation
- [ ] Check current node is not ENDING (at turn start)
- [ ] Verify node exists in game definition
- [ ] Validate node preconditions before entering

### 15.3 Node Transitions
- [ ] Check for forced goto effects
- [ ] Evaluate auto-transition conditions
- [ ] Apply node entry_effects on entering new node
- [ ] Update state.current_node
- [ ] Add to state.nodes_history

### 15.4 Node Choices
- [ ] Load choices from current node
- [ ] Filter choices by conditions (when/when_all/when_any)
- [ ] Check choice preconditions
- [ ] Apply choice effects when selected
- [ ] Apply choice transitions when selected
- [ ] Resolve choice time_category or time_cost

---

## 16. Events System

### 16.1 Event Definition & Loading
- [ ] Load event definitions (id, type, trigger)
- [ ] Load event types (random, conditional, scheduled)
- [ ] Load trigger conditions (when/when_all/when_any)
- [ ] Load event probability weights
- [ ] Load event cooldowns
- [ ] Load event effects (on_enter, on_exit)
- [ ] Load event choices
- [ ] Load event narrative beats

### 16.2 Event Triggering
- [ ] Check event cooldowns (skip if on cooldown)
- [ ] Evaluate trigger conditions
- [ ] Add random events to weighted pool
- [ ] Trigger conditional events immediately if conditions met
- [ ] Select one random event from pool using weights and RNG
- [ ] Apply event on_enter effects
- [ ] Set event cooldowns
- [ ] Collect event choices
- [ ] Collect event narrative beats

### 16.3 Event Cooldowns
- [ ] Track cooldowns per event
- [ ] Decrement cooldowns each turn
- [ ] Remove expired cooldowns

---

## 17. Arcs & Milestones System

### 17.1 Arc Definition & Loading
- [ ] Load arc definitions (id, stages)
- [ ] Load stage definitions within arcs
- [ ] Load stage conditions (when/when_all/when_any)
- [ ] Load stage effects (on_enter, on_exit)
- [ ] Initialize arc state (stage, history)

### 17.2 Arc Progression
- [ ] For each arc, get current stage
- [ ] Evaluate stage conditions
- [ ] Detect stage progression (condition true and stage is new)
- [ ] Apply previous stage on_exit effects
- [ ] Apply new stage on_enter effects
- [ ] Update state.arcs[arc_id].stage
- [ ] Add stage to state.arcs[arc_id].history
- [ ] Track milestones reached

### 17.3 Arc Queries
- [ ] Expose arc stage in condition context (arcs.arc_id.stage)
- [ ] Expose arc history in condition context (arcs.arc_id.history)
- [ ] Support "stage in history" checks

---

## 18. Turn Processing Algorithm

### 18.1 Step 1: Initialize Turn Context
- [ ] Increment turn counter
- [ ] Generate deterministic RNG seed (base_seed + turn)
- [ ] Create RNG instance
- [ ] Capture current node
- [ ] Create state snapshot

### 18.2 Step 2: Validate Current Node
- [ ] Check node is not ENDING
- [ ] Verify node exists

### 18.3 Step 3: Update Character Presence
- [ ] Evaluate character schedules
- [ ] Update state.present_characters

### 18.4 Step 4: Evaluate Character Gates
- [ ] For each character, evaluate all gates
- [ ] Store active gates in context
- [ ] Add gates to DSL context

### 18.5 Step 5: Format Player Action
- [ ] Format action based on type (say, do, choice, move, etc.)
- [ ] Resolve references (choice IDs, character names, item names)
- [ ] Create action summary

### 18.6 Step 6: Execute Action Effects
- [ ] For choice actions: find and apply choice effects
- [ ] For deterministic actions: execute corresponding effects
- [ ] Resolve time category for action

### 18.7 Step 7: Process Triggered Events
- [ ] Check cooldowns
- [ ] Evaluate trigger conditions
- [ ] Build weighted random event pool
- [ ] Select and trigger events
- [ ] Apply event effects
- [ ] Collect event choices and narratives

### 18.8 Step 8: Check and Apply Node Transitions
- [ ] Check for forced goto transitions
- [ ] Evaluate auto-transition conditions
- [ ] Apply node transitions
- [ ] Update current node and history

### 18.9 Step 9: Update Active Modifiers
- [ ] Evaluate modifier auto-activation conditions
- [ ] Activate/deactivate modifiers based on conditions
- [ ] Apply stacking rules

### 18.10 Step 10: Update Discoveries
- [ ] Evaluate discovered_when conditions for zones/locations
- [ ] Add to discovered sets
- [ ] Check for action/ending unlocks

### 18.11 Step 11: Advance Time
- [ ] Resolve time cost (category → minutes, apply modifiers)
- [ ] Add minutes to current_minutes
- [ ] Handle day/slot rollover
- [ ] Tick modifier durations
- [ ] Remove expired modifiers
- [ ] Trigger on_exit effects for expired modifiers
- [ ] Apply meter decay (per_day, per_slot)
- [ ] Decrement event cooldowns

### 18.12 Step 12: Process Arc Progression
- [ ] For each arc, check stage conditions
- [ ] Detect and apply stage progressions
- [ ] Trigger stage effects (on_exit, on_enter)
- [ ] Update arc state and history
- [ ] Track milestones reached

### 18.13 Step 13: Build Available Choices
- [ ] Collect node choices (filtered by conditions)
- [ ] Collect event choices
- [ ] Generate movement choices
- [ ] Add unlocked global actions
- [ ] Return choice list with metadata

### 18.14 Step 14: Build State Summary
- [ ] Collect current meters
- [ ] Collect active flags
- [ ] Collect inventory counts
- [ ] Collect clothing state
- [ ] Format time information
- [ ] List present characters
- [ ] List active modifiers
- [ ] Return state summary

### 18.15 Step 15: Persist State
- [ ] Update state.updated_at timestamp
- [ ] Persist state via StateManager

---

## 19. AI Integration

### 19.1 AI Action Flow (Conditional)
- [ ] Detect AI actions (say, do, choice without skip_ai)
- [ ] Build AI context (character cards, location, history)
- [ ] Call Writer model to generate narrative
- [ ] Stream prose generation
- [ ] Call Checker model to extract state changes
- [ ] Parse Checker JSON deltas
- [ ] Apply Checker deltas as effects
- [ ] Merge AI-generated state changes into pipeline

### 19.2 Character Cards
- [ ] Build character cards for present NPCs
- [ ] Include appearance, meters, gates info
- [ ] Include active modifiers
- [ ] Include clothing state
- [ ] Pass cards to Writer

### 19.3 Writer Contract
- [ ] Provide node type, beats, POV, tense
- [ ] Provide location and time context
- [ ] Provide character cards
- [ ] Provide recent history
- [ ] Provide action summary
- [ ] Request prose generation

### 19.4 Checker Contract
- [ ] Provide Writer narrative output
- [ ] Provide current state snapshot
- [ ] Provide validation rules (gates, consent, bounds)
- [ ] Request JSON deltas
- [ ] Validate Checker output format
- [ ] Reject invalid deltas

---

## 20. State Management

### 20.1 State Initialization
- [ ] Initialize meters with defaults
- [ ] Initialize flags with defaults
- [ ] Initialize inventory as empty
- [ ] Initialize clothing with starting outfit
- [ ] Initialize time (day, current_minutes)
- [ ] Initialize location (start location)
- [ ] Initialize node (start node)
- [ ] Initialize arcs (stage, history)
- [ ] Initialize modifiers as empty
- [ ] Initialize present_characters as empty
- [ ] Initialize discovered sets (zones, locations)
- [ ] Initialize unlocked lists (actions, endings)

### 20.2 State Persistence
- [ ] Save state after each turn
- [ ] Load state for existing sessions
- [ ] Support state snapshots for rollback
- [ ] Track state.updated_at timestamp

### 20.3 State Queries
- [ ] Query meters by character and meter ID
- [ ] Query flags by flag ID
- [ ] Query inventory by character and item ID
- [ ] Query clothing by character and item ID
- [ ] Query active modifiers by character
- [ ] Query present characters
- [ ] Query discovered zones/locations
- [ ] Query unlocked actions/endings
- [ ] Query arc stage and history

---

## 21. Determinism & RNG

### 21.1 Deterministic Execution
- [ ] Use seeded RNG for all randomness
- [ ] Generate RNG seed from game_id + run_id + turn
- [ ] Produce identical results for same inputs
- [ ] Support replay with same seed

### 21.2 Random Event Selection
- [ ] Use weighted random selection for events
- [ ] Use RNG for event probability
- [ ] Use RNG for random effects

---

## 22. Error Handling

### 22.1 Validation Errors
- [ ] Reject actions on ENDING nodes
- [ ] Log warnings for invalid effects
- [ ] Log warnings for unknown condition variables
- [ ] Log warnings for type errors in expressions
- [ ] Log warnings for division by zero

### 22.2 Graceful Degradation
- [ ] Skip invalid effects (don't crash)
- [ ] Skip effects with failed guards (don't log warning)
- [ ] Continue execution on non-critical errors
- [ ] Provide clear error messages

---

## 23. API Contracts

### 23.1 Start Session Endpoint
- [ ] Accept game_id
- [ ] Initialize new game state
- [ ] Return initial turn result with choices
- [ ] Support streaming (optional)

### 23.2 Process Action Endpoint
- [ ] Accept session_id and action payload
- [ ] Load session state
- [ ] Execute turn processing pipeline
- [ ] Return turn result with narrative and choices
- [ ] Support streaming (optional)

### 23.3 Turn Result Schema
- [ ] Include narrative text
- [ ] Include action summary
- [ ] Include available choices
- [ ] Include state summary (meters, flags, time, location, etc.)
- [ ] Include events fired
- [ ] Include milestones reached
- [ ] Include errors/warnings

---

## 24. Performance & Optimization

### 24.1 Caching
- [ ] Cache condition evaluator context per turn
- [ ] Cache character cards during turn
- [ ] Index nodes for O(1) lookup

### 24.2 Optimization
- [ ] Minimize redundant condition evaluations
- [ ] Batch state updates where possible
- [ ] Lazy-load game definitions

---

## 25. Testing Requirements

### 25.1 Unit Tests
- [ ] Test each effect type in isolation
- [ ] Test each DSL function
- [ ] Test each turn processing step
- [ ] Test modifier stacking rules
- [ ] Test time advancement edge cases
- [ ] Test state validation

### 25.2 Integration Tests
- [ ] Test full turn execution with real games
- [ ] Test event triggering and cooldowns
- [ ] Test arc progression
- [ ] Test modifier expiration
- [ ] Test shopping transactions
- [ ] Test clothing changes
- [ ] Test movement and travel

### 25.3 Regression Tests
- [ ] Golden file tests for deterministic actions
- [ ] Snapshot tests for state evolution
- [ ] Performance benchmarks

---

## Completion Status

**Total Items:** ~400+ checkpoints
**Completed:** ___
**In Progress:** ___
**Blocked:** ___
**Not Started:** ___

---

## Notes

- Use this checklist to verify each functional area systematically
- Check off items as they are verified and tested
- Document any deviations or issues found
- Track blocked items and their dependencies
- Update completion status regularly
