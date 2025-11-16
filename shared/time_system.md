# PlotPlay Time System — Comprehensive Proposal

## 1. Core Philosophy

The time system must satisfy four major principles:

1. **Unified logic.**  
The engine has a single, consistent method of advancing time, regardless of user input, narrative structure, or game mode.

2. **Predictability for authors.**  
Authors need simple, reliable tools to control pacing without micromanaging minutes everywhere.

3. **Natural narrative feel.**  
Simple conversations should not advance time like major activities. Travel, significant actions, and long events should consume realistic amounts of time.

4. **AI-compatible.**  
Writer/Checker interaction should not create unpredictable time skips. Any AI-generated hinting must remain optional and clamped by rules.

---

## 2. Unified Time Model

### 2.1 Engine always tracks time in minutes

There is one atomic time unit: minutes since the start of the day.

Internally:

```yaml
time.current_minutes: int (0–1439)
time.day: int
time.weekday: enum/string (optional)
```

All actions, choices, movements, and modifiers reduce to adding minutes to this value.

### 2.2 Slots become a UI/semantic layer

Slots are always derived from `current_minutes` and predefined window ranges:

```yaml
slot_windows:
  morning: { start: "06:00", end: "11:59" }
  afternoon: { start: "12:00", end: "17:59" }
  evening: { start: "18:00", end: "21:59" }
  night: { start: "22:00", end: "05:59" }
```

- “Clock mode” UI: shows HH:MM only
- “Slot mode” UI: shows HH:MM + active slot
- Engine behavior is identical in both.

---

## 3. Action Categories (Time Cost Model)

### 3.1 Categories define pacing

Instead of hardcoding minutes per action, the game defines **named time categories** 
and also provides **default time-related values for nodes**:

```yaml
time:
  categories:
    instant: 0          # dialogue, brief remarks
    trivial: 2          # quick interactions
    quick: 5            # picking items, short tasks
    standard: 15        # default gameplay activity
    significant: 30     # work, studying, moderate tasks
    major: 60           # explicit time skip events
  defaults:                          # Default categories for different actions
    conversation:     "instant"        # Default duration for chat turns
    choice:           "quick"          # Default duration for choices
    movement:         "standard"       # Default duration for local movement
    default:          "trivial"        # Fallback for unspecified actions
    cap_per_visit: 30                  # Max minutes accumulated in this node visit

```

Each category maps to a minute value.

The table is configurable per game.

### 3.2 How categories are used

Every time an action happens, the engine resolves a category using the following priority:

1. **Explicit override.**  
A choice/action/movement specifies a minute value: `time_cost: 20`

2. **Category override.**  
A choice/action/movement specifies a category: `time_category: "quick"`

3. **Contextual fallback.**  
The engine picks a category based on the context:
   - Context-level (choice, action, etc.) setting (category or explicit `time_cost` in minutes)
   - Node-level override (category or explicit `time_cost` in minutes)
   - Global default:
     - Chat turn → `time.defaults.conversation`
     - Local movement → `time.defaults.movement`
     - Travel → category based on travel method
     - Global default: `"time.defaults.default"`

---

## 4. Time Advancement Pipeline

Every turn, the engine performs:

1. Determine a context type based on deterministic action or AI suggestion:
    - chat-only
    - choice selected
    - global action
    - movement inside zone
    - travel between zones

2. Determine effective category (per rules of Section 3)

3. Convert category to base minutes

4. Apply modifiers (Section 8): multipliers, caps

5. Add derived minutes to time.current_minutes

6. Recalculate:
   - HH:MM
   - active slot
   - day/week rollover


This guarantees a single, predictable, extensible method of updating time, no matter where the turn originates.

---

## 5. Conversations & Dialogue Logic


### 5.1 Chat turns

A chat turn is defined as:

- Player enters text
- Writer responds
- No choice selected
- No movement/action triggered

Time cost comes from local node settings or global defaults.  
Typical values: 0–2 minutes.  
This fixes chat spam consuming entire time slots.

### 5.2 Node-level overrides

Nodes may define the time behavior:
```yaml

  nodes:
    - id: <node_id>
      ...
      time_behavior:                      # Optional override block
        conversation: "instant"           # Override for this node
        choice: "quick"                   # Override for this node
        default: "trivial"                # Fallback for unspecified actions
        cap_per_visit: 30                 # Max minutes accumulated in this node visit
```

### 5.3 Visit cap

Prevents infinite chat loops from consuming abnormal time:

```python
minutes = min(action_cost, max(0, cap - time_spent_in_node))
```

This preserves pacing while allowing natural dialogue in scenes.
- The cap is per-node per-visit, and resets on entering a new node.
- The visit cap applies only to conversation turns and default actions.
- Explicit choice/action time costs bypass the cap, as they represent significant narrative moments that should consume their full time.

---

## 6. Choices & Actions (`choices[]`, `dynamic_choices[]`, `actions[]`)

Every choice/action supports:

```yaml

time_category: "quick"
# or
time_cost: 25
```

If unspecified:
- Use node’s `time_behavior.choice`
- else global default `time.defaults.choice`

Example:
```yaml
choices:
  - id: "kiss"
    prompt: "Kiss her"
    time_category: "significant"
```

---

## 7. Movement & Travel


### 7.1 Local movement between locations inside the same zone

Local movement uses fixed time for movement between locations defined in the `time.defaults.movement`.
Authors can override this parameter per zone.

```yaml
zones:
  - id: <zone_id>
    ...
    time_cost: 10   # OPTIONAL. Minutes to travel between locations in this zone
    time_category: "standard" # OPTIONAL. Time category for travel between locations in this zone
```
> Note: exactly one of `time_cost` or `time_category` may be set per zone.

### 7.2 Zone travel

Each travel method defines either a `time_cost` per base unit (e,g, 1 km, 1 mile, etc.) or a `speed`, i.e., base units per hour:

```yaml
movement:
  methods:
    walk:
      active: true   # Means methoid is active and perormed by player, so time modifiers affect time cost
      time_cost: 20  # per base unit, i.e. 20 minutes per km
    run:
      active: true
      category: "quick"  # per base unit, taken from the category  
    bus:
      active: false  # Means methoid is passive, so time modifiers do not affect time cost
      speed: 50      # base units per hour, i.e. 50 km per hour 
    train:
      active: false
      speed: 100  
```
> Note: exactly one of `time_cost` / `speed` / `category` is required per method.

Travel time calculation:

```python
minutes = distance * time_cost
# OR
minutes = (distance / speed) * 60
```

Supports variable pacing depending on transport and world design.

---

## 8. Time Effects and Modifiers (Buffs/Debuffs)

The player may have active effects or modifiers that alter time cost by implementing the `time_modifier` parameter:

```python
energetic -> time_multiplier: 0.9
sleepy    -> time_multiplier: 1.2
```

Mechanics:
1. All active modifiers stack multiplicatively.
2. The final multiplier must be clamped to reasonable bounds: `0.5 <= multiplier <= 2.0`
3. The result is rounded to the nearest minute.

Modifiers apply to:
- Conversation turns
- Choices and actions
- Local movement
- Inter-zone travel if travel method is `active`, i.e., performed by the characters themselves.

Use cases:
- Fatigue slows actions
- Caffeine speeds tasks
- Magic or tech items alter time efficiency
- Weather or terrain affects movement/travel cost

---

## 9. AI Narrative Hinting

AI-generated text **must NOT directly dictate** exact minutes.  
But it **may suggest** time categories or qualitative hints like:
- “This takes a while…”
- “Time passes quickly…”
- “After a long study session…”

Instead of asking Writer to output metadata, use Checker:

- Checker scans narrative for time-related phrases
- Checker proposes:
```yaml
time_hint:
    category: "significant"
    confidence: 0.82
```
- Engine applies **only if**:
    - the current context allows it
    - no explicit author category exists
    - within the node visit cap

If the hint category conflicts with author-defined rules, the author wins.  
The hint is advisory, not authoritative.

---

## 10. Authoring Summary (Mental Model)

Authors now think in terms of:

- What type of action is this? → Assign a category
- Does this scene need conversational pacing? → Override conversation_category or apply a cap
- Does this choice represent a long activity? → Set significant or explicit minutes
- Does travel feel too fast/slow? → Adjust travel method categories
- Do I want fatigue or buffs to affect pacing? → Use modifiers

This eliminates the need to juggle `turns`, `slots`, or `actions per slot`.  
Everything reduces to a single conceptual layer: action → category → minutes.

---

## 11. Engine Implementation Notes


### 11.1 Time calculation pseudo-pipeline
```python
def advance_time(context):
    category = resolve_category(context)
    minutes = category_table[category]

    # apply explicit minutes override
    if context.explicit_minutes is not None:
        minutes = context.explicit_minutes

    # apply modifiers
    for m in active_modifiers:
        minutes *= m.time_multiplier

    # clamp and round
    minutes = clamp(round(minutes), 0, MAX_TIME_PER_TURN)

    # node visit cap
    if current_node.cap_per_visit and time_in_node + minutes > cap:
        minutes = max(0, cap - time_in_node)

    time.current_minutes += minutes
    normalize_day_slot()
```

### 11.2 Normalizing the clock
```python
  if time.current_minutes >= 1440:
      # Trigger day rollover effects BEFORE normalizing
      trigger_day_end_effects()

      # Normalize time
      time.current_minutes -= 1440
      time.day += 1
      time.weekday = next_day_of_week

      # Trigger new day effects AFTER normalizing
      trigger_day_start_effects()
```

### 11.3 Determining active slot
```python
for slot, window in slot_windows:
    if window.start <= HH:MM <= window.end:
        time.current_slot = slot
```

---

## 12. Benefits & Outcomes
🔥 1. Zero chat inflation.  
Simple chatter costs 0–2 minutes.

🔥 2. Travel & movement are naturally balanced.  
Distance × category cost = smooth pacing.

🔥 3. Everything uses the same formula.  
No exceptions, no special handling.

🔥 4. AI safely enhances pacing.  
Optional hinting without losing control.

🔥 5. Modifiers add depth.  
Gameplay systems (fatigue, mood, buffs) interact with pacing.

🔥 6. Simpler spec, simpler engine, richer gameplay.  
A rare combination of simplicity and expressive power.
