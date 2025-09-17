# PlotPlay Specification v3

PlotPlay is an AI-driven text adventure engine that blends **pre-authored branching nodes** with **AI-generated prose**. The system is designed for replayable interactive fiction with mature/NSFW support, structured progression, and clearly defined endings.

---

## Scope of this Document
- Human-readable design rules for authors and developers  
- Formal structure of game definition files (YAML)  
- Machine-readable schemas (see `/spec/` folder)  
- Contracts for Writer and Checker AI models  

---

## Key Features
- **Hybrid Narrative**: Nodes and AI prose work together; AI never “goes off-track” from authored structure.  
- **Character State System**: Per-character meters, flags, modifiers, clothing, and schedules drive behavior.  
- **Consent & Behavior Gates**: NPC responses depend on trust, attraction, arousal, boldness, corruption, and other thresholds.  
- **Dynamic World**: Locations, time, and random events create variety across playthroughs.  
- **Defined Endings**: All stories resolve at authored conclusion nodes, not endless sandbox play.  
- **AI Contracts**: Two-model architecture (Writer and Checker) ensures narrative quality and consistent state.  

---

## Design Philosophy
- **Player Agency**: Choices and freeform actions meaningfully affect characters, story, and outcomes.  
- **State Coherence**: Narrative always respects the current state (clothing, meters, location, presence).  
- **Progressive Intimacy**: Romantic and sexual content gated by consent mechanics, never bypassed.  
- **Author-First**: YAML and schemas keep content authoring deterministic, predictable, and safe.  

---

## Core Concepts

### State
Game state is the single source of truth. It includes:
- **Meters** — numeric values per player and NPC (trust, attraction, energy, etc.)  
- **Flags** — boolean or scalar values for progression (e.g. `emma_met`, `first_kiss`)  
- **Modifiers** — temporary or permanent effects (e.g. drunk, corrupted, aroused)  
- **Inventory** — items owned by the player or NPCs  
- **Clothing** — layered outfits with rules for removal, replacement, validation  
- **Location & Time** — hierarchical world, zones, locations, day/slot tracking  

### Character Cards
Generated dynamically each turn from state. They describe base appearance, outfit & clothing state, active modifiers, summarized meters (threshold labels), dialogue style, and current behavior gates. Cards are passed to the Writer as context each turn.

### Narrative Flow
- **Nodes** define authored story structure (scenes, interactive hubs, endings).  
- **Writer Model** produces freeform prose, respecting node type, state, and character cards.  
- **Checker Model** parses prose back into structured state deltas (meter changes, flags, clothing, etc.).  
- **Transitions** move the story between nodes, determined by authored conditions + Checker outputs.  

### Two-Model Architecture
- **Writer**: Expands on authored beats, generates dialogue and prose, stays within style/POV constraints.  
- **Checker**: Strict JSON output, detects state changes, validates against rules, enforces consent & hard boundaries.  

Both models run each turn; their outputs are merged into the game state.  

---

## 1. Game Configuration (`game.yaml`)

Below is the **manifest** for a game. It references all other files and defines global rules. The example is richly commented so authors understand each field at a glance.

```yaml
# ===============================
# Game Manifest (game.yaml)
# ===============================
game:
  id: "unique_game_id"        # Stable ID used by saves and tooling
  title: "Game Title"
  version: "1.0.0"
  spec_version: "3.1"          # REQUIRED: which spec this content targets
  author: "Author Name"
  content_rating: "explicit"   # all_ages | teen | mature | explicit
  tags: ["romance", "fantasy", "adventure"]

  narration:
    pov: "second"              # first | second | third
    tense: "present"           # past | present
    paragraphs: "2-3"           # target prose length per Writer turn
    token_budget: 350           # hard cap for Writer model
    checker_budget: 200         # hard cap for Checker model

  model_profiles:
    writer: "cheap"            # cheap | luxe | custom
    checker: "fast"            # fast | accurate | custom

  meters:
    player:
      health:   { min: 0, max: 100, default: 100, visible: true,  icon: "❤️" }
      energy:   { min: 0, max: 100, default: 100, visible: true,  icon: "⚡", decay_per_day: -20 }
      money:    { min: 0, max: 9999, default: 100, visible: true,  icon: "💰", format: "currency" }

    character_template:
      trust: {
        min: 0, max: 100, default: 0,
        thresholds: { stranger: [0,19], acquaintance: [20,39], friend: [40,69], close: [70,89], intimate: [90,100] }
      }
      attraction: {
        min: 0, max: 100, default: 0,
        thresholds: { none: [0,19], interested: [20,39], attracted: [40,69], infatuated: [70,89], in_love: [90,100] }
      }
      arousal: {
        min: 0, max: 100, default: 0,
        hidden_until: "meters.{character}.attraction >= 30"
      }
      corruption: {
        min: 0, max: 100, default: 0,
        hidden_until: "flags.corruption_revealed == true"
      }
      boldness: {
        min: 0, max: 100, default: 20,
        hidden_until: "meters.{character}.trust >= 40"
      }

  meter_interactions:
    - source: "{character}.arousal"
      target: "{character}.boldness"
      when: "source >= 60"
      effect: "target += 20 (temporary)"

    - source: "{character}.corruption"
      target: "{character}.trust"
      when: "source >= 60"
      effect: "trust requirement -20"

    - source: "player.energy"
      target: "all.arousal"
      when: "source < 30"
      effect: "max = 60"

  time:
    mode: "hybrid"                # slots | clock | hybrid
    slots: ["morning", "afternoon", "evening", "night"]
    actions_per_slot: 3
    auto_advance: true
    clock:
      minutes_per_day: 1440
      slot_windows:
        morning:   { start: "06:00", end: "11:59" }
        afternoon: { start: "12:00", end: "17:59" }
        evening:   { start: "18:00", end: "21:59" }
        night:     { start: "22:00", end: "05:59" }
    calendar:
      epoch: "2025-01-01"
      week_days: ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
      start_day_index: 2
      weeks_enabled: true
    start:
      day: 1
      slot: "morning"
      time: "08:30"

  difficulty:
    meter_caps: { default: [0, 100] }
    decay_multiplier: 1.0
    money_multiplier: 1.0
    hints: true

  save_system:
    auto_save: true
    slots: 10
    checkpoints: ["chapter_1_end", "chapter_2_end"]

  files:
  # REQUIRED files (must exist):
  characters.yaml   # Always required
  nodes.yaml        # Always required
  
  # OPTIONAL files (can be inline or separate):
  locations.yaml    # Can be inline in game.yaml
  items.yaml        # Can be inline at end of characters.yaml  
  events.yaml       # Can be inline at end of nodes.yaml
  milestones.yaml   # Can be inline in arcs.yaml

---

## 2. Time & Calendar Model

We support **three modes** to fit different game styles:

1. **slots** — simple day broken into named slots. Great for romance/slice-of-life pacing.
2. **clock** — minute-precise time. Useful for stealth/sim or travel-heavy games.
3. **hybrid** — both: minutes tick, but narrative/UI still uses slots. Schedules can reference either.

### Authoring Guidelines
- Use **hybrid** by default: it preserves slot-based design while letting travel/events consume minutes.
- Map each slot to a **time window**. The engine derives the active slot from the clock.
- Expose **week** semantics for schedules (e.g., Friday night parties). Use `calendar.weeks_enabled: true` and `week_days`.
- For schedules/events, allow conditions like:
  - `time.slot == 'evening'`
  - `time.hhmm in ['22:00'..'02:00']` (engine handles wrap-around)
  - `time.weekday in ['friday','saturday']`
  - `time.day >= 7` (absolute narrative day)

```yaml
time:
  mode: "slots"  # CHOOSE ONE: slots | clock | hybrid
  
  # FOR SLOTS MODE (simple, recommended):
  slots: ["morning", "noon", "afternoon", "evening", "night", "late_night"]
  actions_per_slot: 3    # After N actions, auto-advance slot
  
  # FOR HYBRID MODE (slots + minutes):
  # Slots still exist but time tracks minutes within them
  clock:
    minutes_per_slot: {"morning": 240, "noon": 180, ...}
    
  # State representation differs by mode:
  # Slots mode: {day: 3, slot: "evening"}
  # Hybrid mode: {day: 3, slot: "evening", time_hhmm: "19:30"}```
```

### Runtime State (time-related excerpt)

```yaml
state:
  day: 3                 # narrative day counter
  slot: "afternoon"       # derived from the clock window
  time_hhmm: "14:35"      # HH:MM, 24h format (clock/hybrid)
  weekday: "wednesday"    # derived from calendar
```

### Backwards Compatibility
- Games written for pure slot-based play still work: omit `clock` and `calendar`, set `mode: slots`.
- Existing content that used only `day` + `slot` will load unchanged; clock fields are optional.

---

## 3. Character Definitions (`characters.yaml`)

Each character entry defines identity, hard safety facts, meters (overrides and additions), personality/background for context, appearance, wardrobe, behaviors/consent gates, dialogue profile, schedule, and movement preferences.

> **Hard rule:** every character must be an adult. `age >= 18` is required and validated.

```yaml
# ===============================
# Characters (characters.yaml)
# ===============================
characters:
  - id: "emma"                   # stable identifier
    name: "Emma Chen"           # in-game display name
    full_name: "Emma Xiaoli Chen"

    # --- Safety & identity ---
    age: 20                      # REQUIRED and must be >= 18
    gender: "female"            # free text; UI shows as provided
    pronouns: ["she","her"]     # used in narration & dialogue templates
    orientation: "bisexual"     # optional; may inform behaviors/routes
    role: "love_interest"       # taxonomy for UIs/routing (e.g., mentor, rival, etc.)

    # --- Meters: override template or add new per-character meters ---
    meters:
      trust: { default: 10 }     # override template default
      boldness: { default: 15 }
      academic_stress:          # character-specific meter (not in template)
        min: 0; max: 100; default: 30; visible: true; icon: "📚"; decay_per_day: -5

    # --- Personality & background (for Writer context; not rendered verbatim) ---
    personality:
      core_traits: ["intelligent","shy","curious","kind"]
      values: ["honesty","loyalty","academic success"]
      fears: ["rejection","failure","public embarrassment"]
      desires: ["genuine connection","achievement","new experiences"]
      quirks: ["bites lip when thinking","plays with hair when nervous"]
    background: |
      Brief author-facing notes that help the Writer keep tone consistent.
      Avoid sensitive IRL-identifying details; keep it story-relevant.

    # --- Appearance (static base + contextual snippets) ---
    appearance:
      base:
        height: "162 cm"
        build: "petite, athletic"
        hair: { color: "black", length: "shoulder", style: "ponytail" }
        eyes: { color: "dark brown" }
        skin: { tone: "light tan" }
        distinguishing_features: ["dimples","small eyebrow scar"]
      contexts:
        - id: "first_meeting"
          when: "flags.emma_met != true"
          description: "Casual campus look; focused, a bit shy."
        - id: "morning_after"
          when: "flags.emma_spent_night == true and time.slot == 'morning'"
          description: "Loose tee, tousled hair, softer demeanor."

    # --- Wardrobe: controlled ontology and slots ---
    wardrobe:
      rules:
        layer_order: ["outerwear","dress","top","bottom","feet","underwear_top","underwear_bottom","accessories"]
      outfits:
        - id: "casual_day"
          name: "Casual outfit"
          tags: ["everyday","modest"]
          layers:
            outerwear: { item: "hoodie", color: "gray" }
            top:       { item: "tank top", color: "white" }
            bottom:    { item: "jeans", style: "skinny" }
            feet:      { item: "sneakers" }
            underwear_top:    { item: "bra", style: "t-shirt" }
            underwear_bottom: { item: "panties", style: "bikini" }
            accessories: ["glasses","small backpack"]
        - id: "bold_outfit"
          name: "Bold outfit"
          unlock_when: "meters.emma.corruption >= 40 or meters.emma.boldness >= 60"
          layers:
            top: { item: "crop top", color: "black" }
            bottom: { item: "mini skirt", color: "red" }
            feet: { item: "heels" }
            underwear_top: { item: "push-up bra", style: "lace" }
            underwear_bottom: { item: "thong", style: "g-string" }
            accessories: ["choker"]

    # --- Behaviors & consent gates (progressive) ---
    behaviors:
      gates:
        - id: "accept_compliment"
          when: "always"
        - id: "accept_flirting"
          when: "meters.emma.trust >= 20 or meters.emma.corruption >= 30"
        - id: "accept_date"
          when_any:
            - "meters.emma.attraction >= 40 and meters.emma.trust >= 30"
            - "meters.emma.corruption >= 40 and meters.emma.attraction >= 30"
        - id: "accept_kiss"
          when_any:
            - "meters.emma.attraction >= 60 and meters.emma.trust >= 50 and flags.first_date_done == true"
            - "meters.emma.corruption >= 50 and meters.emma.arousal >= 40"
        - id: "accept_oral"
          when_all:
            - "meters.emma.arousal >= 70"
            - "(meters.emma.trust >= 70) or (meters.emma.corruption >= 60)"
            - "privacy == 'high'"
        - id: "accept_sex"
          when_all:
            - "meters.emma.arousal >= 80"
            - "(meters.emma.trust >= 80 and meters.emma.attraction >= 80) or (meters.emma.corruption >= 70)"
            - "privacy == 'high'"
            - "flags.protection_available == true or meters.emma.corruption >= 80"
      refusals:
        generic: "She pulls back, not ready for that yet."
        low_trust: "She shakes her head—she doesn’t know you well enough."
        wrong_place: "Not here. It’s too public."

    # --- Dialogue profile ---
    dialogue:
      base_style: "intelligent, a bit shy; warms with trust"
      vocab:
        normal: ["maybe","I guess","sort of"]
        aroused: ["please","need","want"]
      styles:
        shy: "hesitant, hedging"
        confident: "direct, fewer qualifiers"

    # --- Schedule (week-aware) ---
    schedule:
      weekday:
        morning:   { location: "cafeteria", activity: "breakfast", availability: "high" }
        afternoon: { location: "library",   activity: "study",     availability: "medium" }
        evening:   { location: "emma_room", activity: "relax",     availability: "high" }
        night:     { location: "emma_room", activity: "sleep",     availability: "none" }
      weekend:
        morning:   { location: "emma_room", activity: "sleep in",  availability: "low" }

    # --- Movement preferences ---
    movement:
      willing_zones:
        - { zone: "campus",    when: "always" }
        - { zone: "downtown",  when: "meters.emma.trust >= 50 or meters.emma.corruption >= 40" }
      willing_locations:
        - { location: "player_room", when: "meters.emma.trust >= 40" }
        - { location: "hotel_room",  when: "meters.emma.arousal >= 70" }
      transport:
        walk: "always"
        bus:  "always"
        car:  "meters.emma.trust >= 30"
      follow_thresholds:
        eager: 70     # attraction + trust
        willing: 40
        reluctant: 20
      refusal_text:
        low_trust: "I don't feel comfortable going there with you yet."
        wrong_time: "Now isn't a good time."
```

**Character Card Generation (engine-facing)** — at runtime the engine compiles a card per NPC containing summarized meters (with threshold labels), current outfit & clothing state (removed/displaced layers), active modifiers, behavior gates (allowed vs rejected), recent context beats, and a compact appearance snippet (base + active contexts).

---

## 4. Effects & Modifiers System (`effects` blocks, `modifier_system` in `game.yaml`)

Effects are **atomic state changes** (authored or AI-extracted). Modifiers are **named, stackable states** that alter behavior/appearance and can expire or be condition-bound.

### 4.1 Effect Types (authorable atoms)

```yaml
effects:
  - type: meter_change
    target: "emma"                # player | npc id
    meter: "arousal"
    op: "add"                     # add | subtract | set | multiply | divide
    value: 10
    respect_caps: true
    cap_per_turn: true

  - type: flag_set
    key: "first_kiss"
    value: true

  - type: inventory_add
    owner: "player"
    item: "flowers"
    count: 1

  - type: apply_modifier
    character: "emma"
    modifier_id: "drunk"
    duration_min: 120

  - type: remove_modifier
    character: "emma"
    modifier_id: "drunk"

  - type: outfit_change
    character: "emma"
    outfit: "bold_outfit"

  - type: clothing_remove
    character: "emma"
    layers: ["top","outerwear"]

  - type: move_to
    location: "emma_room"
    with_characters: ["emma"]

  - type: advance_time
    minutes: 30

  - type: goto_node
    node: "emma_bedroom_scene"

  - type: conditional
    when: "meters.emma.trust >= 50"
    then:
      - { type: meter_change, target: "emma", meter: "arousal", op: "add", value: 10 }
    else:
      - { type: meter_change, target: "emma", meter: "trust", op: "add", value: -5 }

  - type: random
    choices:
      - weight: 70
        effects: [{ type: meter_change, target: "emma", meter: "attraction", op: "add", value: 5 }]
      - weight: 30
        effects: [{ type: meter_change, target: "emma", meter: "attraction", op: "add", value: -5 }]
```

> **Engine guarantees** — effects are declarative, order-preserving, validated, and clamped. Unknown keys are rejected.

---

### 4.2 Modifiers (named, stackable states)

```yaml
modifier_system:
  stacking:
    default: "highest"
    per_group:
      arousal: "additive"
      inhibition: "multiplicative"

  priority:
    groups:
      - name: "status"
        priority: 100
        members: ["unconscious","paralyzed"]
      - name: "intoxication"
        priority: 90
        members: ["drunk","high"]

  exclusions:
    - group: "intoxication"
      exclusive: true

  interactions:
    - source: "drunk"
      target: "aroused"
      effect: "multiply"
      value: 1.5

  library:
    aroused:
      group: "emotional"
      appearance: { cheeks: "flushed" }
      behavior:
        dialogue_style: "breathless"
        inhibition: -1
      when: "meters.{character}.arousal >= 40"

    drunk:
      group: "intoxication"
      appearance: { eyes: "glossy" }
      behavior: { inhibition: -3, coordination: -2 }
      safety:
        disallow_gates: ["accept_sex"]
      duration_default_min: 120
```

---

### 4.3 Evaluation Order (per turn)

1. Safety gates  
2. Authored entry effects  
3. Checker deltas  
4. Resolve modifiers (activate, tick, resolve exclusions)  
5. Meter interactions  
6. Advance time  
7. Evaluate transitions/events  

---

### 4.4 Expression DSL

#### Operators:
- Comparison: ==, !=, <, <=, >, >=
- Boolean: and, or, not, in
- Arithmetic: +, -, *, /
- Grouping: ( )

#### Path access:
- Dot notation: meters.emma.trust
- Bracket notation: meters['emma']['trust']

#### Functions:
- has(item_id) - check inventory
- npc_present(npc_id) - check presence
- rand(probability) - random chance (0.0-1.0)
- max(a, b), min(a, b)
- abs(value)

#### Special variables:
- time.day, time.slot, time.weekday
- location.id, location.zone, location.privacy
- flags.* - all flags
- meters.* - all meters
- player.* - player state
- gates.{npc}.* - evaluated gates

#### Examples:
```yaml
"meters.emma.trust >= 50 and gates.emma.accept_date"
"time.slot in ['evening','night'] and rand(0.25)"
"has('flowers') or money >= 20"
```

---

### 4.5 Safety & Consent
- Modifiers cannot override hard safety rules.  
- Intimate effects must pass behavior gates + privacy checks, else trigger refusal text.  

---

## 5. World & Locations (`locations.yaml`)

The file defines the **zones** of the game world and all **locations** within them.

---

### 5.1 Hierarchical Model
- **Zones**: thematic areas (e.g., *Campus*, *Downtown*).  
- **Locations**: places within zones (rooms, streets, venues).  
- **Features**: interactable sub-areas inside locations (bed, desk, stage).  

> This mirrors narrative scale: *Zone travel* consumes more time/resources; *local movement* is near-instant.

---

### 5.2 File Structure (zones with inline locations)

```yaml
# ===============================
# Locations (zones + locations)
# ===============================
zones:
  - id: "campus"
    name: "University Campus"
    discovered: true
    accessible: true
    properties:
      size: "large"
      security: "medium"
      privacy: "low"

    transport_connections:
      - to: "downtown"
        methods: ["bus","walk","bike","car"]
        distance: 2

    events:
      on_first_enter:
        narrative: "The campus sprawls before you."
        effects:
          - { type: flag_set, key: "entered_campus", value: true }

    # Inline locations for this zone
    locations:
      - id: "dorm_room"
        name: "Your Dorm Room"
        type: "private"
        privacy: "high"
        discovered: true
        access:
          locked: true
          unlock_methods: [{ item: "dorm_key" }]
        connections:
          - to: "dorm_hallway"
            type: "door"
            bidirectional: true
        features: ["bed","desk","computer"]

      - id: "emma_room"
        name: "Emma’s Room"
        type: "private"
        privacy: "high"
        discovered: false
        discovery_conditions:
          - "flags.emma_mentioned_room"
          - "meters.emma.trust >= 30"
        access:
          locked: true
          unlock_methods:
            - { flag: "emma_invites_in", requires_presence: "emma" }
        hidden_until_discovered: true

  - id: "downtown"
    name: "City Downtown"
    discovered: false
    accessible: false
    properties:
      size: "very_large"
      privacy: "very_low"
      crime_rate: "medium"

    unlock_conditions:
      discovered: "day >= 3 or flags.heard_about_downtown"
      accessible: "zones.downtown.discovered and money >= 20"

    transport_connections:
      - to: "campus"
        methods: ["bus","car","taxi"]
        distance: 2

    locations:
      - id: "downtown_square"
        name: "Downtown Square"
        type: "public"
        privacy: "low"
        discovered: false
        access: { locked: false }
        connections:
          - to: "downtown_station"
            type: "street"
            distance: "short"
```
---

### 5.3 Movement System

```yaml
movement:
  local:
    base_time: 1
    distance_modifiers: { immediate: 0, short: 1, medium: 3, long: 5 }
  zone_travel:
    requires_exit_point: true
    time_formula: "base_time * distance"
    allow_companions: true
  restrictions:
    requires_consciousness: true
    min_energy: 5
    check_npc_consent: true
```
---

### 5.4 Exploration & Discovery

```yaml
exploration:
  discovery:
    social: { enabled: true }                 # learn via NPC hints
    active: { cost_energy: 10, cost_time: 30 }
  map:
    fog_of_war: true
    show_connections: "only_known"
    reveal_on_discovery: true
```
---

### 5.5 Design Notes
- **Zones** act like narrative hubs.  
- **Locations** provide privacy, NPC presence, and gating for scenes.  
- **Privacy**: none | low | medium | high — feeds into consent checks.  
- **Exploration** supports gradual discovery (NPC hints or wandering).  
- **Transport methods** can gate access (bus schedule, car ownership).  
- **Companions**: NPC willingness to travel is evaluated via their `movement` gates.  


---

## 6. Nodes & Story Structure (`nodes.yaml`)

Nodes are the authored backbone of PlotPlay. They define **where the story is**, **what the player can do**, and **how the game moves forward**. The Writer expands a node’s authored beats into prose; the Checker interprets the prose back into structured deltas and confirms any transitions.

---

### 6.1 Node Types
- **scene** — Focused moment with guided beats; supports freeform actions and optional choices.
- **hub** — An interactive menu of choices; limited freeform, typically used for navigation or management.
- **encounter** — Short, reactive vignette (often event-driven); usually returns to a hub.
- **ending** — Terminal node; saves final state and stops the run.

> Every node must declare a `type`. Endings must set `ending_id`.

---

### 6.2 Node Object (human-readable schema)

```yaml
# ===============================
# Nodes (nodes.yaml)
#
# Node Required Fields:
# - id: string (unique)
# - type: enum (scene|hub|encounter|ending)
# - title: string (UI display)
# - transitions: array (must have at least one with when:"always")
#
# Node Optional Fields:
# - preconditions, beats, choices, effects, etc.


# ===============================
nodes:
  - id: "tavern_entry"             # Required, unique across the game
    type: "hub"                    # Required: scene | hub | encounter | ending
    title: "Warm Lights of the Tavern"

    # Node is available only if this is true. If false, engine searches next matching node or falls back.
    preconditions: "time.slot in ['evening','night'] and zones.campus.discovered"

    # Optional node-level narration overrides (clamped by game.yaml budgets)
    narration_override:
      paragraphs: "1-2"
      writer_profile: "cheap"      # choose model profile for cost control

    # Effects applied once upon **entering** this node
    entry_effects:
      - { type: meter_change, target: "player", meter: "energy", op: "subtract", value: 5 }

    # Optional: block or steer the Writer + UI about disallowed actions
    action_filters:
      banned_freeform:
        - pattern: "steal"         # simple contains match; see DSL for advanced
          reason: "This is a friendly tavern—no theft here."
      banned_topics:
        - "non-consensual acts"
        - "minors"

    # Author guidance bullets the Writer should cover (not shown to player)
    beats:
      - "Alex (barmaid) is present; she looks busy but notices the player."
      - "Establish warmth, noise, and smells; keep it tight (2 short paragraphs)."
      - "Offer light hooks for conversation or ordering a drink."

    # Pre-authored menu choices for hubs/scenes (in addition to freeform input)
    choices:
      - id: "order_drink"
        prompt: "Order a drink"
        conditions: "money >= 5"
        effects:
          - { type: inventory_add, owner: "player", item: "ale", count: 1 }
          - { type: meter_change, target: "player", meter: "money", op: "subtract", value: 5 }

      - id: "talk_to_alex"
        prompt: "Talk to Alex"
        conditions: "npc_present('alex')"
        # node-local transition when selecting this choice (skips rule-based transitions)
        goto: "alex_smalltalk"

    # Choices that appear when their condition becomes true
    dynamic_choices:
      - id: "flirt_with_alex"
        prompt: "Flirt with Alex"
        conditions: "gates.alex.accept_flirting"

    # Rule-based transitions evaluated after effects + checker deltas
    transitions:
      - when: "has('ale') and rand(0.25)"      # 25% chance to trigger a bar brawl encounter
        to: "bar_brawl"
        reason: "Random bar event after drink"
      - when: "always"
        to: "tavern_idle"                      # safe fallback to avoid dead-ends

    # Optional: node-local hints for the Writer to bias scene pacing
    pacing:
      expected_turns: 2-4
      prefers_short_replies: true
```

**Field notes**
- `preconditions` use the shared expression DSL. If false, the engine searches the next node that matches or falls back to a designated default.
- `narration_override` lets authors tune verbosity/cost per node.
- `beats` are **author guidance** only—never shown verbatim. The Writer must weave them into prose.
- `choices` are UI buttons; **freeform input** remains available unless filtered.
- `transitions` always include a **final fallback** (`when: "always"`).

---

### 6.3 Choices: preauthored vs dynamic

```yaml
choices:
  - id: "ask_for_room"
    prompt: "Ask Alex for a room"
    conditions: "money >= 20 and gates.alex.accept_date"
    effects:
      - { type: meter_change, target: "alex", meter: "trust", op: "add", value: 5 }
    goto: "rent_room"

dynamic_choices:
  - id: "apologize_for_rudeness"
    prompt: "Apologize for earlier rudeness"
    conditions: "flags.rude_to_alex == true"
    effects:
      - { type: flag_set, key: "rude_to_alex", value: false }
      - { type: meter_change, target: "alex", meter: "trust", op: "add", value: 2 }
```

- **Preauthored choices** exist up front and gray-out/hide via `conditions`.
- **Dynamic choices** appear only when `conditions` become true.

---

### 6.4 Endings (terminal nodes)

```yaml
- id: "confession_ending"
  type: "ending"
  title: "A Quiet Confession"
  ending_id: "alex_good"
  preconditions: "meters.alex.trust >= 80 and meters.alex.attraction >= 80"
  entry_effects:
    - { type: flag_set, key: "ending_reached", value: "alex_good" }
  credits:
    summary: "You and Alex begin something real."
    epilogue:
      - "In the weeks that follow, the tavern feels like home."
      - "Alex smiles more when you walk in."
```

Rules for endings:
- Must set `ending_id` (stable string used by achievements and save summaries).
- Engine **auto-saves** and stops accepting input after rendering the ending.

---

### 6.5 Ending Taxonomy & Variants
Support multiple endings per character/route and richer metadata for UIs and achievements.
```yaml
# Endings catalog (optional; can live in nodes.yaml top-level or endings.yaml)
endings_index:
  - id: "alex_good"
    character: "alex"              # who this ending primarily concerns (optional)
    tone: "good"                   # good | neutral | bad | secret | joke
    route: "romance"               # freeform tag (e.g., corruption, purity)
    spoiler_level: "low"           # none | low | high (for UI reveal policy)
    summary: "Committed relationship with Alex."
    unlock_hint: "High trust & attraction; private setting; protection available."

```
Node ending fields (augment existing example):
```yaml
- id: "confession_ending"
  type: "ending"
  ending_id: "alex_good"           # REQUIRED
  ending_meta:
    character: "alex"
    tone: "good"
    route: "romance"
  preconditions: "meters.alex.trust >= 80 and meters.alex.attraction >= 80"
  entry_effects:
    - { type: flag_set, key: "ending_reached", value: "alex_good" }
  credits:
    summary: "You and Alex begin something real."
    epilogue:
      - "In the weeks that follow, the tavern feels like home."

```
Runtime notes
- Engine auto-saves on endings and records ```ending_id``` + ```ending_meta``` for the save summary.
- UIs may group endings by ```character``` and color-code by tone.

---

### 6.6 Transition Resolution

When a turn finishes, the engine resolves the next node using this priority:
1. **Forced `goto` from an effect or choice** (e.g., `{ type: goto_node }` or `choice.goto`).
2. **Rule-based `transitions` in the current node** (first match wins; keep ordered).
3. **Checker suggestion** (optional): the Checker may propose `{ node_transition: { to, reason } }` that matches authored rules.
4. **Stay-in-node policy**: if nothing else matches, remain in the current node or jump to its `fallback` (if declared) to avoid dead-ends.

---

### 6.7 Writer/Checker Turn Loop (per node)

1. **Assemble context**: node metadata (title, type), beats, character cards, recent dialogue memory, action filters, and global narration constraints (POV/tense/paragraphs).
2. **Writer generates**: a short scene continuation that respects beats, state, and gates (e.g., refuses prohibited actions with in-character text drawn from `behaviors.refusals`).
3. **Checker emits JSON**: `meter_deltas`, `flag_updates`, `inventory`, `clothing`, `location`, optional `node_transition {to,reason}`, `events_fired`, `safety`, and `memory.append`.
4. **Engine applies**: validate + clamp deltas, run modifier resolution and meter_interactions, and evaluate transitions.
5. **Advance time**: via explicit effects or node semantics (e.g., `hub` no time; `scene` 5–15 minutes by default—tunable in node).

---

### 6.8 Node-Level Overrides & Hints

```yaml
narration_override:
  pov: "second"           # keep aligned with game unless you need a stylistic shift
  paragraphs: "1-2"       # tighten verbose models
  writer_profile: "cheap" # cost control per node

pacing:
  expected_turns: 2-3
  default_time_minutes: 10 # used if turn had no explicit time advance
```

---

### 6.9 Minimal Example (`nodes.yaml` excerpt)

```yaml
nodes:
  - id: "tavern_entry"
    type: "hub"
    title: "Warm Lights of the Tavern"
    preconditions: "time.slot in ['evening','night']"
    beats:
      - "The bar is lively; Alex is present behind the counter."
    choices:
      - { id: "order_drink", prompt: "Order a drink", conditions: "money >= 5" }
      - { id: "talk_to_alex", prompt: "Talk to Alex", conditions: "npc_present('alex')", goto: "alex_smalltalk" }
    transitions:
      - { when: "always", to: "tavern_idle" }

  - id: "alex_smalltalk"
    type: "scene"
    title: "Small Talk with Alex"
    preconditions: "npc_present('alex')"
    beats:
      - "Alex teases lightly; keep tone warm."
      - "If the player is polite, nudge trust by +1; if rude, -1."
    transitions:
      - { when: "gates.alex.accept_flirting and meters.alex.attraction >= 40", to: "alex_flirt" }
      - { when: "always", to: "tavern_entry" }

  - id: "alex_goodbye"
    type: "ending"
    title: "A Promising Start"
    ending_id: "alex_good"
    preconditions: "meters.alex.trust >= 80 and meters.alex.attraction >= 80"
    entry_effects:
      - { type: flag_set, key: "ending_reached", value: "alex_good" }
```
---

### 6.10 Authoring Guidelines
- Always include a **fallback transition** to prevent soft-locks.
- Keep **beats** concise and actionable; avoid prose in beats.
- Use **gates** instead of raw meter checks when possible (centralizes consent logic in `characters.yaml`).
- Prefer **scene** for conversational moments and **hub** for navigation/choices.
- Tag **ending** nodes explicitly and let the engine auto-save.

---

## 7. Events & Random Encounters (`events.yaml`)

> Events inject variety into the narrative: scheduled beats, conditional encounters, or random interruptions. They can occur during travel, upon entering a location, while idling in a node, or as background triggers.

---

### 7.1 Event Object (annotated schema)

```yaml
# ===============================
# Events (events.yaml)
# ===============================
events:
  - id: "emma_drunk_text"              # Unique, stable
    title: "Late-night Text from Emma" # Optional, for logs/UI
    category: "relationship"           # For grouping & filtering (UI/tools)

    scope: "global"                    # global | zone | location | node
    zone: null                          # if scope=zone, restrict to this zone id
    location: null                      # if scope=location, restrict to this location id
    node: null                          # if scope=node, only when in this node

    trigger:                            # one or more trigger types
      scheduled:                        # Fires on specific day/time windows
        - when: "time.weekday in ['friday','saturday']"
          slot: ["night"]              # slots OR time window (hybrid mode supports both)
          hhmm: ["22:00".."02:00"]    # wrap-around ranges allowed
      conditional:
        - when_all:
            - "meters.emma.attraction >= 50"
            - "not npc_present('emma')"
      random:
        pool: "late_night_texts"       # optional: include in a named pool
        base_weight: 10                 # relative weight inside pool

    cooldown:
      days: 7                           # won't refire for N narrative days
      on_failures: true                 # cooldown even if player declined (optional)
    once_per_run: false                 # if true, can trigger only once per save
    max_fires: 3                        # hard cap across the run (optional)

    narrative: |                        # Short prompt for the Writer to weave in
      Your phone buzzes. It’s Emma: *heyyyy... cant stop thinking bout u... maybe we should talk?* 😳

    choices:                            # Optional menu for event resolution
      - id: "invite_over"
        text: "Come over"
        conditions: "gates.emma.accept_flirting"
        effects:
          - { type: meter_change, target: "emma", meter: "corruption", op: "add", value: 5 }
        goto: "emma_drunk_visit"       # Direct transition to a node (if set)

      - id: "delay_talk"
        text: "Let’s talk tomorrow"
        effects:
          - { type: meter_change, target: "emma", meter: "trust", op: "add", value: 10 }

    effects:                            # Auto-applied when the event fires (before choices)
      - { type: flag_set, key: "emma_drunk_texting", value: true }

    priority: 50                        # When multiple events are eligible, higher wins
    interrupt: true                     # If true, can pre-empt node prose and surface immediately
```
---

### 7.2 Trigger Types

* **Scheduled** — fires on exact/relative times (day, slot, weekday, hh\:mm windows).
* **Conditional** — fires when expressions become true.
* **Random (pooled)** — sampled from named pools using **weights**; optional per-turn chance.
* **Location-enter** — fires when entering a location (`scope: location`).
* **Node-enter/exit** — fires on node entry/exit hooks (`scope: node`).
* **Travel interrupts** — fires during zone travel (robbery, encounter). Use `interrupt: true`.

---

### 7.3 Event Pools & Sampling

```yaml
event_pools:
  tavern_randoms:
    chance_per_turn: 0.20            # roll each eligible turn
    max_per_slot: 1                   # avoid spam within the same slot
    members:
      - id: "bar_brawl"              # weight defaults to event.base_weight
        weight: 15
      - id: "bard_song"
        weight: 10
      - id: "stranger_flirt"
        weight: 5
```

**Sampling semantics**

1. If `chance_per_turn` succeeds, build the candidate list: events that are eligible, off cooldown, and within scope.
2. Weighted random pick by `weight` (or `base_weight` on the event).
3. Apply `priority` if multiple events compete **outside** pools (higher first).

---

### 7.4 Evaluation Order (per turn)

1. **Safety checks** (global)
2. **Forced interrupts** (interrupt: true) gathered from all sources (scheduled/conditional/pools).
    - Pick highest priority → tie-breaker: category lexical ASC → id lexical ASC
3. **Location-enter hooks** (if player just moved).
4. **Node-enter hooks** (first tick inside node).
5. **Scheduled triggers** due this tick (collect all eligible).
6. **Conditional events** becoming true this tick (collect all eligible).
7. **Random pools** - For each pool that rolls success:
    - Build candidates off cooldown & in scope.
    - Sample one winner by weight (```weight``` or ```base_weight```).
    - Attach that single pool winner to the candidate set (ignore other members).
8. **Candidate resolution** - If there are multiple candidates from steps 5–7:
    - Select highest priority.
    - Tie-breaker order: scheduled > conditional > pool_winner.
    - Final tie-breaker: id lexical ASC.
9. Apply ```event.effects```, present ```event.choices``` or weave ```event.narrative```, enforce ```cooldown```, ```once_per_run```, ```max_fires```


>Notes
>- Inside a pool, ```priority``` does not affect weighted sampling; it only matters later at step 8 if multiple sources exist.
>- Set ```priority``` mainly to let key plot events beat ambience.

---

### 7.5 Time & Calendar Integration

* In **slots** mode: use `slot: [...]` and `day >= N` conditions.
* In **hybrid** mode: prefer `hhmm` windows; the engine derives `slot` automatically from `slot_windows` (see Time & Calendar).
* Week-aware content: `time.weekday in ['friday','saturday']`.
* Travel time: events marked `interrupt: true` may **pause and consume** travel minutes.

---

### 7.6 Location & Travel Hooks

```yaml
# Location-enter example
- id: "tavern_applause"
  scope: "location"
  location: "tavern"
  trigger:
    location_enter: true
  narrative: "A round of applause erupts as you step inside."

# Travel interrupt example
- id: "rainstorm"
  category: "weather"
  scope: "global"
  interrupt: true
  trigger:
    random:
      pool: "travel_interrupts"
      base_weight: 8
  narrative: "Rain lashes the street, slowing you down."
  effects:
    - { type: advance_time, minutes: 10 }
```

---

### 7.7 Writer/Checker Interaction for Events

* The **Writer** receives `event.narrative` and a short "event header" (id, title, category) to weave into the scene **without breaking POV/tense**.
* The **Checker** may include `events_fired: [event_id]` and any state deltas caused by the event resolution.
* If an event sets `goto`, it counts as a **forced transition** (priority over node `transitions`).

---

### 7.8 Authoring Guidelines

* Keep `narrative` **short**; let the Writer style it to current scene.
* Use `cooldown` generously to avoid repetition.
* Prefer **pools** for ambience; use **scheduled** for plot beats.
* Always include a **decline/opt-out** choice for intrusive events.
* For NSFW content, ensure relevant **gates** are satisfied; otherwise provide a refusal path.

---

## 8. Milestones & Arcs (`arcs.yaml`)

> Milestones track **medium/long-term progression** (relationship stages, corruption paths, chapters). They gate content, grant achievements, and shape NPC behavior.

---

### 8.1 Arc Object (annotated schema)

```yaml
# ===============================
# Milestones / Arcs (arcs.yaml)
# ===============================

arcs:
  - id: "emma_corruption"
    name: "Emma — Corruption"
    category: "character_development"   # For UI/tools
    visibility: "hidden"                 # hidden | discovered | visible

    progression:
      mode: "threshold"                  # threshold | ordered
      evaluation: "highest"              # highest | first_match
      priority: 50                        # Compete with other arcs for overlays
    exclusive_with: ["emma_purity"]      # Only one from this set can be active

    requirements:                         # Arc activates only if true
      all:
        - "flags.met_emma == true"
        - "not flags.route_locked"

    stages:                               # Mutually exclusive; one active at a time
      - id: "innocent"
        when: "meters.emma.corruption < 20"
        title: "Innocent"
        description: "Emma is pure and cautious."
        overlays:                         # Temporary evaluation nudges while active
          behavior_gates: { disallow: ["accept_sex"] }
        entry_effects: []                 # One-time on entering this stage
        exit_effects: []                  # One-time on leaving this stage

      - id: "curious"
        when: "20 <= meters.emma.corruption < 40"
        title: "Curious"
        unlock_effects:
          - { type: unlock_outfit, character: "emma", outfit: "sexy_underwear" }
        description: "Emma is open to gentle experimentation."

      - id: "experimenting"
        when: "40 <= meters.emma.corruption < 60"
        title: "Experimenting"
        unlock_effects:
          - { type: unlock_actions, actions: ["suggest_roleplay","introduce_toys"] }
        overlays:
          behavior_gates: { allow: ["accept_kiss","accept_oral"] }

      - id: "corrupted"
        when: "60 <= meters.emma.corruption < 80"
        title: "Corrupted"
        unlock_effects:
          - { type: unlock_outfit, character: "emma", outfit: "fetish_outfit" }

      - id: "depraved"
        when: "meters.emma.corruption >= 80"
        title: "Depraved"
        unlock_effects:
          - { type: unlock_ending, ending: "emma_corruption_ending" }
        achievement:
          id: "ach_emma_corruption_max"
          title: "Complete Corruption"
          description: "Fully corrupted Emma."
          points: 25
          secret: false
```

#### Stage Hysteresis (optional fields)

You can express stages with separate enter/exit conditions or numeric thresholds.
```yaml
arcs:
  - id: "emma_corruption"
    progression: { mode: "threshold", evaluation: "highest" }
    stages:
      - id: "innocent"
        # leave when corruption rises above 22 (exit condition wider than enter of next stage)
        exit_when: "meters.emma.corruption > 22"

      - id: "curious"
        # enter at 20+, but only drop back if < 18 (hysteresis band)
        enter_when: "meters.emma.corruption >= 20"
        exit_when:  "meters.emma.corruption < 18"

      - id: "experimenting"
        enter_when: "meters.emma.corruption >= 40"
        exit_when:  "meters.emma.corruption < 36"

```

Alternative numeric shorthand (engine may expand to expressions):
```yaml
stages:
  - id: "curious"
    thresholds: { enter: 20, exit: 18 }     # applies to the arc’s primary meter

```

Debounce (time-based)
```yaml
arcs:
  - id: "emma_corruption"
    debounce:
      min_turns_in_stage: 2   # must remain ≥N turns before switching again
      min_minutes_in_stage: 5 # optional for clock/hybrid
```

Evaluation updates
- Stage selection honors ```debounce``` first, then ```exit_when/enter_when```, then the usual ```evaluation``` rule.
- If both ```when``` and hysteresis fields are present, hysteresis wins.


---

### 8.2 Semantics

* **Activation**: An arc is *eligible* when `requirements` pass.
* **Stage selection**: Depending on `progression.mode`, pick the **highest** matching stage or the **first** in order.
* **Mutual exclusivity**: `exclusive_with` deactivates other arcs in its set (most recent win, or highest `priority`).
* **Overlays**: While a stage is active, it may temporarily **allow/disallow gates**, provide meter evaluation nudges, or expose UI hints.
* **Unlocks**: `unlock_effects` fire **once** per stage the first time it’s entered.

---

### 8.3 Achievements (optional)

```yaml
achievements:
  - id: "ach_emma_corruption_max"
    title: "Complete Corruption"
    description: "Fully corrupted Emma."
    icon: "trophy_corrupt.png"      # optional, UI-only
    points: 25
    secret: false
    when: "arcs.emma_corruption.stage == 'depraved'"
```

---

### 8.4 Integration Points

* **Nodes**: use `transitions.when` with arc state, e.g., `arcs.emma_corruption.stage == 'experimenting'`.
* **Events**: preconditions can require a stage or arc activation.
* **Gates**: stage `overlays` can add/remove gate allowances (e.g., allow `accept_kiss`).
* **Endings**: terminal stages can unlock an `ending_id` and/or force transition.

---

### 8.5 Save/Load & Telemetry

```yaml
# ===============================
# Save System & State Persistence
# ===============================

save_file:
  version: "1.0.0"              # Save format version
  spec_version: "3.1"           # PlotPlay spec version
  game_id: "college_romance"
  game_version: "0.1.0"
  
  metadata:
    created_at: "2025-01-15T14:30:00Z"
    updated_at: "2025-01-15T15:45:00Z"
    play_time_minutes: 75
    turn_count: 42
    
  snapshot:
    # Current state - complete snapshot
    state:
      time: { day: 3, slot: "evening" }
      location: { zone: "campus", id: "library" }
      current_node: "study_session"
      
      meters:
        player: { energy: 65, money: 40, mind: 45 }
        npcs:
          emma: { trust: 42, attraction: 38, arousal: 0 }
          
      flags: { emma_met: true, first_kiss: false }
      
      inventory:
        player: { dorm_key: 1, flowers: 1 }
        
      clothing:
        emma: { outfit: "modest_campus", state: "intact" }
      arcs:
        emma_corruption:
            active: true
            stage: "experimenting"
            entered_at_day: 5
            history: ["innocent","curious","experimenting"]
        
    # Rolling history for context
    history:
      recent_nodes: ["intro_dorm", "first_lecture", "study_session"]
      recent_dialogue: [
        { turn: 40, speaker: "player", text: "Want to study together?" },
        { turn: 41, speaker: "emma", text: "Sure, but just studying." }
      ]
      
    # Progression tracking
    progression:
      endings_unlocked: []
      milestones_completed: ["first_meet"]
      achievements: []
```
>Note:
>* Engine should persist per-arc:
>* Persist **history** for achievements and analytics.
>* On spec migrations, provide a **stage remap** if thresholds change.

---

### 8.6 Authoring Guidelines

* Prefer **threshold** stages for meters (trust/attraction/corruption).
* Use **ordered** stages for linear chapters (chapter\_1 → chapter\_2).
* Keep stage **descriptions** author-facing (not shown verbatim).
* Give players tangible **unlocks** at key stages.
* Avoid stage thrashing: add **hysteresis** (slightly different enter vs exit thresholds) if needed.

---

### 8.7 Testing Hooks

* Provide a console command to **set arc stage** and to **print arc evaluation** for the current state.
* Golden tests pin a seed and assert arc transitions when meter thresholds are crossed.

---

## 9. Items & Inventory (`items.yaml`)

> Items provide concrete gameplay affordances: things the player can carry, give, consume, equip, or use to unlock content. They integrate with meters, modifiers, clothing, and nodes.


---

### 9.1 Item Object (annotated schema)

```yaml
# ===============================
# Items (items.yaml)
# ===============================
items:
  - id: "aphrodisiac"                  # unique stable id
    name: "Strange Pink Pill"          # display name
    category: "consumable"             # consumable | equipment | key | gift | trophy | misc
    description: "A small pink pill with unknown effects"
    value: 100                          # money value for shops/economy
    stackable: true                     # if true, counts >1 merge
    tags: ["drug","corruption"]        # freeform search/classification

    # --- Usage ---
    consumable: true                    # if true, destroyed on use
    target: "character"                 # player | character | any
    use_text: "You swallow the pill..."
    effects_on_use:
      - { type: meter_change, target: "player", meter: "arousal", op: "add", value: 50 }
      - { type: meter_change, target: "player", meter: "corruption", op: "add", value: 10 }
      - { type: apply_modifier, character: "player", modifier_id: "aphrodisiac_effect", duration_min: 120 }

    can_give: true                      # can be gifted to NPCs (gift logic in behaviors)
    gift_effects:
      - { type: meter_change, target: "emma", meter: "trust", op: "add", value: 5 }

  - id: "dorm_key"
    name: "Dorm Key"
    category: "key"
    description: "Opens your dorm room."
    stackable: false
    droppable: false                    # cannot be dropped
    unlocks:
      location: "dorm_room"

  - id: "flowers"
    name: "Bouquet of Flowers"
    category: "gift"
    description: "Freshly picked roses."
    value: 20
    tags: ["romance"]
    consumable: true
    gift_effects:
      - { type: meter_change, target: "emma", meter: "attraction", op: "add", value: 10 }
      - { type: flag_set, key: "emma_received_flowers", value: true }

  - id: "emma_panties"
    name: "Emma’s Panties"
    category: "trophy"
    description: "A pair of Emma’s panties, still warm."
    value: 0
    tags: ["intimate","emma"]
    droppable: false
    obtain_conditions:
      - "meters.emma.corruption >= 60"
      - "flags.emma_undressed == true"
```

---

### 9.2 Equipment Slots

```yaml
equipment_slots:
  weapon: { max: 1 }
  outfit: { max: 1 }
  accessory: { max: 2 }
  underwear_top: { max: 1 }
  underwear_bottom: { max: 1 }
```

- Clothing uses the wardrobe system; items.yaml can extend with accessories/equipment.
- Engine validates exclusivity per slot.

---

### 9.3 Inventory Structure (runtime state excerpt)

```yaml
state.inventory:
  player:
    flowers: 1
    dorm_key: 1
    condoms: 3
  emma:
    gifted_items: ["flowers"]
```

---

### 9.4 Mechanics

- **Acquisition**: via node effects, events, milestones, shops, or crafting.
- **Stacking**: if `stackable: true`, counts merge; otherwise each item is unique.
- **Dropping/Trading**: items may set `droppable: false` to forbid removal.
- **Keys**: unlock locations via `unlock_methods`.
- **Consumables**: apply `effects_on_use` when consumed.
- **Gifts**: apply `gift_effects` when given; conditions may reference NPC gates.
- **Trophies**: narrative collectibles; often non-droppable, may set unique flags.

---

### 9.5 Integration Points

- **Nodes**: choices can consume or require items.
- **Events**: preconditions/effects may add or remove items.
- **Milestones**: unlock special items as rewards.
- **Clothing**: normal clothes handled in wardrobe; items.yaml may add accessories or special outfits.
- **AI Context**: Checker recognizes inventory adds/removes; Writer sees notable items in character cards.

---

### 9.6 Authoring Guidelines

- Keep item descriptions short and evocative.
- Only create unique items when they matter for narrative or mechanics.
- Use categories consistently: `consumable`, `gift`, `key`, `equipment`, `trophy`.
- Test gifts on multiple NPCs to ensure trust/attraction balance.
- Avoid inventory bloat—prefer flags for abstract progress.

---
## 10. AI Contracts (Writer & Checker)

> This section defines the exact **prompts**, **inputs**, and **outputs** for both models. It is implementation-agnostic (OpenRouter, etc.) and focuses on invariants the engine depends on.

---

### 10.1 Shared Concepts

#### Turn Context Envelope (engine → models)

The engine sends a compact envelope each turn. Both Writer and Checker receive parts of this structure.

```yaml
turn:
  game:
    id: "college_romance"
    spec_version: "3.2"
    narration: { pov: "second", tense: "present", paragraphs: "2-3" }
  time: { day: 3, slot: "evening", time_hhmm: "19:42", weekday: "friday" }
  location: { zone: "campus", id: "tavern", privacy: "low" }
  node:
    id: "tavern_entry"
    type: "hub"
    title: "Warm Lights of the Tavern"
    beats: ["Alex is present behind the counter.", "Keep it tight; set ambience."]
    action_filters:
      banned_topics: ["minors", "non-consensual acts"]
      banned_freeform: [{ pattern: "steal", reason: "no theft" }]
    overrides: { paragraphs: "1-2" }
  player:
    name: "You"
    inventory: { money: 45, items: { flowers: 1 } }
  npcs:
    - id: "alex"
      card:
        summary: "barmaid, warm, observant"
        meters: { trust: 42, attraction: 38, arousal: 10, boldness: 22 }
        gates: { accept_flirting: true, accept_kiss: false }
        outfit: "work_uniform"  # clothing state already validated by engine
        modifiers: ["aroused:light"]
        dialogue_style: "teasing, warm"
  recent_dialogue:
    - speaker: player
      text: "Busy night, huh?"
    - speaker: alex
      text: "Always. You here for company or a drink?"
  last_player_action: { type: "say", text: "Maybe both." }
  ui:
    choices: [{ id: "order_drink", prompt: "Order a drink" }]
```

#### Content Safety & Consent (hard rules)

* Characters are **18+**.
* Non-consensual content is disallowed; characters use **refusal text** from their behavior definitions when gates fail.
* Public vs private scenes must respect `privacy` value from location and character gates.

---

### 10.2 Writer Contract

The Writer turns the envelope into **short, vivid prose** and **dialogue** that strictly follows style and state.

#### Input (Writer sees)

* `turn` envelope except: numerical internals (full meter ranges), raw flags, and author-only notes are **not** shown verbatim; instead they’re summarized via **character cards** and **beats**.
* If an **event** fires or a **choice** is selected, a short header is included.

#### Output (Writer must return)

A **plain text block**, ≤ target paragraph count. The Writer **must not** invent crossings (moving rooms, removing clothes) or hard state changes; instead it should imply intent and dialogue.

**Required behaviors**

* Follow `pov` and `tense` strictly.
* Respect `action_filters` and consent gates (use refusal lines if needed).
* Keep **verbosity** under `paragraphs` guidance; one paragraph = 1–4 sentences.
* Use **naturalistic dialogue** with quotation marks; avoid screenplay formatting.
* Provide hooks that align with `ui.choices` when present.

**Example (Writer)**

```
Heat spills from the doorway as you step in. The tavern hums with chatter and clinking glass. Alex catches your eye above a half-polished mug, a quick smile warming her face.

“Company’s free,” she teases, “the drink will cost you.”
```

> Note: The engine will append UI choices after this text. The Writer does not output buttons.

#### Style Guards (engine-side)

To control verbosity and POV:

* **Prefix** the prompt with a compact style charter (see 9.4 prompts).
* Add **few-shot** examples showing correct paragraphing and refusals.
* Set **token ceilings**: `writer_budget` from `game.yaml`.

---

### 10.3 Checker Contract

The Checker extracts structured state deltas **only** from what actually happened in the Writer’s prose **and** validates them against rules.

#### Input (Checker sees)

* The full `turn` envelope (including numeric meters, flags).
* The Writer’s **returned text**.
* Any **event headers** and the **player’s input** for the turn.

#### Output (Checker JSON)

Return **strict JSON** matching this shape. No extra keys, no comments, no trailing commas.

```json
{
  "safety": { "ok": true, "violations": [] },
  "meters": {
    "player": {},
    "npcs": { "alex": { "trust": =1 } }
  },
  "flags": { "rude_to_alex": false },
  "inventory": { "player": { "money": -5, "ale": +1 } },
  "clothing": { "alex": { "top": "intact" } },
  "modifiers": { "alex": [ { "apply": "aroused", "duration_min": 15 } ] },
  "location": null,
  "events_fired": ["tavern_ambience"],
  "node_transition": null,
  "memory": { "append": ["Alex teased warmly when you arrived at the tavern."] }
}
```

**Rules**

- Only emit deltas that are **explicitly implied** by the prose or confirmed by authored effects.
- Clamp to meter caps; ignore out-of-range requests.
- Never perform disallowed actions (e.g., clothing removal) unless gates + privacy allow. If attempted in prose, set `safety.ok=false` and add a violation (engine will enforce refusal next turn).
- All numeric values are either DELTAS (changes), or ABSOLUTE values
    - Format for deltas: +N or -N (always include sign for clarity)
    - Format for absolute values: =N (explicitly include = operator without space )

#### Error Recovery

If the Checker returns malformed JSON, the engine:

1. Runs a **cleanup pass** (strip code blocks, fix trailing commas, replace single quotes).
2. If still invalid, re-prompts the Checker with: *“Return JSON only. Your last output failed to parse at: <snippet>.”*
3. If it fails twice, the engine applies **no deltas** for that turn and logs an error.

---

### 10.4 Prompt Templates

#### Writer (system + user)

**System**

```
You are the PlotPlay Writer. Stay within the authored node’s intent and the character cards. POV: {pov}. Tense: {tense}. Write {paragraphs} short paragraph(s) max. Never describe state changes that require mechanics (moving zones, removing clothing, spending money). Use refusal lines when a gate would be violated. Avoid repetition. Keep it tight and evocative.
```

**User** (engine-filled)

```
NODE: {node.title} ({node.type})
BEATS: {node.beats.join(" | ")}
LOCATION: {location.id} (privacy: {location.privacy})
TIME: day {time.day}, {time.slot} {time.time_hhmm}, {time.weekday}
CARD[alex]: trust {meters.alex.trust}/100, attraction {meters.alex.attraction}/100, style {dialogue_style}, gates {allowed_gates}
RECENT: {last 3 dialogue turns}
PLAYER INPUT: {say/do text if any}
EVENT: {event.title if any}
UI CHOICES: {list visible choice prompts}
```

#### Checker (system + user)

**System**

```
You are the PlotPlay Checker. Extract ONLY what the prose and authored effects justify. Enforce consent gates and privacy rules. Output strict JSON matching the schema. No comments, no prose.
```

**User**

```
TURN ENVELOPE (machine-readable):
{compact JSON of time, node, meters, flags, inventory, clothing, gates}

WRITER TEXT:
"""
{writer_text}
"""

PLAYER INPUT:
{player_action_json}

Return JSON ONLY following this schema keys:
[safety, meters, flags, inventory, clothing, modifiers, location, events_fired, node_transition, memory]
```

---

### 10.5 Character Card Template (engine → Writer)

A minimal, consistent format the Writer can rely on.

```yaml
card:
  id: "alex"
  name: "Alex"
  summary: "barmaid, warm, observant"
  meters: { trust: 42, attraction: 38, arousal: 10, boldness: 22 }
  thresholds:
    trust: "acquaintance"
    attraction: "interested"
  outfit: "work_uniform"              # derived clothing summary
  appearance: "soft smile, rolled sleeves, ink-black hair in a band"
  modifiers: ["aroused:light"]
  dialogue_style: "teasing, warm"
  gates:
    allow: ["accept_flirting"]
    deny:  ["accept_kiss", "accept_sex"]
  refusals:
    wrong_place: "Not here. Too many eyes."
    low_trust:   "Slow down. We barely know each other."
```

---

### 10.6 JSON Schemas (formal)

> Pseudotype notation for brevity; implement as JSON Schema in `/spec/ai/`.

```txt
Safety = {
  ok: boolean,
  violations: [ { code: string, message: string, gate?: string } ]
}

Meters = {
  player?: { [meterId]: intDelta },
  npcs?:   { [npcId]: { [meterId]: intDelta } }
}

Flags = { [flagKey]: boolean | number | string }

Inventory = {
  player?: { [itemId]: intDelta | { count?: intDelta, money?: intDelta } },
  npcs?:   { [npcId]: { [itemId]: intDelta } }
}

Clothing = { [npcId]: { [layerId]: "intact" | "displaced" | "removed" } }

ModifierOp = { apply?: string, remove?: string, duration_min?: int }
Modifiers = { [npcId]: [ModifierOp] }

Location = null | { move_to: string, with?: [npcId] }

NodeTransition = null | { to: string, reason?: string }

Memory = { append?: [string], forget?: [string] }

CheckerOutput = {
  safety: Safety,
  meters: Meters,
  flags: Flags,
  inventory: Inventory,
  clothing: Clothing,
  modifiers: Modifiers,
  location: Location,
  events_fired: [string],
  node_transition: NodeTransition,
  memory: Memory
}
```

**Constraints**

* `intDelta` is an integer delta (e.g., `+2`, `-5`).
* Unknown keys are rejected; engine validates against schema.
* Missing objects mean **no change**.

---

### 10.7 Guardrails & Heuristics

* **Verbosity**: engine enforces paragraph cap; if exceeded, truncate at sentence boundary.
* **POV/Tense**: engine checks first two verbs; if mismatch, prepend corrective system reminder next turn.
* **Refusals**: if Writer attempts a gate-violating act, Checker adds `safety.violation` and **does not** apply the change; engine injects refusal line next turn using character’s profile.
* **Clothing**: any `removed` layer must pass privacy + gate checks; otherwise revert to `intact` and add a violation.
* **Money**: only change via explicit item purchase, node effects, or Checker delta with textual justification (e.g., the prose states the bartender charges 5 coins).

---

### 10.8 Memory Handling

* `memory.append` stores compact, factual scene reminders (e.g., “Alex teased you when you arrived”).
* Engine keeps a rolling window (e.g., last 6–10 memory lines) to feed into Writer as **recent\_context**.
* Avoid storing explicit sexual acts in memory unless they form a **milestone** or **flag** already tracked.

---

### 10.9 Few-Shot Snippets (recommended)

Include 1–2 mini examples for the Writer showing:

* A **polite flirt** accepted (uses `accept_flirting`).
* A **boundary push** refused (uses `refusals.low_trust`).

Include 1 mini example for the Checker showing:

* Parsing a **purchase** (money−, item+), a **meter nudge**, and a **no-op** on disallowed clothing removal.

---

### 10.10 Streaming & Partial Turns (optional)

* If streaming is enabled, Writer sends chunks; engine displays after full paragraph boundaries.
* Checker is invoked **once** after the final Writer chunk.
* On stream failure, the engine falls back to a compact retry prompt with increased temperature slightly.

#### Streaming protocol
```yaml
# ===============================
# Streaming Protocol
# ===============================

streaming:
  enabled: true
  
  writer_streaming:
    # Send chunks at natural boundaries
    chunk_boundaries: ["sentence", "paragraph", "dialogue"]
    min_chunk_tokens: 20
    max_buffer_tokens: 100
    
    # Chunk format
    chunk:
      type: "partial" | "complete"
      content: "text"
      paragraph_count: 1
      is_final: false
      
  checker_streaming:
    enabled: false  # Checker always returns complete JSON
    
  error_recovery:
    on_stream_break: "show_partial"
    timeout_ms: 30000
    retry_partial: false
```

---

### 10.11 Cost Profiles

* **cheap**: concise Writer, low temperature, nucleus sampling; Checker = fast model.
* **luxe**: more evocative Writer, higher temperature; Checker = accurate model with larger context window.
* **custom**: per-game overrides in `game.yaml`.
