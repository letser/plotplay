# PlotPlay Specification

## Table of Contents

1. [Introduction](#1-introduction)  
2. [Game Package & Manifest](#2-game-package--manifest)  
3. [Expression DSL & Condition Context](#3-expression-dsl-conditions)  
4. [Meters](#4-meters)  
5. [Flags](#5-flags)
6. [Time & Calendar](#6-time--calendar)
7. [Economy System](#7-economy-system)
8. [Items](#8-items)
9. [Clothing System](#9-clothing-system)
10. [Inventory](#10-inventory)
11. [Shopping System](#11-shopping-system)
12. [Locations & Zones](#12-locations--zones)  
13. [Characters](#13-characters)  
14. [Effects](#14-effects)
15. [Modifiers](#15-modifiers)  
16. [Actions](#16-actions)
17. [Nodes](#17-nodes)  
18. [Events](#18-events)  
19. [Arcs & Milestones](#19-arcs--milestones)  
20. [AI Contracts (Writer & Checker)](#20-ai-contracts-writer--checker)  
21. [Runtime State](#21-runtime-state)  

---

## 1. Introduction

### Overview
PlotPlay is an AI-driven text adventure engine that blends authored branching structure with dynamic prose. 
Authors define worlds, characters, and story logic; the engine enforces state, consent, 
and progression rules while the Writer model produces immersive text and the Checker model ensures consistency. 
Unlike freeform AI sandboxes, every PlotPlay game is deterministic, replayable, and always resolves at authored endings.

**The key engine features are:**
- **Blended Narrative** — Pre-authored nodes give structure; AI prose fills the gaps, always within authored boundaries.
- **Deterministic State System** — Meters, flags, modifiers, clothing, and inventory are validated and updated in predictable ways.
- **Consent & Boundaries** — All intimacy is gated by explicit thresholds and privacy rules; non-consensual paths are impossible.
- **Dynamic World Layer** — Locations, time, schedules, and random events add variation between playthroughs.
- **Structured Progression** — Arcs and milestones track long-term growth and unlock authored endings; no endless sandbox drift.

The engine uses **two-model architecture:**
- **Writer**: Expands on authored beats, generates dialogue and prose, stays within style/POV constraints.  
- **Checker**: Strict JSON output, detects state changes, validates against rules, enforces consent & hard boundaries.  
- Both models run each turn; their outputs are merged into the game state. 

### Core Concepts
PlotPlay is built on a small set of core entities. 
Authors combine these to define worlds, characters, behaviors, and story flows.

**Game Loop Entities**
- **Game** — A packaged story folder with game definition. The folder must contain the main manifest in the `game.yaml` 
and optional split files included by the game manifest.
- **Turn** — One iteration which starts with player input followed by AI Writer response. 
- **Node** — An authored story unit (scene, hub, encounter, or ending) with beats, choices, effects, and transitions.
- **Event** — A scheduled, conditional, or random trigger that overlays or interrupts play.
- **Arc** — Long-term progression trackers; arcs advance through milestones based on conditions, unlocking content and endings.
- **State** — The snapshot of current game condition: meters, flags, modifiers, clothing, inventory, time, location, arcs, and memory.
- **Character** — Any player or NPC; defined with identity, meters, flags, consent gates, wardrobe, and optional schedule/movement rules.
- **Character Card** — A compact runtime summary of a character (appearance, meters, gates, refusals) passed to the Writer for context.

**Turn flow:**
- **Nodes** define the authored story structure (scenes, interactive hubs, endings).  
- **Writer Model** produces freeform prose, respecting node type, state, and character cards.  
- **Checker Model** parses prose back into structured state deltas (meter changes, flags, clothing, etc.).  
- **Transitions** move the story between nodes, determined by authored conditions + Checker outputs.  

### State overview

Game state is the single source of truth for everything that has happened in a game. 
It captures the current snapshot of the world, characters, and story progression, 
and it is the structure that both the Writer and Checker operate at each turn.

The state is:
- **Author-driven** — all meters, flags, items, and arcs must be defined in the game’s configuration.
- **Validated** — unknown keys or invalid values are rejected at runtime.
- **Dynamic** — updated every turn by authored effects, Checker deltas, and engine rules.

**Components of State**
- **Meters** — numeric values for player and NPCs (e.g., trust, attraction, energy, money).
- **Flags** — boolean or scalar markers of progress (e.g., emma_met, first_kiss).
- **Modifiers** — temporary or stackable statuses that affect appearance/behavior (e.g., drunk, aroused).
- **Inventory** — items held by player or NPCs, with counts and categories.
- **Clothing** — wardrobe layers and their current states (intact, displaced, removed).
- **Location & Time** — current zone, location, privacy level, day/slot/clock time, and calendar info.
- **Arcs** — long-term progression trackers (current stage, history, unlocks).
- **History/Memory** — rolling log of recent nodes, dialogue, and milestones, used for AI context.

**Role of State**
- Provides **context** to the Writer (via character cards, location/time info, and node metadata).
- Provides **ground truth** to the Checker, which validates deltas against rules.
- Drives **transitions**, **events**, and **milestones** deterministically.
- Ensures **consistency**: narrative always reflects current meters, clothing, location, and consent gates.

---

## 2. Game Package & Manifest

### Game folder layout 

A **game** is a single folder containing a primary manifest file `game.yaml`plus any optional, referenced YAML files. 
The manifest declares metadata, core config, and (optionally) a list of **includes**. 
This lets small games live in a single file, while bigger games split sections into multiple files — **without changing the schema**.

```yaml
<game_folder>/
  game.yaml          # REQUIRED: main manifest
  # optional referenced files, all inside this folder:
  characters.yaml
  nodes.yaml
  events.yaml
  arcs.yaml
  items.yaml
  zones.yaml
  # ...or any custom names referenced via include
```
The engine merges all includes into the game manifest which is then validated. 
The manifest consists of a fixed set of root nodes, each defining a specific aspect of the game.  

### Game manifest template
```yaml
# ---Game metadata ---
meta:                             # REQUIRED. Game metadata node.                            
  id: "<string>"                      # REQUIRED. Game ID must match the game folder name.
  title: "<string>"                   # REQUIRED. Display title.
  version: "<string>"                 # REQUIRED. Content version (e.g., "1.0.0").
  authors: ["<string>", ...]          # REQUIRED. One or more authors.
  description: "<string>"             # OPTIONAL. Short blurb.
  content_warnings: ["<string>", ...] # OPTIONAL. e.g., ["NSFW","strong language"]
  nsfw_allowed: true                  # REQUIRED. Must be true for adult content.
  license: "<string>"                 # OPTIONAL. e.g., "CC-BY-NC-4.0"

narration:                        # REQUIRED. Narration style and engine hints
  pov: "<first|second|third>"         # Narration point of view.
  tense: "<present|past>"             # Narration tense.
  paragraphs: "1-2"                   # Hint to engine for narration size per turn.

rng_seed: "<int|auto>"           # OPTIONAL. Allows fixing random seed to reproduce the same gameplay.         
                                 # Default: auto (engine generates a random seed for each playthrough).

# --- Game starting point ---
start:                           # REQUIRED. Game starting point. See corresponding sections for details about fields.
  location: "<location_id>"           # Starting location
  node: "<node_id>"                   # Starting node.
  day: 1                              # Starting day.
  time: "08:00"                       # OPTIONAL. Starting time, "HH:MM". Default: "00:00" 

# --- Global state variables ---
meters:                          # OPTIONAL. Game meters definitions. See the Meters section.                          
  player: { ... }                     # Player meters
  template: { ... }                   # Template for NPC meters.
flags: { ... }                   # OPTIONAL. Game flags. See the Flags section.

# --- Game world definition ---
time: { ... }                    # REQUIRED. See the Time & Calendar section. 
economy: { ... }                 # REQUIRED. See the Economy section. 
items: { ... }                   # REQUIRED. See the Items section.
wardrobe: { ... }                # REQUIRED. See the Wardrobe & Outfits section. 

characters: [ ... ]              # REQUIRED. See the Characters section.              
zones: [ ... ]                   # REQUIRED. See the Locations & Zones section.
movement: { ... }                # REQUIRED. See the Movement Rules section.

# --- Game logic ---
nodes: [ ... ]                   # See the Nodes section.
modifiers: [ ... ]               # See the Modifiers section
actions: [ ... ]                 # See the Actions section.
events: [ ... ]                  # See the Events section.
arcs: [ ... ]                    # See the Arcs & Milestones section.

# ---Includes ---

# Includes: pull in external files and merge their sections
# Each included file must declare recognized root keys (e.g., characters, nodes, zones).
# Unknown root keys cause a load error.
includes: [<string>, ...]        # OPTIONAL. List of yaml files to include.
```

### Loader behavior and rules

1. First, loader Loads the `game.yaml`.
2. Then, for each file in `includes` in listed order, loader **loads** and **merges** any **recognized root keys** it contains.
   - Entries with the same id replace prior ones in corresponding sections. 
3. Loader **validates** the game after all merges:
    - unique IDs within each list section (`characters`, `items`, `nodes`, `events`, `arcs`, `zones`).
    - Cross-refs resolve (node targets, item/outfit/location IDs, etc.).
    - Time config sanity, start node/location exist.
4. All included files must be inside the game folder; no `..`, no absolute paths, no URLs.
5. Loader loads **known root keys only**; unknown roots cause a load error (helps catch typos).
6. **No nested includes** inside included files (max depth = 1).

### Authoring tips

- Small games: keep everything in **one** `game.yaml`.
- Growing games: split by **natural sections** (`characters`, `nodes`, `events`, `arcs`, `zones`, `items`).
- For huge node sets, shard into `nodes_partN.yaml` — the loader will merge them into nodes.
- Avoid redefining `meta/time/start` outside `game.yaml` to keep entry clear.

---

## 3. Expression DSL (Conditions)

### Purpose & Syntax
The game engine uses a small, safe, deterministic expression language anywhere the spec accepts a condition
(e.g., node `preconditions`, effect `when`, event triggers, content unlocking (`when/when_all/when_any`),
flag `reveal_when`, arc `when`).

```
expr        := or_expr
or_expr     := and_expr { "or" and_expr }
and_expr    := not_expr { "and" not_expr }
not_expr    := ["not"] cmp_expr
cmp_expr    := sum_expr [ ( "==" | "!=" | "<" | "<=" | ">" | ">=" | "in" ) sum_expr ]
sum_expr    := term { ( "+" | "-" ) term }
term        := factor { ( "*" | "/" ) factor }
factor      := primary | "(" expr ")"
primary     := literal | path | function_call

literal     := boolean | number | string | list
boolean     := "true" | "false"
number      := /-?\d+(\.\d+)?/
string      := double_quoted_string   # use "..."
list        := "[" [literal {"," literal}] "]"

path        := ident {("." ident) | ("[" string_or_number "]")}
ident       := /[A-Za-z_][A-Za-z0-9_]*/

function_call := ident "(" [ arg {"," arg} ] ")"
arg            := expr
```

### Types & Truthiness
- Types: **boolean**, **number**, **string**, **list** (homogenous recommended).
- Falsey: `false`, `0`, `""`, `[]`. Everything else is truthy.
- Short-circuit: `and`/`or` evaluate left→right with short-circuit.

### Operators
- Comparison: `== != < <= > >=`
- Boolean: `and or not`
- Arithmetic: `+ - *` / (numbers only)
- Membership: `X in ["a","b"]` or `time.slot in ["evening","night"]`

### Path Access
- Dotted or bracketed: `meters.emma.trust`, `flags["first_kiss"]`
- **Safe resolution**: Missing paths evaluate to `null` (falsey). They **never throw**.
- For dynamic paths, use `get("flags.route_locked", false)`.

### Built-in Functions

#### Inventory Functions
- `has(owner, item_id)` → bool — check all inventory categories (items, clothing, outfits)
  - Example: `has("player", "flowers")`
- `has_item(owner, item_id)` → bool — check items inventory only
  - Example: `has_item("player", "coffee_cup")`
- `has_clothing(owner, item_id)` → bool — check clothing inventory only
  - Example: `has_clothing("player", "red_dress")`
- `has_outfit(owner, outfit_id)` → bool — check if outfit exists in inventory (tangible item)
  - Example: `has_outfit("player", "evening_gown")`

#### Outfit Functions
- `knows_outfit(owner, outfit_id)` → bool — check if outfit recipe is known/unlocked
  - Example: `knows_outfit("player", "sexy_lingerie")`
- `can_wear_outfit(owner, outfit_id)` → bool — check if character has all required clothing items
  - Example: `can_wear_outfit("player", "formal_attire")`
- `wears_outfit(owner, outfit_id)` → bool — check if currently wearing outfit
  - Example: `wears_outfit("player", "campus_ready")`

#### Clothing Functions
- `wears(owner, item_id)` → bool — check if currently wearing clothing item (condition != "removed")
  - Example: `wears("player", "jacket")`

#### Presence & Discovery
- `npc_present(npc_id)` → bool — check if NPC is in current location
  - Example: `npc_present("emma")`
- `discovered(zone_or_location_id)` → bool — check if zone or location is discovered
  - Example: `discovered("library")`
- `unlocked(category, id)` → bool — check if ending/action/etc is unlocked
  - Example: `unlocked("ending", "good_ending")`

#### Utility Functions
- `rand(p)` → bool — random with probability 0.0-1.0 (deterministic per turn)
  - Example: `rand(0.25)`
- `min(a, b)`, `max(a, b)`, `abs(x)` — math functions
- `clamp(x, lo, hi)` → number — clamp value between bounds
- `get(path_string, default)` → any — safe nested lookup
  - Example: `get("meters.emma.trust", 0)`

### Constraints & Safety
- No assignments, no user-defined functions, no I/O, no imports, no eval.
- Strings must be **double-quoted**.
- Division by zero → expression is false (and the engine logs a warning).
- Engine enforces **length & nesting caps** to prevent abuse.

### Examples
```yaml
"meters.emma.trust >= 50 and gates.emma.accept_date"
"time.slot in ['evening','night'] and rand(0.25)"
"has('player', 'flowers') and location.privacy in ['medium','high']"
"arcs.emma_romance.stage == 'dating'"
"can_wear_outfit('player', 'formal_attire') and location.privacy == 'high'"
"wears('emma', 'sundress') and npc_present('emma')"
"get('flags.protection_available', false) == true"
```

### Runtime Variables (Condition Context)

All conditions are evaluated against a read-only **turn context** built by the engine.
The following variables and namespaces are available:

#### Time & Calendar
- `time.day` (int) — narrative day counter (≥1)
- `time.slot` (string) — current slot (e.g., "morning"), derived from current_minutes
- `time.time_hhmm` (string) — "HH:MM" format (always available)
- `time.weekday` (string) — e.g., "monday"

#### Location & Navigation
- `location.id` (string) — current location id
- `location.zone` (string) — current zone id
- `location.privacy` (string) — "low" | "medium" | "high"
- `node.id` (string) — current node id
- `turn` (int) — total turn count

#### Characters & Presence
- `characters` (list[string]) — all character ids in game
- `present` (list[string]) — character ids in current location
  - Prefer `npc_present('emma')` for clarity

#### Meters
- `meters.<char_id>.<meter_id>` (int|float) — character meter values
  - Example: `meters.emma.trust >= 50`, `meters.player.energy > 20`

#### Flags
- `flags.<flag_id>` (bool|int|float|string) — global game flags
  - Example: `flags.first_kiss == true`, `flags.route == "romance"`

#### Modifiers (active)
- `modifiers.<char_id>` (list[string]) — active modifier IDs for character
  - Example: `"well_rested" in modifiers.player`

#### Inventory (by category)
- `inventory.<char_id>.items.<item_id>` (int) — item count
- `inventory.<char_id>.clothing.<item_id>` (int) — clothing item count
- `inventory.<char_id>.outfits.<outfit_id>` (int) — outfit count
  - Prefer `has()`, `has_item()`, `has_clothing()`, `has_outfit()` functions

#### Clothing State (what's being worn)
- `clothing.<char_id>.outfit` (string|null) — currently equipped outfit ID
- `clothing.<char_id>.items.<item_id>` (string) — item condition
  - Condition: `"intact"` | `"opened"` | `"displaced"` | `"removed"`
  - Example: `clothing.player.items.jacket == "removed"`
  - Prefer `wears()` and `wears_outfit()` functions

#### Gates (consent/behavior)
- `gates.<char_id>.<gate_id>` (bool) — active behavior gates
  - Gate values are derived from meters/flags/privacy
  - Example: `gates.emma.accept_kiss == true`

#### Arcs
- `arcs.<arc_id>.stage` (string|null) — current stage ID
- `arcs.<arc_id>.history` (list[string]) — completed stage IDs
  - Example: `arcs.emma_romance.stage == "dating"`
  - Example: `"first_kiss" in arcs.emma_romance.history`

#### Discovery & Unlocks
- `discovered.zones` (set[string]) — discovered zone IDs
- `discovered.locations` (set[string]) — discovered location IDs
- `unlocked.endings` (list[string]) — unlocked ending IDs
- `unlocked.actions` (list[string]) — unlocked action IDs
  - Prefer `discovered()` and `unlocked()` functions

### Authoring Guidelines
- Prefer checking **gates** (`gates.emma.accept_kiss`) over raw meter math.
- Keep expressions short; move complexity into flags/arcs or precomputed gates.
- Use `get(...)` when a path might not exist yet (e.g., optional flags).
- Randomness: use `rand(p)` sparingly and only where replay determinism is acceptable.

### Validation & Errors
- Unknown variables/paths → resolve to `null` (falsey) and log a warning in dev builds.
- Type errors (e.g., `"foo" + 1`) → expression evaluates false; warning logged.
- Exceeding size/nesting caps → expression rejected at a load or first evaluation.

---
## 4. Meters

### Definition & template 
A **meter** is a numeric variable that tracks a continuous aspect of the player or an NPC. 
Meters represent qualities such as trust, attraction, energy, health, arousal, or corruption. 
They are:
- **Bounded** — every meter has min, max, and a default value.
- **Visible** or **hidden** — some are shown in the UI, others stay hidden until conditions reveal them.
- **Thresholded** — meters can define labeled ranges (e.g., stranger → friend → intimate) for easier gating and narrative logic.
- **Dynamic** — values can change through authored effects, Checker deltas, or automatic decay/growth rules.
- **Central to gating** — NPC behavior gates often check meter thresholds to decide whether an action is allowed.

Meters are always defined in the game configuration and are validated at load time:
 - The root `meters` node contains two sub-nodes: 
   - `player` defines meters for players, 
   - `template` defines meters for NPCs. 
 - Each NPC inherits all meters from the `template` subnode.
 - Each NPC definition in the `characters` section can provide additional `meters` section 
which may introduce additional meters for this specific NPC or override meters from the template. 

```yaml
# Single Meter Definition (template)
# Place under: meters.player.<meter_id>, or meters.template.<meter_id>, or characters.<npc_id>.meters.<meter_id>

<meter_id>:             # REQUIRED. Meter ID unique within its parent node.
# --- Bounds & Defaults ---
  min: <int>            # REQUIRED. Absolute floor (inclusive).
  max: <int>            # REQUIRED. Absolute ceiling (inclusive). Must be > min.
  default: <int>        # REQUIRED. Initial value. Must be within [min, max].

  # --- Visibility & UI ---
  visible: <bool>       # OPTIONAL. Default: true for player meters, false for NPC meters.
  hidden_until: "<expr>"# OPTIONAL. Expression DSL. When true, the meter may be shown in UI/logs.
  icon: "<string>"      # OPTIONAL. Short icon/emoji or UI key, e.g., "⚡" or "heart".
  format: "integer|percent|currency"  # OPTIONAL. UI hint: "integer" (default) | "percent" | "currency".

  # --- Behavior & Dynamics ---
  decay_per_day: <int>   # OPTIONAL. Applied at day rollover; negative = decay, positive = regen.
  decay_per_slot: <int>  # OPTIONAL. Applied when slot advances; negative = decay, positive = regen.
  delta_cap_per_turn: <int>  # OPTIONAL. Max absolute change allowed per turn for this meter.
                             # Overrides any game-wide default cap for this meter only.

  # --- Threshold Labels (authoring sugar) ---
  thresholds:           # OPTIONAL. Labeled ranges for gating & cards. Non-overlapping, ordered.
    <label_a>: { min: <int>, max: <int>}  # inclusive bounds; must lie within [min, max]
    <label_b>: { min: <int>, max: <int>}

  # --- Notes (author-facing only; ignored by engine) ---
  description: "<string>"   # OPTIONAL. Brief author notes

```
### Example (NPC meter)

```yaml
meters:
  template:
    trust:
      min: 0
      max: 100
      default: 20
      visible: false
      thresholds:
        distant: { min: 0, max: 29 }
        friendly: { min: 30, max: 69 }
        inner_circle: { min: 70, max: 100 }
      decay_per_slot: -2
      delta_cap_per_turn: 15
    attraction:
      min: 0
      max: 100
      default: 10
      visible: false
      hidden_until: "flags.met_emma == true"
      thresholds:
        curious: { min: 0, max: 39 }
        smitten: { min: 40, max: 100 }
```
---

## 5. Flags

### Definition & template 
A **flag** is a small, named piece of state that marks discrete facts or progress (met someone, completed a step, 
unlocked a route, etc.). Flags are lightweight, easy to query in conditions, and are validated at load time. 
They can be boolean, number, or string, but should remain simple and stable over a whole run.

```yaml
# Single Flag Definition (template)
# Place under: flags.<flag_key>

<flag_key>:
  type: "bool|number|string"         # REQUIRED. One of: "bool" | "number" | "string".
  default: <value>       # REQUIRED. Initial value (must match 'type').

  # --- Visibility & UI ---
  visible: <bool>        # OPTIONAL. Show in debug/author UIs. Default: false.
  reveal_when: "<expr>"  # OPTIONAL. Expression DSL; when true, UI may show this flag.
  label: "<string>"      # OPTIONAL. Human-friendly name for UI.
  
  # --- Validation (optional helpers) ---
  allowed_values:        # OPTIONAL. Only for string/number; reject values outside this set/range.
    - <valueA>
    - <valueB>
  # --- Notes (author-facing only; ignored by engine) ---
  description: "<string>"   # OPTIONAL. Brief author notes
```

**Constraints & Notes**
- **Naming**: use clear, stable keys (e.g., `emma_met`, `route_locked`, `first_kiss`).
- **Usage**: reference in expressions like `flags.first_kiss == true` or `flags.route_locked != true`.
- **Scope**: flags are **global** ; if you need NPC-scoped facts, either prefix (`emma_*`) or use NPC's meters.

### Examples

```yaml
flags:
  met_alex:
    type: "bool"
    default: false
    visible: true
    label: "Met Alex"
    description: "Set after you talk to Alex in the quad."
  alex_route_state:
    type: "string"
    default: "locked"
    allowed_values: ["locked", "available", "completed"]
    reveal_when: "flags.met_alex == true"
    description: "Tracks where the Alex romance arc currently sits."
  study_kudos:
    type: "number"
    default: 0
    allowed_values: [0, 1, 2, 3]
    description: "How many successful tutoring scenes the player completed."
```

**Typical conditions**
```yaml
"flags.emma_met == true and time.slot in ['evening','night']"
"flags.first_kiss == true or meters.emma.attraction >= 60"
"flags.study_reputation in ['good','excellent']"
```

---
## 6. Time & Calendar

### Core Philosophy

The time system satisfies four major principles:

1. **Unified logic** — The engine has a single, consistent method of advancing time, regardless of user input, narrative structure, or game mode.
2. **Predictability for authors** — Authors use simple, reliable tools to control pacing without micromanaging minutes everywhere.
3. **Natural narrative feel** — Simple conversations should not advance time like major activities. Travel, significant actions, and long events consume realistic amounts of time.
4. **AI-compatible** — Writer/Checker interaction should not create unpredictable time skips. Any AI-generated hinting remains optional and clamped by rules.

### Unified Time Model

The engine always tracks time in **minutes** as the atomic unit:

```python
time.current_minutes: int  # 0–1439 (minutes since start of day)
time.day: int              # Days elapsed since game start
time.weekday: str          # Optional day of week
```

All actions, choices, movements, and modifiers reduce to adding minutes to this value.

**Slots** are a UI/semantic layer derived from `current_minutes` and predefined window ranges:

```yaml
slot_windows:
  morning:   { start: "06:00", end: "11:59" }
  afternoon: { start: "12:00", end: "17:59" }
  evening:   { start: "18:00", end: "21:59" }
  night:     { start: "22:00", end: "05:59" }
```

- **Clock mode UI**: shows HH:MM only
- **Slot mode UI**: shows HH:MM + active slot
- **Engine behavior is identical in both**

### Time Categories and Defaults

Instead of hardcoding minutes per action, games define **named time categories** and **default values**:

```yaml
time:
  categories: {<str: <int>, ...}  # REQUIRED. Named durations in minutes for actions/choices/movements. 

  defaults:                       # REQUIRED. Assigned duration for standard actions.
    conversation: <str>             # Default for chat turns
    choice: <str>                   # Default for choices
    movement: <str>                 # Default for local movement
    default: <str>                  # Fallback for unspecified actions
    cap_per_visit: <int>>           # Max minutes accumulated per node visit

  # Calendar (optional)
  week_days: ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
  start_day: "monday"           # Day of the week at epoch start

  slots_enabled: true           # REQUIRED. Whether to show slot mode UI
  slot_windows:                 # REQUIRED if slots_enabled is true. Define slot windows
    <slot: str>: { start: <hh:mm str>, end: <hh:mm str> }
    morning:   { start: "06:00", end: "11:59" }
    afternoon: { start: "12:00", end: "17:59" }
    evening:   { start: "18:00", end: "21:59" }
    night:     { start: "22:00", end: "05:59" }
```

Each category maps to a minute value. The table is configurable per game.

### Time Resolution Priority

Every time an action happens, the engine resolves a category using the following priority:

1. **Explicit override** — A choice/action/movement specifies: `time_cost: 20`
2. **Category override** — A choice/action/movement specifies: `time_category: "quick"`
3. **Contextual fallback** — The engine picks based on context:
   - Context-level setting (choice, action, etc.)
   - Node-level override
   - Global default from `time.defaults`

### Node-Level Time Behavior

Nodes may override time behavior for actions within that node:

```yaml
nodes:
  - id: "library_study"
    type: "scene"
    time_behavior:              # OPTIONAL override block
      conversation: "instant"   # Override for this node
      choice: "quick"           # Override for this node
      default: "trivial"        # Fallback for unspecified actions
      cap_per_visit: 30         # Max minutes accumulated in this node visit
```

### Visit Cap

Prevents infinite chat loops from consuming abnormal time:

```python
minutes = min(action_cost, max(0, cap - time_spent_in_node))
```

- The cap is **per-node per-visit**, and resets on entering a new node
- The visit cap applies only to **conversation turns and default actions**
- **Explicit choice/action time costs bypass the cap**, as they represent significant narrative moments

### Choices and Actions

Every choice/action supports:

```yaml
choices:
  - id: "kiss"
    prompt: "Kiss her"
    time_category: "significant"
    # OR
    time_cost: 25
    on_select: [...]
```
> Note: `time_category` and `time_cost` are mutually exclusive.
 
If unspecified:
- Use node's `time_behavior.choice`
- Else global default `time.defaults.choice`

### Movement and Travel

#### Local Movement (within zone)

Local movement between locations in the same zone uses a fixed time cost:

```yaml
zones:
  - id: "campus"
    name: "University Campus"
    time_cost: 10              # OPTIONAL. Minutes to travel between locations in this zone
    # OR
    time_category: "standard"  # OPTIONAL. Time category for travel
```

> Note: exactly one of `time_cost` or `time_category` may be set per zone. If neither is set, uses `time.defaults.movement`.

#### Zone Travel (between zones)

Each travel method defines either `time_cost` per base unit, `speed` (base units per hour), or `category`:

```yaml
movement:
  methods:
    walk:
      active: true        # Means method is active (performed by player), so time modifiers affect time cost
      time_cost: 20       # per base unit (e.g., 20 minutes per km)
    run:
      active: true
      category: "quick"   # per base unit, taken from the category
    bus:
      active: false       # Means method is passive, so time modifiers do NOT affect time cost
      speed: 50           # base units per hour (e.g., 50 km per hour)
    train:
      active: false
      speed: 100
```

> Note: exactly one of `time_cost` / `speed` / `category` is required per method.

Travel time calculation:

```python
# If time_cost is specified:
minutes = distance * time_cost

# If speed is specified:
minutes = (distance / speed) * 60

# If category is specified:
minutes = distance * category_table[category]
```

### Time Modifiers (Buffs/Debuffs)

Active modifiers may alter time cost via `time_multiplier`:

```yaml
modifiers:
  library:
    - id: "energetic"
      group: "mood"
      when: "meters.player.energy >= 70"
      time_multiplier: 0.9     # Actions complete 10% faster

    - id: "sleepy"
      group: "mood"
      when: "meters.player.energy <= 35"
      time_multiplier: 1.2     # Actions take 20% longer
```

**Mechanics:**

1. All active modifiers stack multiplicatively
2. The final multiplier is clamped: `0.5 <= multiplier <= 2.0`
3. The result is rounded to the nearest minute

**Modifiers apply to:**

- Conversation turns
- Choices and actions
- Local movement
- Inter-zone travel **if travel method is `active: true`** (performed by characters themselves)

**Use cases:**

- Fatigue slows actions
- Caffeine speeds tasks
- Magic or tech items alter time efficiency
- Weather or terrain affects movement/travel cost

### Time Advancement Pipeline

Every turn, the engine performs:

1. Determine context type:
   - chat-only
   - choice selected
   - global action
   - movement inside zone
   - travel between zones

2. Determine effective category (per priority rules above)

3. Convert category to base minutes

4. Apply modifiers (multipliers, clamps)

5. Apply visit cap (for conversation/default actions only)

6. Add derived minutes to `time.current_minutes`

7. Recalculate:
   - HH:MM
   - active slot
   - day/week rollover

This guarantees a single, predictable, extensible method of updating time.

### Day Rollover

When time reaches or exceeds 1440 minutes (midnight):

```python
if time.current_minutes >= 1440:
    # Trigger day-end effects BEFORE normalizing
    trigger_day_end_effects()

    # Normalize time
    time.current_minutes -= 1440
    time.day += 1
    time.weekday = next_day_of_week

    # Trigger new-day effects AFTER normalizing
    trigger_day_start_effects()
```

### AI Narrative Hinting

AI-generated text **must NOT directly dictate** exact minutes.

But it **may suggest** time categories or qualitative hints like:
- "This takes a while…"
- "Time passes quickly…"
- "After a long study session…"

The **Checker** scans narrative for time-related phrases and proposes:

```yaml
time_hint:
  category: "significant"
  confidence: 0.82
```

The engine applies **only if**:
- The current context allows it
- No explicit author category exists
- Within the node visit cap

If the hint conflicts with author-defined rules, **the author wins**. The hint is advisory, not authoritative.

### Example Configuration

```yaml
time:
  categories:
    instant: 0
    trivial: 2
    quick: 5
    standard: 15
    significant: 30
    major: 60

  defaults:
    conversation: "instant"
    choice: "quick"
    movement: "standard"
    default: "trivial"
    cap_per_visit: 30

  week_days: ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
  start_day: "monday"

  slot_windows:
    morning:   { start: "06:00", end: "11:59" }
    afternoon: { start: "12:00", end: "17:59" }
    evening:   { start: "18:00", end: "21:59" }
    night:     { start: "22:00", end: "05:59" }

movement:
  methods:
    walk:
      active: true
      time_cost: 20
    bus:
      active: false
      speed: 50
```

### Authoring Guidelines

Authors now think in terms of:

- **What type of action is this?** → Assign a category
- **Does this scene need conversational pacing?** → Override `conversation` category or apply a cap
- **Does this choice represent a long activity?** → Set `significant` or explicit minutes
- **Does travel feel too fast/slow?** → Adjust travel method categories
- **Do I want fatigue or buffs to affect pacing?** → Use modifiers with `time_multiplier`

This eliminates the need to juggle turns, slots, or actions per slot. Everything reduces to a single conceptual layer: **action → category → minutes**.

### Benefits

1. **Zero chat inflation** — Simple chatter costs 0–2 minutes
2. **Travel & movement naturally balanced** — Distance × category cost = smooth pacing
3. **Everything uses the same formula** — No exceptions, no special handling
4. **AI safely enhances pacing** — Optional hinting without losing control
5. **Modifiers add depth** — Gameplay systems (fatigue, mood, buffs) interact with pacing
6. **Simpler spec, simpler engine, richer gameplay** — A rare combination of simplicity and expressive power

---

## 7. Economy system

### Configuration

The **economy system** provides a built-in money/currency mechanism. 
When enabled, it automatically creates a money meter for the player and enables purchase mechanics.
When disabled:
- No money meter created
- `purchase_item` effects are ignored
- Item `value` properties have no effect


```yaml
# Economy system configuration
# In game manifest (top level)
economy:                      # REQUIRED 
  enabled: true               # Default: true. Set false to disable a money system.
  starting_money: 50          # Default player starting money.
  max_money: 9999             # Optional: money cap. Default: 9999.
  currency_name: "dollars"    # Optional: display name. Default: "dollars".
  currency_symbol: "$"        # Optional: display symbol. Default: "$".
```

### Auto-Generated Money Meter

When `economy.enabled: true`, the engine automatically creates:

```yaml
meters:
  player:
    money:
      min: 0
      max: 9999                 # From economy.max_money
      default: 50               # From economy.starting_money
      visible: true
      icon: "💵"
      format: "currency"
```

---
## 8. Items

### Definition & template

An **item** is a defined object (gift, key, consumable, equipment, trophy, etc.) that can be owned 
by the player or NPCs or exist in locations. The game defintion defines a global list of all known items that mey be referenced by ID in applicable places. 


Clothing items are NOT defined here — they are tracked separately and live in the global `wardrobe` section.


```yaml
# Single Item Definition (template)
# Place under the inventory top level 

items:
  - id: "<string>"                # REQUIRED. Unique ID.
    name: "<string>"              # REQUIRED. Display name.
    category: "str"               # OPTIONAL. Freeform category to group items 
    
    # --- Presentation ---
    description: "<string>"       # OPTIONAL. Short description.
    icon: "<string>"              # OPTIONAL. UI hint (emoji or asset key).
    
    # --- Economy ---
    value: <float>                # OPTIONAL. Shop/economy price.
    stackable: <bool>             # OPTIONAL. Default: true.
    droppable: <bool>             # OPTIONAL. Default: true.
    
    # --- Locking ---
    locked: <bool>              # OPTIONAL. Default: false.
    when: "<expr>"              # OPTIONAL. Unlock condition (single expression).
    when_all: [<expr>, ...]     # OPTIONAL. All conditions must be true.
    when_any: [<expr>, ...]     # OPTIONAL. Any condition must be true.

    # --- Usage ---
    consumable: <bool>            # OPTIONAL. Destroyed on use.
    use_text: "<string>"          # OPTIONAL. Flavor text when used.
    
    # --- Gifting ---
    can_give: <bool>              # OPTIONAL. Can be gifted.
    
    # --- Dynamic effects ---
    on_get:  [<effect>, ... ]    # OPTIONAL. Effects applied when get item. See the Effects section.
    on_lost: [<effect>, ... ]    # OPTIONAL. Effects applied when lost item. See the Effects section.
    on_use:  [<effect>, ... ]    # OPTIONAL. Effects applied when used. See the Effects section.
    on_give: [<effect>, ... ]    # OPTIONAL. Effects when given. See the Effects section.
```

### Examples

```yaml
items:
  - id: "coffee_cup"
    name: "Campus Cafe Latte"
    category: "drink"
    description: "Hazelnut-sweet espresso that restores focus."
    value: 5
    stackable: true
    consumable: true
    use_text: "You savor the latte; the warmth steadies your nerves."
    on_use:
      - type: "meter_change"
        target: "player"
        meter: "energy"
        op: "add"
        value: 8
  - id: "backstage_pass"
    name: "Backstage Pass"
    category: "event"
    description: "Lets you access Zoe's show after midnight."
    value: 20
    stackable: false
    droppable: false
    locked: true
    when: "flags.zoe_band_invite == true"
    can_give: true
    on_give:
      - type: "meter_change"
        target: "zoe"
        meter: "trust"
        op: "add"
        value: 5
  - id: "study_notes"
    name: "Annotated Notes"
    category: "gift"
    description: "Meticulous notes that make Emma smile."
    value: 15
    stackable: false
    on_get:
      - type: "flag_set"
        key: "emma_study_session"
        value: true
```

### Authoring Notes
- `id` must be unique across all items; referenced by inventory, nodes, effects.
- Use **effects** to model concrete outcomes (money change, meter changes, flags) on use/gift.
- Prefer **keys/unlocks** for access gating; use flags only if no physical artifact is desired.
- Keep `description` concise; long lore should live in node prose.

---
## 9. Clothing System

### Concepts
The **wardrobe system** defines all clothing items globally, which can then be owned and worn by any character.


To simulate different clothing layers (e.g., outerwear, top, bottom, underwear), the wardrobe system 
defines a set of **clothing slots** that are ordered and allow one item to conceal another one. 


Clothing items can be worn separately or grouped into **outfits**. 
Outfits predefine clothing items to slots and populate corresponding items once applied.


Outfits can be worn either as a single unit and add all items to the character's inventory, 
or require a character to have/acquire all required items to be applied. Outfits just populate items into slots,
so individual items can be changed or removed as a set of items. Each clothing item has own condition and can be `intact`, `opened`, `displaced`, `removed`. `displaced` and `opened` allow revealing items from underneath slots.
`removed` means that the item is removed but still present in the inventory and can be worn again by changing its condition.
There is no special order between these statuses, 
the engine assumes that statuses will be set by effects ir detected by the Checker from narrative. 


Both clothing items and outfits act like items, included into the inventory and can be bought, given, apply effects, etc. 

The game manifest defines a global list of clothing items and outfits. Similar to meters, the definition of each character may extend and override the global lists.
  

### Global Wardrobe Definition

```yaml
# Top level in game manifest - alongside 'items', 'meters', 'characters'
wardrobe:
  slots: ["<string>",  ... ]       # Ordered list of clothing slots. 
  # E.g. ["outerwear", "top", "bottom", "underwear_top", "underwear_bottom", "feet", "accessories"] 
  items:                           # Global clothing item library
    - id: "<string>"                 # REQUIRED. Unique clothing item ID.
      name: "<string>"               # REQUIRED. Display name.
      value: <float>                 # OPTIONAL. Shop price; non-negative.
      condition: "intact|opened|displaced|removed"  # OPTIONAL. Default: "intact"
      look:                          # OPTIONAL. Narrative description.
        intact: "<string>"           # OPTIONAL. Description of the intact item.
        opened: "<string>"           # OPTIONAL. Description of the opened item.
        displaced: "<string>"        # OPTIONAL. Description of the displaced item.
        removed: "<string>"          # OPTIONAL. Description of the removed item.
      occupies: ["<slot>", ...]      # REQUIRED. Which slot(s) the current item occupies? Items like dresses that use multiple slots.
      conceals: ["<slot>", ...]      # OPTIONAL. Which slots are under the current slot? Engine can generate a description based on this. 
      can_open: <bool>               # OPTIONAL. Default: true. Can be opened/unfastened?
      # --- Locking ---
      locked: <bool>              # OPTIONAL. Default: false.
      when: "<expr>"              # OPTIONAL. Unlock condition (single expression).
      when_all: [<expr>, ...]     # OPTIONAL. All conditions must be true.
      when_any: [<expr>, ...]     # OPTIONAL. Any condition must be true.
      # --- Dynamic effects ---
      on_get:  [<effect>, ... ]      # OPTIONAL. Effects applied when get item. See the Effects section.
      on_lost: [<effect>, ... ]      # OPTIONAL. Effects applied when lost item. See the Effects section.
      on_put_on:  [<effect>, ... ]   # OPTIONAL. Effects applied when the item is put on.
      on_take_off: [<effect>, ... ]  # OPTIONAL. Effects applied when the item is taken off.
  outfits:                        # Global outfits library
    - id: "<string>"              # REQUIRED. Outfit ID.
      name: "<string>"            # REQUIRED. Display name.
      description: "<string>"     # OPTIONAL. Author notes.

      # --- Items ---
      items: {<item_id>: <condition>, ...} #Items in the outfit and their conditions. 
      grant_items: <bool>                 # OPTIONAL. Auto-grant items.

      # --- Locking ---
      locked: <bool>              # OPTIONAL. Default: false.
      when: "<expr>"              # OPTIONAL. Unlock condition (single expression).
      when_all: [<expr>, ...]     # OPTIONAL. All conditions must be true.
      when_any: [<expr>, ...]     # OPTIONAL. Any condition must be true.
      # --- Dynamic effects ---
      on_get:  [<effect>, ... ]      # OPTIONAL. Effects applied when get outfit. See the Effects section.
      on_lost: [<effect>, ... ]      # OPTIONAL. Effects applied when lost outfit. See the Effects section.
      on_put_on:  [<effect>, ... ]   # OPTIONAL. Effects applied when the outfit is put on.
      on_take_off: [<effect>, ... ]  # OPTIONAL. Effects applied when the outfit is taken off.
```

> Note: items in outfits will be merged into slots in order of appearance. 
If some items occupy the same slot, the last one will be used.


### Examples
```yaml
wardrobe:
  slots: ["outerwear", "top", "bottom", "feet", "accessory"]
  items:
    - id: "denim_jacket"
      name: "Denim Jacket"
      value: 60
      occupies: ["outerwear"]
      conceals: ["top"]
      can_open: true
      look:
        intact: "A light denim jacket peppered with enamel pins."
        opened: "The jacket hangs open, showing the shirt beneath."
    - id: "band_tee"
      name: "Vintage Band Tee"
      value: 30
      occupies: ["top"]
      look:
        intact: "A cracked-ink tee tied at the waist."
        displaced: "The tee rides up, revealing a sliver of stomach."
    - id: "black_jeans"
      name: "Black Jeans"
      value: 40
      occupies: ["bottom"]
      look:
        intact: "Slim black jeans with hidden pockets."
    - id: "combat_boots"
      name: "Combat Boots"
      value: 75
      occupies: ["feet"]
      look:
        intact: "Scarred boots with bright new laces."
  outfits:
    - id: "campus_ready"
      name: "Campus Ready"
      description: "Default outfit for the player."
      items:
        denim_jacket: "intact"
        band_tee: "intact"
        black_jeans: "intact"
        combat_boots: "intact"
      grant_items: true
    - id: "showtime"
      name: "Showtime Layers"
      items:
        band_tee: "displaced"
        black_jeans: "intact"
        combat_boots: "intact"
      locked: true
      when: "flags.zoe_band_invite == true"
```
---

## 10. Inventory

Inventory is a collection of items, clothing items, and outfits that owned by a character or avilable at a location. 

Dropping an item or clothing item means decreasing its counter for a character and increasing the corresponding value at the current location. Getting an item work in opposite way, as well as transferring between characters. 

Outfits work differently. Dropping an outfit drops corresponding clothing items but the outfit recipe itself remains known for a character. Obtaining an outfit may either give an outfit recipe itself or also give all corresponding items, depending on outfit configuration. 

The internal game state object tracks the same inventory structure for each character and location. 

```yaml
# Inventory definition
# Place under shop or location nodes 

inventory:
  items:                                      # OPTIONAL. Ids of available items with counts
    <str>: <int>
  clothing:                                   # OPTIONAL. Ids of available clothing items with counts
    <str>: <int>
  outfits:                                    # OPTIONAL. Ids of known / available outfits (recipes)
    <str>: <int>                              # For characters count is always 1 if exists
                                              # For locations may be more than 1 if outfit grants items
```

---

## 11. Shopping System


The shopping system allows players to buy or sell items. 
The `shop` node defines its own shop inventory with items available for sale. 
It can also provide an option for the player to sell items. 
Expressions allow to set price multipliers for selling and purchasing. 

The `shop` node can be **attached** to any location or character, so characters become merchants and location become stores. 
Once a shop node is attached, game UI allows players to enther the shop, list items and buy/sell. 

```yaml
# Shop definition
# Place under any location or character 
shop:                                 # OPTIONAL. Shop definition.
  name: "<string>"                    # REQUIRED. Shop name
  description: "<string>"             # OPTIONAL. Author notes.
  when: "<expr>"                      # OPTIONAL. Expression DSL. Default: true. Defines when shop is open.                      
  can_buy: "<expr>"                   # OPTIONAL. Expression DSL. Default: true. Can buy items from the player.
  can_sell: "<expr>"                  # OPTIONAL. Expression DSL. Default: true. Can sell items to the player.
  multiplier_sell: "<expr>"           # OPTIONAL. Expression DSL. Multiplier for selling to the player. Default 1.0
  multiplier_buy: "<expr>"            # OPTIONAL. Expression DSL. Multiplier for buying from the player. Default 1.0
  resell: <bool>                      # OPTIONAL. Put bought items in stock and sell back. Default false.
  
  # --- Inventory ---
  inventory: <inventory>
```

---

## 12. Locations & Zones

### World Model
The world model is hierarchical:
- **Zones**: broad narrative areas (e.g., Campus, Downtown).
- **Locations**: discrete places within zones (e.g., Library, Dorm Room).

 
the zones must be listed twice.

Locations define connections, each location lists zones it is connected to.

Locations carry **privacy levels** (public → private), **discovery state**, **access rules**, and **connections**.
Zones may define **transport options** and **events** tied to entering or exploring.

This model allows authored content to target specific areas and the engine to enforce rules 
for **movement**, **privacy**, **discovery**, and **NPC willingness**.

### Zone template
Zones have unique id, name, and define locations within a zone, access rules, and connections, each zone lists zones it is connected to. 
Connections are one way links, so for bidirectional connection between two zones, each one must refer another one.
If there are no connections provides then it is possible to travel between any zone based on visibility and access rules.

```yaml
# Zone definition
# Place under the top level zones node 

- id:                                    # REQUIRED. Unique stable zone ID.
  name: "<string>"                       # REQUIRED. Display name.
  summary: "<string>"                    # OPTIONAL. Short description to show in UI and pass to Writer. 
  privacy: "low|medium|high"             # REQUIRED. low | medium | high (default: low)
  description: "<string>"                # OPTIONAL. Author notes.

  # --- Access & discovery ---
  access:                                # OPTIONAL. Access rules.
    discovered: <bool>                     # OPTIONAL. Default false.
    hidden_until_discovered: <boo  l>      # OPTIONAL. Default false.
    discovered_when: "<expr>"              # OPTIONAL. Expressions; if true, then revealed.
    locked: <bool>                         # OPTIONAL. Default false.
    when: "<expr>"                         # OPTIONAL. Unlock condition (single expression).
    when_all: [<expr>, ...]                # OPTIONAL. All conditions must be true.
    when_any: [<expr>, ...]                # OPTIONAL. Any condition must be true.

  # --- Local movement time ---
  time_cost: <int>                      # OPTIONAL. Minutes to move between locations in this zone.
  # OR
  time_category: "<string>"             # OPTIONAL. Time category for local movement (from time.categories).
  # Note: Exactly one of time_cost or time_category may be set. If neither is set, uses time.defaults.movement.

  # --- Transport & travel ---
  connections:                          # OPTIONAL. Travel routes between zones.
    - to: ["<zone_id>|all", ...]          # REQUIRED. Connects to specified zones, shortcut 'all' means all zones. 
      exceptions: ["<zone_id>", ...]      # OPTIONAL. Excludes zone from the connection if to='all'.
      methods: ["bus|car|walk", ...]      # OPTIONAL. Transport methods for the link. See the Movement Rules for details 
      distance: <float>                   # OPTIONAL. Distance to calculate time and cost. See the Movement Rules for details.

  # --- Inline locations (see below) ---
  locations: [ ... ]
  
  # --- Entrances and exits ---
  entrances: ["<location_id>"]    # OPTIONAL. List of locations that allow entering a zone. Not set = enter any location.
  exits: ["<location_id>"]        # OPTIONAL. List of locations that allow exiting a zone. Not set = exit from any location.
  

```
### Location template
Locations are similar to zones with some differences:
- Connections have another system of connections which allows step by step movibg between locations 
using cardinal direction and up/down between floors.
- Connections may be locked with conditional unlock (e.g., a closed door requires a key)
- Locations have own inventory which defines all present items with option to collect items.
- Dropped items may be added to a location's inventory. 

> Location's inventory is not a shop, but just a list of what is available in the location and can be collected.
>
> **All price options in the inventory are ignored.**

```yaml
# Location definition lives under: zones[].locations[]
- id:                             # REQUIRED. Unique stable zone ID.
  name: "<string>"                # REQUIRED. Display name.
  summary: "<string>"             # OPTIONAL. Short description to show in UI and pass to Writer. 
  description: "<string>"         # OPTIONAL. Author notes.
  privacy: "low|medium|high"      # REQUIRED. low | medium | high (default: low)

  # --- Access & discovery ---
  access:                         # OPTIONAL. Access rules.
    discovered: <bool>                   # OPTIONAL. Default false.
    hidden_until_discovered: <bool>      # OPTIONAL. Default false.
    discovered_when: "<expr>"            # OPTIONAL. Expressions; if true, then revealed.
    locked: <bool>                       # OPTIONAL. Default false.
    when: "<expr>"                       # OPTIONAL. Unlock condition (single expression).
    when_all: [<expr>, ...]              # OPTIONAL. All conditions must be true.
    when_any: [<expr>, ...]              # OPTIONAL. Any condition must be true.

  # --- Connections (intra-zone travel) ---
  connections:                    # OPTIONAL. Connection to adjacent locations 
    - to: "<location_id>"         # REQUIRED. Target location in the same zone
      description: "<string>"     # OPTIONAL. Short description to show in UI and pass to Writer. 
      direction: "n|s|w|e|nw|ne|sw|se|u|d"   # REQUIRED. Cardinal directions and up/down.
      locked: <bool>                       # OPTIONAL. Default false.
      when: "<expr>"                       # OPTIONAL. Unlock condition (single expression).
      when_all: [<expr>, ...]              # OPTIONAL. All conditions must be true.
      when_any: [<expr>, ...]              # OPTIONAL. Any condition must be true.
  # --- Inventory ---
  inventory:   <inventory>        # OPTIONAL. Location's inventory. This is not a shop.
  shop: <shop>                    # OPTIONAL. Shop definition.
```

### Examples
```yaml
zones:
  - id: "campus"
    name: "Northbridge Campus"
    summary: "Dorms, quads, labs, and late-night coffee."
    privacy: "low"
    access:
      discovered: true
    connections:
      - to: ["downtown"]
        methods: ["walk", "bike"]
        distance: 2.0
    locations:
      - id: "campus_quad"
        name: "Sunlit Quad"
        summary: "Students weave between club tables and classes."
        privacy: "low"
        access:
          discovered: true
        connections:
          - to: "campus_library"
            description: "Follow the ivy-covered path north."
            direction: "n"
          - to: "campus_cafe"
            description: "Cut south past the lecture hall."
            direction: "s"
        inventory:
          items:
            campus_flyer: 2
        shop:
          name: "Club Merch Table"
          can_buy: "false"       # Donations only – players can't sell back.
          inventory:
            items:
              sticker_pack: 10
      - id: "campus_library"
        name: "Lambert Library"
        summary: "Stacks of books and glassed-in study rooms."
        privacy: "medium"
        connections:
          - to: "campus_quad"
            direction: "s"
        inventory:
          items:
            textbook_stats: 1
```

### Movement
The **movement system** governs how the player (and companions) travel between locations and zones.
Movement consumes **time** (in minutes), requires **access conditions** to be met,
and checks **NPC consent** when traveling with companions.

- **Local movement**: moving between locations inside the same zone consumes time based on zone configuration (see **Time & Calendar** section for details on `time_cost` and `time_category`).
- **Zone travel**: moving between different zones consumes time based on distance and travel method. Each method defines either `time_cost`, `speed`, or `category` (see **Time & Calendar** section).
- **Companions**: NPC willingness depends on trust/attraction/gates and defined for each character.

```yaml
# Movement system definition
# Place as a top level movement node
movement:                         # OPTIONAL. Top level node
  use_entry_exit: <bool>          # OPTIONAL. Default false.
                                    # If true, arrive to zone's entry locations and
                                    # must reach the zone's exit location to travel out of a zone.

  base_unit: <str>                # REQUIRED if using zone travel. Base unit for distances (km, miles, etc.)
  methods:                        # REQUIRED if using zone travel. Travel method definitions.
    <method_name>:
      active: <bool>              # REQUIRED. If true, time modifiers affect travel time.
      time_cost: <int>            # Minutes per base_unit (mutually exclusive with speed/category)
      # OR
      speed: <int>                # Base units per hour (mutually exclusive with time_cost/category)
      # OR
      category: <str>             # Time category per base_unit (mutually exclusive with time_cost/speed)
```

### Examples

```yaml
movement:
  use_entry_exit: true               # Must enter via zone entrances before exploring.
  base_unit: "km"                    # Distance is measured in kilometers.
  methods:
    walk:
      active: true                   # Player-powered, affected by modifiers
      time_cost: 20                  # 20 minutes per km
    bike:
      active: true
      category: "quick"              # Uses time.categories.quick per km
    rideshare:
      active: false                  # Passive transport, not affected by modifiers
      speed: 50                      # 50 km/h

# Zones can override local movement time:
zones:
  - id: "campus"
    time_category: "standard"        # Uses time.categories.standard for local movement
    connections:
      - to: ["downtown"]
        methods: ["walk", "bike", "rideshare"]
        distance: 2.0                # 2 km -> 40 min walking, or 2.4 min by rideshare
```

---
## 13. Characters

### Character Template
A **character** is any entity (NPC or player avatar) that participates in the story. 
Characters are defined with **identity**, **meters**, **consent gates**, **wardrobe**, and **availability**.


Characters cannot exist without a valid `id`, `name`, and `age`. 
All other aspects (meters, outfits, behaviors) are optional but strongly recommended.

Characters provide the core state the Writer and Checker operate on: they drive interpersonal progression, gating, and narrative consistency.


The player character is always defined as `player`. It can be defined as a character with `id: "player"`. 
If such character is not defined, the game engine will create a default one.
The only difference between the player character and other characters are meters: 
meters for player are taken from the `player` section of the `meters` node in the game manifest 
while meters for other characters are taken from the `template`  section.  

```yaml
# Character Template 
# Place under the top level items node 

- id:                             # REQUIRED. Unique stable ID.
  name: "<string>"                # REQUIRED. Display name.
  age: <int>                      # REQUIRED. 
  gender: "<string>"              # REQUIRED. Free text or enum ("female","male","nonbinary").
  pronouns: [<string>]            # OPTIONAL. List of pronouns for better UI pointing. E.g. ["she", "her", "herself"].
  description: "<string>"         # OPTIONAL. Author-facing description (cards, logs).
  dialogue_style: "<string>"      # OPTIONAL. A simple string describing the character's speech patterns for the AI.

  # Personality - small text pieces describing character
  # E.g. {
  #          "core traits": "strong, honest, loyal",
  #          "quirks": "clever, clever, clever",
  #          "fears": "darkness",
  #       }
  personality: {"<key>": "<string>"}  # OPTIONAL. Free text key/value pairs.
  appearance: "<string>"              # OPTIONAL. Free text.
  
  meters:  { ... }                # OPTIONAL. Overrides / additions to character_template meters.

  gates: { ... }                  # OPTIONAL. Behavioral gates 

  wardrobe: { ... }               # OPTIONAL. Overrides / additions to global wardrobe.
  clothing:                       # OPTIONAL. Initial character clothing
    outfit: <outfit_id>           # OPTIONAL. If set, will populate items into slots 
    items:  {<item_id>: <condition>, ... } # OPTIONAL. Clothing items with conditions.

  # --- Locking ---
  locked: <bool>              # OPTIONAL. Default: false.
  when: "<expr>"              # OPTIONAL. Unlock condition (single expression).
  when_all: [<expr>, ...]     # OPTIONAL. All conditions must be true.
  when_any: [<expr>, ...]     # OPTIONAL. Any condition must be true.

  # --- Schedule ---
  schedule:                      # OPTIONAL. Controls where the character is by time/day. List of schedules 
    - when: "<expr>"              # A condition, typically checking time.slot or time.weekday
      when_all: ["<expr>", ...]   # A list of conditions, all must be true.
      when_any: ["<expr>", ...]   # A list of conditions, at least one must be true.
      location: "<location_id>"   # A location where a character will appear when condition met
      # Exactly one of when, when_all, or when_any must be set.

  # --- Movement willingness ---
  movement:                       # OPTIONAL. Rules for following player to other zones/locations.
    willing_zones:                # OPTIONAL. List of rules for following player to other zones.
      - zone: "<zone_id>>"          # REQUIRED. Target zone.
        when: "<expr>"              # OPTIONAL. Condition when willing to move. Can be 'always', it is the same as not having a rule at all.
        when_all: ["<expr>", ...]   # OPTIONAL. List of conditions, all must be true.
        when_any: ["<expr>", ...]   # OPTIONAL. List of conditions, at least one must be true.
        # Exactly one of when, when_all, or when_any must be set.
    willing_locations:            # OPTIONAL. List of rules for following player to other locations.
      - location: "<location_id>>"  # REQUIRED. Target location.
        when: "<expr>"              # OPTIONAL. Condition when willing to move. Can be 'always', it is the same as not having a rule at all.
        when_all: ["<expr>", ...]   # OPTIONAL. List of conditions, all must be true.
        when_any: ["<expr>", ...]   # OPTIONAL. List of conditions, at least one must be true.
        # Exactly one of when, when_all, or when_any must be set.

  inventory: <inventory>          # OPTIONAL. Items carried by this character.
  shop: <shop>                    # OPTIONAL. Shop definition.
```
> Exactly one of `location` or `zone` must be set where applicable.

###  Gates 
Behavioral **gates** are a powerful tool for defining the conditions under which a character 
will do certain action or behave in a certain way. They are defined as a list of conditions 
that must be met for a character to be allowed to perform a certain action. 


The game engine checks gates each turn and activate all gates that are met.
Active gates can be checked by their id in expressions. Also, each gate contains narrative text 
that will be passed to the Writer and Checker to keep character's behavior consistent.

```yaml
gates:                        # OPTIONAL. A list of consent/behavior gates.
  - id: `````                   # REQUIRED. Unique ID (e.g., "accept_kiss").
    when: "<expr>"              # OPTIONAL. A single condition that must be true.
    when_any: ["<expr>", ...]   # OPTIONAL. A list of conditions where at least one must be true.
    when_all: ["<expr>", ...]   # OPTIONAL. A list of conditions where all must be true.
    acceptance: "<string>"      # OPTIONAL. Text to pass to Writer and Checker if a gate is active
    refusal: "<string>"         # OPTIONAL. Text to pass to Writer and Checker if a gate is not active
```
> Exactly one of `when`, `when_any`, and `when_all` may be set.
> 
> Either `acceptance` or `refusal` must be set.`

Each evaluated gate contributes one of the following objects:
 - `{ id, allow: true, text: acceptance }` if the gate is active and acceptance text is provided;
 - `{ id, allow: false, text: refusal }` if the gate is not active and refusal text is provided;

The engine exposes this compact form in:
 - **Character cards** (for the Writer model) — used to naturally steer dialogue.
 - **Checker envelope** — used for enforcement and validation.

### Examples
```yaml
gates:
  - id: "accept_study_session"
    when: "meters.emma.trust >= 30"
    acceptance: "\"Sure, but no copying answers,\" Emma teases."
    refusal: "\"Let's keep it casual until we know each other better.\""
  - id: "share_number"
    when_all:
      - "meters.emma.trust >= 45"
      - "time.slot in ['evening','night']"
    acceptance: "\"Text me when you get home so I know you made it.\""
    refusal: "\"Maybe after the midterm? I'm slammed right now.\""
  - id: "accept_kiss"
    when_any:
      - "meters.zoe.attraction >= 50"
      - "flags.zoe_band_invite == true"
    acceptance: "Zoe hooks a finger under your chin and closes the distance."
    refusal: "She presses a palm to your chest. \"Not yet.\""

```
### Authoring Guidelines
- Define **gates explicitly**: they control intimacy and prevent unsafe AI output.
- Use **character-scoped meters** sparingly; prefer template defaults unless diverging.
- Keep wardrobe minimal unless outfits are narratively important.
- Use **schedule** for predictable presence; events can override temporarily.
- For romance/NSFW arcs, define **both trust and attraction** as core meters.

---

## 14. Effects

### Base Effect Definition

An **effect** is an atomic, declarative instruction that changes the game state. Effects are:
- **Deterministic** — applied in order, validated against schema.
- **Declarative** — authors describe what changes, not how.
- **Guarded** — can include a `when` condition (expression DSL).
- **Validated** — invalid or disallowed effects are ignored and logged.

Effects can be authored in nodes, events, arcs, milestones, or items. 
The Checker may also emit effects as JSON deltas, which are merged into the same pipeline

```yaml
# Single Effect Definition (template)
- type: "<enum>"              # REQUIRED. Effect kind (see catalog below).
  description: "<string>"     # OPTIONAL. Author notes.
  when: "<expr>"              # OPTIONAL. A single guard condition that must be true. Default: "always". 
  when_any: ["<expr>", ...]   # OPTIONAL. A list of conditions where at least one must be true.
  when_all: ["<expr>", ...]   # OPTIONAL. A list of conditions where all must be true.

  # Rest of fields depend on type.
```
> Only one of `when`, `when_any`, and `when_all` may be set.

### Catalog of Effect Types

#### Meter change
Applies a change to a meter.
```yaml
# Modify meter value  
- type: meter_change
  # ... common fields
  target: "player|<npc_id>"   # REQUIRED. Effect target. 
  meter: "<meter_id>"
  op: "add | subtract | set | multiply | divide"
  value: <int>
  respect_caps: true    # OPTIONAL. Default: true (clamp to min/max).
  cap_per_turn: true    # OPTIONAL. Default: true (respect delta caps).
```
#### Flag set
Changes a flag value.
```yaml
# Set flag
- type: flag_set
  # ... common fields
  key: "<flag_key>"
  value: true | false | number | string
```

#### Inventory
```yaml
# Add item to inventory
- type: inventory_add
  # ... common fields
  target: "player | <npc_id>"                 # REQUIRED. Effect target. 
  item_type: "item | clothing | outfit"       # REQUIRED. Type of the item
  item: "<item_id | clothing_id | outfit_id>" # REQUIRED 
  count: <int>                                # OPTIONAL. Default: 1.

# Remove item from inventory
- type: inventory_remove
  # ... common fields
  target: "player | <npc_id>"                 # REQUIRED. Effect target. 
  item_type: "item | clothing | outfit"       # REQUIRED. Type of the item
  item: "<item_id | clothing_id | outfit_id>" # REQUIRED 
  count: <int>                                # OPTIONAL. Default: 1.

# Take item from the current location; checks availability 
- type: inventory_take
  # ... common fields
  target: "player | <npc_id>"                 # REQUIRED. Effect target. 
  item_type: "item | clothing | outfit"       # REQUIRED. Type of the item
  item: "<item_id | clothing_id | outfit_id>" # REQUIRED 
  count: <int>                                # OPTIONAL. Default: 1.

# Drops item at the current location inventory
- type: inventory_drop
  # ... common fields 
  target: "player | <npc_id>"                 # REQUIRED. Effect target. 
  item_type: "item | clothing | outfit"       # REQUIRED. Type of the item
  item: "<item_id | clothing_id | outfit_id>" # REQUIRED 
  count: <int>                                # OPTIONAL. Default: 1.

# Gives item to another player/npc
- type: inventory_give
  # ... common fields 
  source: "player | <npc_id>"                 # REQUIRED. Effect source - who gives the item. 
  target: "player | <npc_id>"                 # REQUIRED. Effect target - who receives the item. 
  item_type: "item | clothing | outfit"       # REQUIRED. Type of the item
  item: "<item_id | clothing_id | outfit_id>" # REQUIRED 
  count: <int>                                # OPTIONAL. Default: 1.
```

#### Shopping
```yaml
# Purchase item 
- type: inventory_purchase
  # ... common fields
  target: "player | <npc_id>"                  # REQUIRED. Effect target. Ignored for the flag_set
  source: "<location_id | npc_id>"             # REQUIRED. Source of the item (npc or location with a shop).
  item_type: "item | outfit | clothing"        # REQUIRED. Type of the item
  item: "<item_id | outfit_id | clothing_id>"  # REQUIRED 
  count: <int>                                 # OPTIONAL. Default: 1.
  price: <float>                               # OPTIONAL. Default: defined by item or shop 

# Sell item from inventory
- type: inventory_sell
  # ... common fields
  target: "<location_id | npc_id>"             # REQUIRED. Source of the item (npc or location with a shop).
  source: "player | <npc_id>"                  # REQUIRED. Effect target. Ignored for the flag_set
  item_type: "item | outfit | clothing"        # REQUIRED. Type of the item
  item: "<item_id | outfit_id | clothing_id>"  # REQUIRED 
  count: <int>                                 # OPTIONAL. Default: 1.
  price: <float>                               # OPTIONAL. Default: defined by item or shop 
```
#### Clothing
````yaml
# Puts an item from the wardrobe on
- type: clothing_put_on
  # ... common fields
  target: "player | <npc_id>"    # REQUIRED. Effect target. Ignored for the flag_set
  item: "<clothing_id>"          # REQUIRED. Clothing item will occupy corresponding slot(s).
  condition: "intact | displaced | opened | removed" # OPTIONAL. Default: taken from the item or intact.

# Takes an item off and keeps it in the wardrobe 
- type: clothing_take_off
  # ... common fields
  target: "player | <npc_id>"     # REQUIRED. Effect target. Ignored for the flag_set
  item: "<clothing_id>"           # REQUIRED. 

# Applies state to item  
- type: clothing_state
  # ... common fields
  target: "player | <npc_id>"     # REQUIRED. Effect target. Ignored for the flag_set
  item: "<clothing_id>"           # REQUIRED. 
  condition: "intact | displaced | opened | removed" # REQUIRED.

# Applies state to the item that occupies the slot
- type: clothing_slot_state
  # ... common fields
  target: "player | <npc_id>"   # REQUIRED. Effect target. Ignored for the flag_set
  slot: "<slot_id>"             # REQUIRED. 
  condition: "intact | displaced | opened | removed" # REQUIRED.

# Puts on all items from te outfit 
- type: outfit_put_on
  # ... common fields
  target: "player | <npc_id>"   # REQUIRED. Effect target. Ignored for the flag_set
  item: "<outfit_id>"           # REQUIRED. 

# Takes off all items from the outfit  
- type: outfit_take_off
  # ... common fields
  target: "player | <npc_id>"    # REQUIRED. Effect target. Ignored for the flag_set
  item: "<outfit_id>"            # REQUIRED.
````

#### Movement & Time
```yaml
# Local movement from the current location in a specified direction  
- type: move
  # ... common fields
  direction: "n | s | w | e | nw | ne | sw | se | u | d"  # REQUIRED. Cardinal directions and up/down.
            # Also allows full values north, south, etc. 
  with_characters: ["<npc_id>", ...]   # consent checked

# Local movement within a zone to a location 
- type: move_to
  # ... common fields
  location: "<location_id>"             # REQUIRED. Target location in the same zone
  with_characters: ["<npc_id>", ...]    # OPTIONAL.  

# Global movement between zones  
- type: travel_to
  # ... common fields
  location: "<location_id>"             # REQUIRED. Target location in another zone.
  method: "<method_id>"                 # REQUIRED. Method to travel with. 
  with_characters: ["<npc_id>", ...]    # OPTIONAL.   

# Time advancement (advances time by specified minutes; slots auto-update)
- type: advance_time
  # ... common fields
  minutes: <int>                        # REQUIRED. Minutes to advance.
```

#### Flow control
```yaml
# Switches game to a specified node 
- type: goto
  # ... common fields
  node: "<node_id>"

# Combined effect with complex conditions
- type: conditional
  when: "<expr>"                # One of when/when_any/when_all is REQUIRED.
  when_any: ["<expr>", ...]
  when_all: ["<expr>", ...]
  then: [ <effects...> ]        # Effects to apply when a condition is met.
  otherwise: [ <effects...> ]   # Effects to apply when a condition is not met.

# Random effect applies one of different sets of effects based on random value with defined weights (%) 
- type: random
  # ... common fields
  choices:
    - weight: <int>
      effects: [ <effects...> ]
    - weight: <int>
      effects: [ <effects...> ]
```
> Only one of `when`, `when_any`, and `when_all` may be set.

#### Modifiers
```yaml
# Applies a modifier
- type: apply_modifier
  # ... common fields
  target: "player|<npc_id>"    # REQUIRED. Effect target. Ignored for the flag_set
  modifier_id: "<modifier_id>" # REQUIRED.  
  duration: <int>              # OPTIONAL. Duration override

# Removes a modifier
- type: remove_modifier
  # ... common fields
  target: "player|<npc_id>"    # REQUIRED. Effect target. Ignored for the flag_set
  modifier_id: "<modifier_id>" # REQUIRED.  
```


#### Unlocks & Locks
```yaml
# Unlocks listed entity(ies) 
- type: unlock
  items: ["<item_id>", ... ]
  clothing: ["<clothing_id>", ... ]
  outfits: ["<outfit_id>", ... ]
  zones: ["<zone_id>", ... ]
  locations: ["<location_id>", ... ]
  actions: ["<action_id>", ... ]
  endings: ["<node_id>", ... ]
  
# Locks listed entity(ies) 
- type: lock
  items: ["<item_id>", ... ]
  clothing: ["<clothing_id>", ... ]
  outfits: ["<outfit_id>", ... ]
  zones: ["<zone_id>", ... ]
  locations: ["<location_id>", ... ]
  actions: ["<action_id>", ... ]
  endings: ["<node_id>", ... ]
  
```
### Execution Order (per turn)

1. **Gates** (hard rules, consent).
2. **Node entry_effects** / **event effects** (in order).
3. **Checker deltas** (validated, clamped).
4. **Modifiers resolution** (activation, expiry, stacking).
5. **Advance time** (explicit or defaults).
6. **Node transitions** (forced `goto` → authored `transitions` → fallback).

### Constraints & Notes

- Conditions use the Expression DSL.
- Unknown `type` or invalid fields → effect rejected, log warning.
- Invalid references (unknown meter/item/npc/location) → effect rejected.
- `when` guard false → effect skipped silently.
- All randomness is seeded deterministically (`game_id + run_id + turn_index`) for replay stability.

### Examples
**Trust boost or penalty**
```yaml
- type: conditional
  when: "player.polite == true"
  then:
    - { type: meter_change, target: "emma", meter: "trust", op: "add", value: 2 }
  otherwise:
    - { type: meter_change, target: "emma", meter: "trust", op: "subtract", value: 1 }

```
**Weighted random outcome**
```yaml
- type: random
  choices:
    - weight: 70
      effects: [{ type: flag_set, key: "heard_rumor", value: true }]
    - weight: 30
      effects: [{ type: meter_change, target: "player", meter: "energy", op: "subtract", value: 5 }]
```

**Move with companion**
```yaml
- type: move_to
  location: "emma_room"
  with_characters: ["emma"]
```
---

## 15. Modifiers

### Purpose & Template 
A **modifier** is a named, (usually) temporary state that overlays appearance/behavior rules 
without directly rewriting canonical facts. Think **aroused**, **drunk**, **injured**, **tired**.
Modifiers can auto-activate from conditions, be applied/removed by effects, stack or exclude each other, 
and may carry a default duration. They influence gates, dialogue tone, and presentation 
but don’t invent hard state changes by themselves.


**Activation**: a modifier can be **auto-activated** by `when` each turn, or explicitly applied via an effect.

```yaml
# Modifier Template
# Place under: modifiers.library

  # --- Identity ---
- id: "<string>"                # REQUIRED. Unique ID.
  group: "<string>"             # OPTIONAL but recommended. Category for stacking/exclusions (e.g., "intoxication", "emotional").
  priority: <int>               # OPTIONAL. Priority within a group (see below).

  # --- Activation ---
  when: "<expr>"                # OPTIONAL. Auto-activation condition (evaluated each turn).
  when_all: "<expr>"            # OPTIONAL. Auto-activation condition (evaluated each turn).
  when_any: "<expr>"            # OPTIONAL. Auto-activation condition (evaluated each turn).
  duration: <int>               # OPTIONAL. Default runtime duration in minutes/actions when applied without explicit duration.

  # --- Appearance & Behavior overlays (soft influence) ---
  mixins: ["<string", ...]      # OPTIONAL. Small deltas for cards/descriptions; never hard state edits.
                                #  "cheeks flushed", "eyes glossy"
  dialogue_style: <string>       # OPTIONAL, Overrides dialogue style.

  # --- Safety & Gates (hard constraints) ---
  disallow_gates: ["<gate_id>", ...]  # OPTIONAL. Gates to disable, e.g., forbid "accept_sex" while drunk
  allow_gates: ["<gate_id>", ...]     # OPTIONAL. Gates to force. Rarely used; prefer arcs/gates unless tightly controlled

  # --- Systemic Rules ---
  clamp_meters:                 # OPTIONAL. Enforce temporary boundaries on meters while active.
    <meter_id>: { min: <int>, max: <int> } # e.g., arousal: { max: 60 }

  time_multiplier: <float>      # OPTIONAL. Time cost multiplier (0.5 - 2.0). Affects conversation, choices, actions, and active movement.
                                #  < 1.0 = faster (e.g., 0.9 = 10% faster)
                                #  > 1.0 = slower (e.g., 1.2 = 20% slower)
                                #  See Time & Calendar section for details on how modifiers stack and apply.

  # --- One-shot hooks (optional sugar) ---
  on_enter: [<effect>, ... ]    # OPTIONAL. Apply once when the modifier becomes active.
  on_exit:  [<effect>, ... ]    # OPTIONAL. Apply once when it ends.
```
> No conditions at all or exactly one of `when`, `when_any`, and `when_all` must be set.

### Modifiers Node & Stacking Rules 

All modifiers are defined under the `modifiers` node together with stacking rules.  
Stacking rules define how multiple modifiers of the same group applied:
- All modifiers of the same group are sorted by priority (highest first). 
Modifiers with the same priority are applied in the order they defined.
- If multiple modifiers of the same group is about to be applied, the engine decides what to do 
based on the `stacking` parameter:
   - `highest` - the highest priority modifier is applied. Any other active modifiers of the same group are removed.
   - `lowest` - the lowest priority modifier is applied. Any other active modifiers of the same group are removed.
   - `all` - all modifiers that are not currently active applied.
 
```yaml
# Modifiers definition
# In game manifest (top level)
modifiers:
  stacking:                                   # OPTIONAL. Stacking rules
     <group_name>: "highest|lowest|all"     # REQUIRED. List of staking options for groups 
  library: [ <modifier>, ... ]                # REQUIRED. Modifiers definition                
```

### Examples
```yaml
modifiers:
  library:
    aroused:
      group: "emotional"
      when: "meters.{character}.arousal >= 40"
      appearance: { "cheeks flushed" }
      dialogue_style: "breathless"

    drunk:
      group: "intoxication"
      duration: 120
      appearance: { "eyes glossy" }
      disallow_gates: ["accept_sex"]   # hard stop while intoxicated

    injured_light:
      group: "status"
      duration: 240
      on_enter:
        - { type: meter_change, target: "player", meter: "energy", op: "subtract", value: 10 }
      on_exit:
        - { type: flag_set, key: "injury_healed", value: true }
```
---

## 16. Actions

### Purpose & Template

An **action** is a globally defined, reusable player choice that can be unlocked through effects. 
Unlike node-based `choices` which are tied to a specific scene, 
unlocked actions can become available to the player in any context, provided their conditions are met. 
This allows for character growth and new abilities that persist across the game.

Actions are defined in a top-level `actions` node.


```yaml
# Actions definition
# In game manifest (top level)
actions:
 -  id:                           # REQUIRED. UniqueID for unlocking.
    prompt: "<string>"            # REQUIRED. The text shown to the player.
    category: "<string>"          # OPTIONAL. UI hint (e.g., "conversation", "romance").
    when: "<expr>"                # OPTIONAL. Expression DSL. Action is only available if true.
    when_all: ["<expr>", ... ]    # OPTIONAL. Expression DSL. Action is only available if true.
    when_any: ["<expr>", ... ]    # OPTIONAL. Expression DSL. Action is only available if true.
    effects: [ <effect>, ... ]    # OPTIONAL. Effects applied when the action is chosen.
```

> Only one of `when`, `when_any`, and `when_all` may be set.

### Example

```yaml
# actions.yaml

actions:
  - id: "deep_talk_emma"
    prompt: "Ask Emma about her family"
    category: "conversation"
    when: "npc_present('emma') and meters.emma.trust >= 60"
    effects:
      - type: "meter_change"
        target: "emma"
        meter: "trust"
        op: "add"
        value: 10
      - type: "flag_set"
        key: "emma_opened_up"
        value: true
```
---

## 17. Nodes

### Purpose & Template

A **node** is the authored backbone of a PlotPlay story.
Each node represents a discrete story unit — a scene, a hub, an encounter,an event, or an ending. 
Nodes combine **authored beats and choices** with **freeform AI prose**, 
and control how the story progresses via **transitions**.

Nodes are where most author effort goes: they set context for the Writer, define conditions and effects, and connect to other nodes

**Node types:**
- **scene** — A focused moment with authored beats and freeform AI prose.
- **hub** — A menu-like node for navigation or repeated interactions.
- **encounter** — Short, often event-driven vignette; usually returns to a hub.
- **ending** — Terminal node; resolves the story and stops play.

```yaml
# Node template
# Place under the 'nodes' root node
- id:                                   # REQUIRED. Unique node id
  type: "scene|hub|encounter|ending"    # REQUIRED. scene | hub | encounter | ending
  title: "<string>"                     # REQUIRED. Display name in UI/logs.
  description: "<string>"               # OPTIONAL. Author notes.
  characters_present: ["<string>", ...] # OPTIONAL. Explicitly list character IDs present in this node.

  # --- Writer guidance ---
  narration:                            # OPTIONAL. Override defaults from the game manifest.
    pov: "<first|second|third>"
    tense: "<present|past>"
    paragraphs: "1-2"

  beats: [<string>, ... ]               # OPTIONAL. Bullets for Writer (not shown to players).

  # --- Time behavior ---
  time_behavior:                        # OPTIONAL. Override time costs for actions in this node.
    conversation: "<string>"            # OPTIONAL. Time category for chat turns (from time.categories).
    choice: "<string>"                  # OPTIONAL. Time category for choices (from time.categories).
    default: "<string>"                 # OPTIONAL. Fallback category for unspecified actions.
    cap_per_visit: <int>                # OPTIONAL. Max minutes accumulated per node visit (default: 30).

  # --- Effects ---
  on_enter: [ <effect>, ... ]           # OPTIONAL. Applied when the node is entered.
  on_exit:  [ <effect>, ... ]           # OPTIONAL. Applied when the node is left.

  # --- Actions & choices ---
  choices:                              # OPTIONAL. Pre-authored menu buttons. Always visible
    - id: "<string>"                    # REQUIRED. Unique id
      prompt: "<string>"                # REQUIRED. Shown to player.
      when: "<expr>"                    # OPTIONAL. Choice disabled if false.
      when_all: ["<expr>", ... ]        #   Expression DSL; all must be true to activate transition.
      when_any: ["<expr>", ... ]        #   Expression DSL; any must be true to activate transition.
      time_cost: <int>                  # OPTIONAL. Explicit minutes consumed by this choice.
      # OR
      time_category: "<string>"         # OPTIONAL. Time category (from time.categories).
      # Note: If neither is set, uses node's time_behavior.choice or time.defaults.choice.
      on_select: [ <effect>, ... ]      # REQUIRED. Effects applied when the choice is chosen.

  dynamic_choices:                      # OPTIONAL. Pre-authored menu buttons. Appear only when conditions become true.
    - prompt: "<string>"                # REQUIRED. Shown to player.
      when: "<expr>"                    # OPTIONAL. Choice disabled if false.
      when_all: ["<expr>", ... ]        #   Expression DSL; all must be true to activate transition.
      when_any: ["<expr>", ... ]        #   Expression DSL; any must be true to activate transition.
      time_cost: <int>                  # OPTIONAL. Explicit minutes consumed by this choice.
      # OR
      time_category: "<string>"         # OPTIONAL. Time category (from time.categories).
      # Note: If neither is set, uses node's time_behavior.choice or time.defaults.choice.
      on_select: [ <effect>, ... ]      # REQUIRED. Effects applied when the choice is chosen.

  # --- Triggers ---
  triggers:                              # OPTIONAL. Automatic effects and transitions (via goto effect). 
    - when: "<expr>"                    #   Expression DSL; must be true to activate transition.
      when_all: ["<expr>", ... ]        #   Expression DSL; all must be true to activate transition.
      when_any: ["<expr>", ... ]        #   Expression DSL; any must be true to activate transition.
      on_select: [ <effect>, ... ]      #   REQUIRED. Effects applied when conditions are met.

  # --- Ending-specific ---
  ending_id: "<string>"                    # REQUIRED if type == ending. Unique ending id
```

> Only one of `when`, `when_any`, and `when_all` may be set.

### Examples


#### Scene 
```yaml
- id: "intro_courtyard"
  type:  "scene"
  title: "First Day on Campus"
  when:  "time.day == 1 and time.slot == 'morning'"
  beats:
    - "Set the scene in the campus courtyard."
    - "Emma is visible but shy."
  transitions:
    - { when: "always", to: "player_room_intro" }
```
#### Hub
```yaml
- id: "player_room"
  type:  "hub"
  title: "Your Dorm Room"
  choices:
    - id: "sleep"
      prompt: "Go to sleep"
      effects:
        - { type: advance_time, minutes: 480 }
        - { type: meter_change, target: "player", meter: "energy", op: "set", value: 100 }
      goto: "morning_after"
  transitions:
    - { when: "always", to: "player_room_idle" }
```

#### Ending
```yaml
- id: "emma_love_good"
  type: "ending"
  title: "A Happy Ending with Emma"
  ending_id: "emma_good"
  when: "meters.emma.trust >= 80 and meters.emma.attraction >= 80"
  on_enter:
    - { type: flag_set, key: "ending_reached", value: "emma_good" }
  beats:
    - "You and Emma start a genuine relationship."
    - "Over the next weeks, she grows more confident."
    - "You share love without losing her innocence."
```

### Authoring Guidelines

- Always provide at least one **fallback transition** (`when: always`) to prevent dead-ends.
- Keep **beats** concise — bullets of intent, not prose.
- Use **choices** for deliberate actions; **dynamic_choices** for reactive unlocking.
- Use **gates** (in `characters` node) instead of raw meter checks where possible.
- For endings, always set a stable `ending_id`.
---

## 18. Events

### Purpose & Template

An **event** is authored content that can **interrupt**, **inject**, or **overlay** narrative 
outside the main node flow. 
They are triggered by **conditions** or **randomness**, and can fire once, repeat, or cycle with cooldowns.
Conditions allow to restrict events to specific nodes, locations, characters, time, etc. 

Events differ from nodes:
- **Nodes** are the backbone of the story (explicit story beats).
- **Events** are side-triggers, often opportunistic or reactive.

- The event template follows the same structure as a node, but with a few differences:
- **Type** is always `event`,
- Events contain **conditions** that define when the event fires,
- `ending_id` is ignored.

**Runtime behavior:**
- Engine evaluates all events **each turn** after node resolution, before the next node selection.
- An event is **eligible** to fire if:
 - conditions are met (if any),
 - random value fails into the probability range,
 - the event is not at cooldown.
- Eligible events are collected into a pool in order they defined:
- Events are applied one by one:
  - **On entry** effects are applied.
  - **Add characters** to the scene,  
  - **Inject beats** into the current node,
  - **Inject choices and dynamic choices** into the current node,
  - **Evaluate triggers** and **run matching triggers** 
  - **On exit** effects are applied, even is effect triggers a transition to another node.
- Once fired, an event is **cooled down** for a defined duration of minutes or time slots. 

Depending on effects in triggers, they can be either applied silently or trigger a node transition.
In case of transition the processing chain terminates and the engine jumps to the target node.


```yaml
# Event definition lives under: events: [ ... ]
# Place under the 'events' root node
- id:                                   # REQUIRED. Unique node id 
  type: "event"                         # REQUIRED. scene | hub | encounter | ending
  title: "<string>"                     # REQUIRED. Display name in UI/logs.
  description: "<string>"               # OPTIONAL. Author notes.
  characters_present: ["<string>", ...] # OPTIONAL. Explicitly list character IDs present in this node.

  # --- Triggering ---
  when: "<expr>"                # OPTIONAL. Expression DSL Condition to trigger an event.
  when_all: ["<expr>", ... ]    # OPTIONAL. Expression DSL Condition to trigger an event.
  when_any: ["<expr>", ... ]    # OPTIONAL. Expression DSL Condition to trigger an event.
  probability: <int>            # OPTIONAL. Probability of ramdom event firing in percent. Default: 100. 
  cooldown: <int>               # OPTIONAL. Default 0. Minutes or slots before re-eligibility.
  once_per_game : <bool>        # OPTIONAL. Default: false. If true, fires only once per game run.


  # --- Writer guidance ---
  narration:                            # OPTIONAL. Override defaults from the game manifest.
    pov: "<first|second|third>"
    tense: "<present|past>"
    paragraphs: "1-2"

  beats: [<string>, ... ]               # OPTIONAL. Bullets for Writer (not shown to players).

  # --- Effects ---
  on_enter: [ <effect>, ... ]           # OPTIONAL. Applied when the node is entered.
  on_exit:  [ <effect>, ... ]           # OPTIONAL. Applied when the node is left.

  # --- Actions & choices ---
  choices:                              # OPTIONAL. Pre-authored menu buttons. Always visible
    - id: "<string>"                    # REQUIRED. Unique id 
      prompt: "<string>"                # REQUIRED. Shown to player.
      when: "<expr>"                    # OPTIONAL. Choice disabled if false.
      when_all: ["<expr>", ... ]        #   Expression DSL; all must be true to activate transition.
      when_any: ["<expr>", ... ]        #   Expression DSL; any must be true to activate transition.
      on_select: [ <effect>, ... ]      # REQUIRED. Effects applied when the choice is chosen.

  dynamic_choices:                      # OPTIONAL. Pre-authored menu buttons. Appear only when conditions become true.
    - prompt: "<string>"                # REQUIRED. Shown to player.
      when: "<expr>"                    # OPTIONAL. Choice disabled if false.
      when_all: ["<expr>", ... ]        #   Expression DSL; all must be true to activate transition.
      when_any: ["<expr>", ... ]        #   Expression DSL; any must be true to activate transition.
      on_select: [ <effect>, ... ]      # REQUIRED. Effects applied when the choice is chosen.

  # --- Transitions ---
  triggers:                              # OPTIONAL. Automatic effects and transitions (via goto effect). 
    - when: "<expr>"                    #   Expression DSL; must be true to activate transition.
      when_all: ["<expr>", ... ]        #   Expression DSL; all must be true to activate transition.
      when_any: ["<expr>", ... ]        #   Expression DSL; any must be true to activate transition.
      on_select: [ <effect>, ... ]      #   REQUIRED. Effects applied when conditions are met.
```
> Only one of `when`, `when_any`, and `when_all` may be set.

### Examples

#### Scheduled event
```yaml
- id: "emma_text_day1"
  type: "event"
  title: "Emma Texts You"
  when: "time.slot == 'night' and time.day == 1"
  narrative: "Your phone buzzes — Emma wants to meet tomorrow."
  effects:
    - { type: flag_set, key: "emma_texted", value: true }
```
#### Conditional encounter
```yaml
- id: "library_meet"
  type: "event"
  title: "Chance Meeting in Library"
  when: "location.id == 'library' and meters.emma.trust >= 20"
  beats: ["Emma waves shyly from behind a book."]
  choices:
    - id: "chat"
      prompt: "Go talk to her"
      effects:
        - { type: meter_change, target: "emma", meter: "trust", op: "add", value: 5 }
      goto: "library_chat"
```

#### Random ambient
```yaml
- id: "rumor_spread"
  type: "event"
  title: "Rumor at the Courtyard"
  when: "location.zone == 'campus'"
  probability: 30
  cooldown: 720     # 12h before next chance
  beats: ["You overhear whispers of your name among the students."]
  effects:
    - { type: flag_set, key: "rumor_active", value: true }

```

### Authoring Guidelines

- Always define **cooldowns** for random events to prevent spam.
- Use **location** in conditions to tie events naturally to a setting.
- Keep **scheduled triggers** simple (slot/day/weekday).
- Avoid chaining too many effects — events should be light and modular.
- For **story-critical beats**, prefer nodes to events.
- Mark one-time story events with `once_per_game: true` to avoid repeats.

---

## 19. Arcs & Milestones

### Purpose & Arc Template

An **arc** is a long-term progression track that represents a character route, corruption path, relationship stage,
or overarching plotline. Each arc consists of ordered **milestones** (stages).
- **Arcs** define the big picture: multi-stage progressions with conditions.
- **Milestones** are checkpoints inside an arc: when conditions are met, the arc advances.
- Advancing a milestone can **unlock content**, **trigger effects**, or **open endings**.

Arcs ensure that stories have clear progression, and that endings are unlocked in a controlled, authored way.

```yaml
# Arc Template
# Place under the 'arcs' root node
- id: "<string>"                     # REQUIRED. Unique arc ID.
  title: "<string>"                  # REQUIRED. Display name for authoring.
  description: "<string>"            # OPTIONAL. Author note.

  # --- Metadata ---
  character: "<npc_id>"              # OPTIONAL. Link arc to a character.
  category: "<string>"               # OPTIONAL. e.g., "romance","corruption","plot"
  repeatable: <bool>                 # OPTIONAL. Default false.

  # --- Stages / milestones ---
  stages:
    - id: "<string>"                 # REQUIRED. Stage ID.
      title: "<string>"              # REQUIRED. Stage name.
      description: "<string>"        # OPTIONAL. Author note.

      # --- Conditions to enter the stage ---
      when: "<expr>"         # REQUIRED. DSL condition. Checked each turn.
      when_all: "<expr>"     # REQUIRED. DSL condition. Checked each turn.
      when_any: "<expr>"     # REQUIRED. DSL condition. Checked each turn.
      once_per_game: <bool>                   # OPTIONAL. Default true. Fires once.

      # --- Effects ---
      on_enter:   [ <effect>, ... ]  # Applied once when the stage begins.
      on_exit: [ <effect>, ... ]     # Applied once when leaving stage.
```

### Examples

#### Romance arc
```yaml
- id: "emma_romance"
  title: "Emma Romance Path"
  character: "emma"
  category: "romance"
  stages:
    - id: "acquaintance"
      title: "Just Met"
      when: "flags.emma_met == true"
      on_enter:
        - { type: meter_change, target: "emma", meter: "trust", op: "add", value: 5 }

    - id: "dating"
      title: "Dating"
      when: "meters.emma.trust >= 50 and flags.first_kiss == true"
      on_exit:
        - { type: unlock_ending, ending: "emma_good" }

    - id: "in_love"
      title: "In Love"
      when: "meters.emma.trust >= 80 and meters.emma.attraction >= 80"
      on_enter:
        - { type: flag_set, key: "emma_in_love", value: true }
      on_exit:
        - { type: unlock_ending, ending: "emma_best" }
```

#### Corruption arc

```yaml
- id: "emma_corruption"
  title: "Emma Corruption Path"
  character: "emma"
  category: "corruption"
  stages:
    - id: "innocent"
      title: "Innocent"
      when: "meters.emma.corruption < 20"

    - id: "curious"
      title: "Curious"
      when: "20 <= meters.emma.corruption and meters.emma.corruption < 40"

    - id: "experimenting"
      title: "Experimenting"
      when: "40 <= meters.emma.corruption and meters.emma.corruption < 70"
      on_enter:
        - { type: unlock_outfit, character: "emma", outfit: "bold_outfit" }

    - id: "corrupted"
      title: "Corrupted"
      when: "meters.emma.corruption >= 70"
      on_enter:
        - { type: unlock_ending, ending: "emma_corrupted" }

```
### Authoring Guidelines
- Always order stages so they evaluate from lowest to highest.
- Keep `when` expressions simple (use flags/meters).
- Use `on_enter` effects for immediate narrative unlocks.
- Use `on_exit` effects for one-off triggers (new choices, outfits, endings).
- Mark arcs as **non-repeatable** unless designed for loops.
- Each arc should normally have **at least one ending unlock**.

---

## 20. AI Contracts (Writer & Checker)

### Definition

The game engine uses a **two-model architecture** every turn:
 - **Writer**: expands authored beats, generates prose & dialogue in style/POV, and respects state/gates.
 - **Checker**: parses the Writer’s text into structured **state deltas** (meters, flags, clothing, inventory), validates consent & safety, and proposes transitions if justified.

Both run each turn; the engine merges outputs into the game state.

#### Turn Context Envelope

Every turn, the engine builds a **context envelope** that goes to both models.
```yaml
turn:
  game: { id: "college_romance", spec_version: "3.2" }
  time: { day: 3, slot: "evening", time_hhmm: "19:42", weekday: "friday" }
  location: { zone: "campus", id: "tavern", privacy: "low" }
  node: { id: "tavern_entry", type: "hub", title: "Warm Lights of the Tavern" }
  player:
    inventory: { money: 45, flowers: 1 }
  npcs:
    - id: "alex"
      card:
        meters: { trust: 42, attraction: 38, arousal: 10 }
        gates: { accept_flirting: true, accept_kiss: false }
        outfit: "work_uniform"
        refusals: { low_trust: "Slow down." }
  recent_dialogue:
    - { speaker: "player", text: "Busy night, huh?" }
    - { speaker: "alex", text: "Always. You here for company or a drink?" }
  last_player_action: { type: "say", text: "Maybe both." }
  ui:
    choices: [{ id: "order_drink", prompt: "Order a drink" }]
```

### Safety & Consent Enforcement (engine rules)

- **Inputs considered:** `location.privacy`, per-character **gates** (allow/refusal text), active **modifiers** 
(e.g., `disallow_gates`), and game-level switches (`nsfw_allowed`).
- **Writer behavior:** may narrate **attempts** or social beats around blocked acts but **must not describe** the act 
as completed. Use the gate’s **refusal text** to guide the scene when blocked.
- **Checker behavior:** if prose contradicts gates/privacy, set `safety.ok = false`, 
record a violation (`gate:<id>` or `privacy:<level>`), and omit any deltas that would realize the blocked act.
- **Modifiers** can temporarily alter permissions (e.g., `drunk` may `disallow_gates: [accept_sex]`).

### Writer Contract

- **Input**: node metadata, beats, character cards, last dialogue, UI choices, player action, events.
- **Output**: **plain text prose** (≤ target paragraphs).

#### Requirements
- Follow POV/tense.
- Respect gates and privacy rules.
- Writer may narrate attempts or refusals, but never depict blocked acts as happening. Use gate `refusal` text where `allow = false`.
- Keep to the paragraph budget.
- Never describe raw state changes (money, inventory, clothing). Imply only.

#### Example Output
```
Heat spills from the tavern. Alex smiles from behind the bar, polishing a glass.  

“Company’s free,” she teases, “but the drink will cost you.”

```
### Checker Contract

- **Input**: full envelope + Writer text + player input.
- **Output**: strict JSON with deltas.

#### Schema
```json
{
  "safety": { "ok": true, "violations": [] },
  "meters": { "player": {}, "npcs": { "alex": { "trust": "+1" } } },
  "flags": { "rude_to_alex": false },
  "inventory": { "player": { "money": "-5", "ale": "+1" } },
  "clothing": { "alex": { "top": "intact" } },
  "modifiers": { "alex": [{ "apply": "aroused", "duration_min": 15 }] },
  "location": null,
  "events_fired": ["tavern_ambience"],
  "node_transition": null,
  "memory": { "append": ["Alex teased warmly when you arrived."] }
}

```

#### Rules
- Use `+N/-N` for deltas, `=N` for absolutes.
- Output only changes justified by prose and allowed by gates/privacy.
- Clamp values within defined caps.
- If prose depicts a blocked act: set `safety.ok = false`, add `violations: ["gate:<id>", "privacy:<level>"]`, and emit no deltas realizing the act.
- Output strict JSON; no extra keys or comments.

### Prompt templates

#### Writer 
```
You are the PlotPlay Writer. POV: {pov}. Tense: {tense}. Write {paragraphs} short paragraph(s) max. 
Never describe state changes (items, money, clothes). Use refusal lines if a gate blocks. 
Keep dialogue natural. Stay within beats and character cards.
```
#### Checker
```
You are the PlotPlay Checker. Extract ONLY justified deltas. 
Respect consent gates and privacy. Output strict JSON with keys: 
[safety, meters, flags, inventory, clothing, modifiers, location, events_fired, node_transition, memory].

```

#### Character Cards (engine → Writer)
Minimal, consistent format:
```yaml
card:
  id: "alex"
  summary: "barmaid, warm, observant"
  meters: { trust: 42, attraction: 38, arousal: 10 }
  thresholds: { trust: "acquaintance", attraction: "interested" }
  outfit: "work_uniform"
  modifiers: ["aroused:light"]
  dialogue_style: "teasing, warm"
  gates: { allow: ["accept_flirting"], deny: ["accept_kiss"] }
  refusals: { low_trust: "Not yet.", wrong_place: "Not here." }
```

---

## 21. Runtime State

### Snapshot overview

The engine keeps a single `GameState` dataclass (see `app/core/state_manager.py`) for the active session.  
This object is the canonical, mutation-safe snapshot that feeds **ConditionEvaluator**, all engine services,
and the Writer/Checker envelopes. It flattens the author-defined data into runtime-friendly shapes and
tracks every outcome the Checker or authored effects apply.

### Time, location & discovery
- `day`, `time_slot`, `time_hhmm`, `weekday`, and the embedded `time: TimeState` mirror the configured clock.
- `location_current` / `zone_current` (aliases `current_location` / `current_zone`) identify where the player stands.
- `location_previous` lets movement describe "where you came from".
- `location_privacy` (alias `current_privacy`) stores the resolved `LocationPrivacy` enum for the present location.
- `discovered_locations` and `discovered_zones` are sets of IDs the player has revealed. 
- `zones` / `locations` map IDs to `ZoneState` / `LocationState` snapshots (locked/discovered booleans, privacy, local inventory/shop data).

### Characters, meters & inventory
- `characters` holds `CharacterState` objects (runtime meters, inventory, gate cache, per-character arc state).
- `present_chars` (alias `present_characters`) is the ordered list of NPC IDs currently on scene (the player is implied).
- `meters` is a dict of `char_id -> { meter_id: value }` used for fast math and UI.
- `flags` is the resolved `FlagsState` dict defined in the manifest.
- `inventory` stores `owner_id -> { item_id: count }` for every actor. Clothing pieces and outfits share the same namespace, so `"campus_ready": 1` simply means the outfit recipe is owned.
- `location_inventory` mirrors the same structure but keyed by `location_id`.

```json
"inventory": {
  "player": { "coffee_cup": 1, "denim_jacket": 1, "campus_ready": 1 },
  "emma": { "textbook_stats": 1 }
},
"location_inventory": {
  "campus_library": { "textbook_stats": 1 }
}
```

### Wardrobe, outfits & modifiers
- `clothing` (per-character within `characters` dict) tracks which clothing items a character is wearing and their current conditions. The structure is **item-based** rather than slot-based, allowing the engine to derive slot occupancy from item definitions:
  - `outfit`: The ID of the currently equipped outfit (if any). When an outfit is equipped, it populates the `items` dict with the outfit's clothing items.
  - `items`: Maps clothing item IDs to their current condition (`"intact"`, `"opened"`, `"displaced"`, or `"removed"`).

  The engine derives slot occupancy by looking up each item's `occupies` field in the clothing item definition. For example, if `"denim_jacket"` occupies `["outerwear"]` and `"band_tee"` occupies `["top"]`, the engine knows which slots are filled without storing slot-to-item mappings in state. When an item is `"removed"`, it remains in the `items` dict (allowing re-wearing) but is not considered when determining slot occupancy for concealment rules.

- `modifiers` is `owner_id -> {"<modifier_id>": <duration_in_minutes>, ...}`.

```json
"characters": {
  "player": {
    "clothing": {
      "outfit": "campus_ready",
      "items": {
        "denim_jacket": "intact",
        "band_tee": "displaced",
        "black_jeans": "intact"
      }
    },
    "modifiers": { "well_rested": 120 }
  },
  "emma": {
    "clothing": {
      "outfit": null,
      "items": {
        "sundress": "intact"
      }
    },
    "modifiers": {}
  }
}
```

### Arcs, milestones & progression
- `arcs` maps `arc_id -> ArcState(stage, history)` so repeatable arcs can replay.
- `active_arcs` caches `arc_id -> stage_id` for quick lookups, while `arc_history` exposes the chronological trail per arc.
- `completed_milestones` flattens milestone IDs that fired outside of a still-active arc (handy for events).
- `current_node`, `visited_nodes`, `unlocked_actions`, and `unlocked_endings` collectively reflect narrative progress and which UI actions should appear.
- `discovered_locations` / `discovered_zones` (above) gate navigation menus.

### Events, cooldowns & logging
- `cooldowns` keeps `event_id -> turns remaining` to throttle re-entry.
- `events_history` is a chronological list of event IDs already fired.
- `turn_count` counts the total turns the player has taken; `actions_this_slot` tracks per-slot action consumption for the time service.
- `narrative_history` stores the recent prose (used for recap/memory prompts).
- `memory_log` is a list of dicts such as `{ "text": "Emma lent you her notes.", "characters": ["emma"], "day": 2 }` and powers the character memories UI.

### Metadata & helpers
- `shops` / `merchants` are optional caches of location IDs and NPC IDs that expose shop menus for faster lookups.
- `created_at` / `updated_at` are UTC timestamps set when the save slot is created and last modified.
- `to_dict()` returns a serialization-ready copy for debug APIs (sets remain sets; FastAPI’s encoder turns them into lists).

Together these fields represent the full runtime contract for the engine and the AI agents.  
Any new system should either extend the manifest schemas or add a new, well-defined namespace inside `GameState` so the Writer/Checker context stays deterministic.
