# PlotPlay Specification v3


---

## 1. Introduction

PlotPlay is an AI-driven text adventure engine that blends authored branching structure with dynamic prose. 
Authors define worlds, characters, and story logic in YAML; the engine enforces state, consent, 
and progression rules while the Writer model produces immersive text and the Checker model ensures consistency. 
Unlike freeform AI sandboxes, every PlotPlay game is deterministic, replayable, and always resolves at authored endings.

---

## Table of Contents

1. [Introduction](#1-introduction)  
2. [Key Features](#2-key-features)  
3. [Core Concepts](#3-core-concepts)  
4. [Game Package & Manifest](#4-game-package--manifest)  
5. [State Overview](#5-state-overview)  
6. [Expression DSL & Condition Context](#6-expression-dsl-conditions)  
7. [Characters](#7-characters)  
8. [Meters](#8-meters)  
9. [Flags](#9-flags)  
10. [Modifiers](#10-modifiers)  
11. [Inventory & Items](#11-inventory--items)  
12. [Clothing & Wardrobe](#12-clothing--wardrobe)  
13. [Effects](#13-effects)  
14. [Actions](#14-actions)
15. [Locations & Zones](#15-locations--zones)  
16. [Movement Rules](#16-movement-rules)  
17. [Time & Calendar](#17-time--calendar)  
18. [Nodes](#18-nodes)  
19. [Events](#19-events)  
20. [Arcs & Milestones](#20-arcs--milestones)  
21. [AI Contracts (Writer & Checker)](#21-ai-contracts-writer--checker)  


---

## 2. Key Features
- **Blended Narrative** — Pre-authored nodes give structure; AI prose fills the gaps, always within authored boundaries.
- **Deterministic State System** — Meters, flags, modifiers, clothing, and inventory are validated and updated in predictable ways.
- **Consent & Boundaries** — All intimacy is gated by explicit thresholds and privacy rules; non-consensual paths are impossible.
- **Dynamic World Layer** — Locations, time, schedules, and random events add variation between playthroughs.
- **Structured Progression** — Arcs and milestones track long-term growth and unlock authored endings; no endless sandbox drift.
- **Two-Model Safety Loop** — Writer creates prose; Checker enforces rules and state, ensuring consistency.

---


## 3. Core Concepts

PlotPlay is built on a small set of core entities. Authors combine these to define worlds, characters, and story flows.

### 3.1. Game Parts and Flow

**Game Loop Entities**
- **Game** — A packaged story folder with game.yaml manifest and optional split files.
- **Turn** — One iteration of player input, Writer prose, Checker deltas, and state update.
- **Node** — An authored story unit (scene, hub, encounter, or ending) with beats, choices, effects, and transitions.
- **Event** — A scheduled, conditional, or random trigger that overlays or interrupts play.
- **Arc & Milestone** — Long-term progression trackers; arcs advance through milestones based on conditions, unlocking content and endings.

**State Entities**
- **State** — The single source of truth: meters, flags, modifiers, clothing, inventory, time, location, arcs, and memory.
- **Character** — Any player or NPC; defined with identity, age (18+), meters, flags, consent gates, wardrobe, and optional schedule/movement rules.
- **Character Card** — A compact runtime summary of a character (appearance, meters, gates, refusals) passed to the Writer for context.


### 3.2. State
Game state is the single source of truth. It includes:
- **Meters** — numeric values per player and NPC (trust, attraction, energy, etc.)  
- **Flags** — boolean or scalar values for progression (e.g. `emma_met`, `first_kiss`)  
- **Modifiers** — temporary or permanent effects (e.g., drunk, corrupted, aroused)  
- **Inventory** — items owned by the player or NPCs  
- **Clothing** — layered outfits with rules for removal, replacement, validation  
- **Location & Time** — hierarchical world, zones, locations, day/slot tracking  

### 3.3. Character Cards
Generated dynamically each turn from the state. They describe base appearance, outfit and clothing state, active modifiers, summarized meters (threshold labels), dialogue style, and current behavior gates.
Cards are passed to the Writer as context at each turn.

### 3.4.Narrative Flow
- **Nodes** define the authored story structure (scenes, interactive hubs, endings).  
- **Writer Model** produces freeform prose, respecting node type, state, and character cards.  
- **Checker Model** parses prose back into structured state deltas (meter changes, flags, clothing, etc.).  
- **Transitions** move the story between nodes, determined by authored conditions + Checker outputs.  

### 3.5. Two-Model Architecture
- **Writer**: Expands on authored beats, generates dialogue and prose, stays within style/POV constraints.  
- **Checker**: Strict JSON output, detects state changes, validates against rules, enforces consent & hard boundaries.  

Both models run each turn; their outputs are merged into the game state.  

---

## 4. Game Package & Manifest

### 4.1. Definition

A **game** is a single folder containing a primary manifest file `game.yaml`plus any optional, referenced YAML files. 
The manifest declares metadata, core config, and (optionally) a list of **includes**. 
This lets small games live in a single file, while bigger games split sections into multiple files — **without changing the schema**.

### 4.2. Folder Layout (required)

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
  # ...or any custom names you reference via include
```

### 4.3. Manifest Template - `game.yaml`
```yaml
# REQUIRED top-level fields
meta:
  id: "<string>"                 # REQUIRED. Stable game ID (folder-safe).
  title: "<string>"              # REQUIRED. Display title.
  version: "<semver>"            # REQUIRED. Content version (e.g., "1.0.0").
  authors: ["<string>", ...]     # REQUIRED. One or more authors.
  description: "<string>"        # OPTIONAL. Short blurb.
  content_warnings: ["<string>", ...]  # OPTIONAL. e.g., ["NSFW","strong language"]
  nsfw_allowed: true             # REQUIRED. Must be true for adult content.
  license: "<string>"            # OPTIONAL. e.g., "CC-BY-NC-4.0"

# Core narrative/time config (can be inline or split via includes)
time:
  mode: "<slots|clock|hybrid>"
  # ... see Time & Calendar section

world:
  # OPTIONAL. High-level world notes; often you’ll define zones/locations explicitly.
  # This is an author-facing context (ignored by engine).

# Narration style and engine hints
narration:
  pov: "<first|second|third>"
  tense: "<present|past>"
  paragraphs: "1-2"

rng_seed: "<int|auto>"         # OPTIONAL. For deterministic golden tests.

# Starting point (required so the game can boot)
start:
  location: { zone: "<zone_id>", id: "<location_id>" }
  node: "<node_id>"              # First node to enter after any entry_effects
  time:                          # Optional if derivable from time config
    day: 1
    slot: "morning"
    time: "08:00"

# Optional single-file sections (you may define small games here inline)
characters: [ ... ]              # See Characters
meters:                          # See Meters (player + character_template)
  player: { ... }
  character_template: { ... }
flags: { ... }                   # See Flags
modifier_system:                 # See Modifiers
  library: { ... }
items: [ ... ]                   # See Inventory & Items
actions: [ ... ]                 # See Actions
defaults: { ... }                # See Defaults
zones: [ ... ]                   # See Locations & Zones
movement: { ... }                # See Movement Rules
nodes: [ ... ]                   # See Nodes
events: [ ... ]                  # See Events
arcs: [ ... ]                    # See Arcs & Milestones

# Includes: pull in external files and merge their sections
# Each included file must declare recognized root keys (e.g., characters, nodes, zones).
# Unknown root keys cause a load error.
includes:
  - "characters.yaml"
  - "zones.yaml"
  - "items.yaml"
  - "actions.yaml"
  - "nodes_part1.yaml"
  - "nodes_part2.yaml"
  - "events.yaml"
  - "arcs.yaml"

```
**Example: included files (root keys = target sections)**
```yaml
# characters.yaml
characters:
  - id: "emma"  # ...
  - id: "liam"  # ...

# nodes_part1.yaml
nodes:
  - id: "intro_courtyard"   # ...
  - id: "player_room_idle"  # ...

# zones.yaml
zones:
  - id: "campus"
    locations: [ ... ]
```
### 4.4. Loader behavior (deterministic)

1. Load `game.yaml` (base).
2. For each file in `includes` (listed order), **load** and **merge** any **recognized root keys** it contains.
3. **Validate** after all merges:
    - Unique IDs within each list section (`characters`, `items`, `nodes`, `events`, `arcs`, `zones`).
    - Cross-refs resolve (node targets, item/outfit/location IDs, etc.).
    - Safety gates, time config sanity, start node/location exist.


### 4.5. Merge rules (section-aware)

- **Lists** (`characters`, `items`, `nodes`, `events`, `arcs`, `zones`): merged by id.
  - Duplicate `id` → error by default.
  - Optional override: in the included file, add a file-level directive:
    ```yaml
    __merge__:
      mode: "replace | append" 
    ```
    - `replace`: entries with the same id replace prior ones in that section.
    - `append`: (default) duplicate IDs error out.
- **Maps/objects** (`meters`, `flags`, `movement`, `modifier_system`, `defaults`, `time`, `start`, `meta`):
    - **Deep-merge** with **manifest** (`game.yaml`) winning on conflict.
    - `meta` and `start` are strongly recommended to live in `game.yaml` only; if present in includes, they **cannot remove required fields**.

### 4.6. Constraints & safety

- All included files must be inside the game folder; no `..`, no absolute paths, no URLs.
- **Known root keys only**; unknown roots cause a load error (helps catch typos).
- **No nested includes** inside included files (max depth = 1).
- Deterministic: same files → identical assembled game.

### 4.7. Authoring tips

- Small games: keep everything in **one** `game.yaml`.
 - Growing games: split by **natural sections** (`characters`, `nodes`, `events`, `arcs`, `zones`, `items`).
 - For huge node sets, shard into `nodes_partN.yaml` — the loader will merge them into nodes.
 - Avoid redefining `meta/time/start` outside `game.yaml` to keep entry clear.
 - If you must patch an entry from a prior include, add `__merge__.mode: "replace"` at the top of that file.

---

## 5. State overview

Game state is the single source of truth for everything that has happened in a game. 
It captures the current snapshot of the world, characters, and story progression, 
and it is the structure that both the Writer and Checker operate at each turn.

The state is:
- **Author-driven** — all meters, flags, items, and arcs must be defined in the game’s YAML configuration.
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
## 6. Expression DSL (Conditions)

### 6.1. Purpose
A small, safe, deterministic expression language used anywhere the spec accepts a condition 
(e.g., node `preconditions`, effect `when`, event triggers, outfit `unlock_when`, 
flag `reveal_when`, arc `advance_when`).

### 6.2. Syntax (EBNF-style)
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

### 6.3. Types & Truthiness
- Types: **boolean**, **number**, **string**, **list** (homogenous recommended).
- Falsey: `false`, `0`, `""`, `[]`. Everything else is truthy.
- Short-circuit: `and`/`or` evaluate left→right with short-circuit.

### 6.4. Operators

- Comparison: `== != < <= > >=`
- Boolean: `and or not`
- Arithmetic: `+ - *` / (numbers only)
- Membership: `X in ["a","b"]` or `time.slot in ["evening","night"]`

### 6.5. Path Access

- Dotted or bracketed: `meters.emma.trust`, `flags["first_kiss"]`
- **Safe resolution**: Missing paths evaluate to `null` (falsey). They **never throw**.
- For dynamic paths, use `get("flags.route_locked", false)`.


### 6.6. Built-in Functions

- `has(item_id)` → bool (player inventory)
- `npc_present(npc_id)` → bool (NPC currently in same location)
- `rand(p)` → bool (Bernoulli; `0.0 ≤ p ≤ 1.0`; seeded per turn)
- `min(a,b)`, `max(a,b)`, `abs(x)`
- `clamp(x, lo, hi)`
- `get(path_string, default)` → safe lookup (e.g., `get("meters.emma.trust", 0)`)

### 6.7. Constraints & Safety

- No assignments, no user-defined functions, no I/O, no imports, no eval.
- Strings must be **double-quoted**.
- Division by zero → expression is false (and the engine logs a warning).
- Engine enforces **length & nesting caps** to prevent abuse.

### 6.8. Examples
```yaml
"meters.emma.trust >= 50 and gates.emma.accept_date"
"time.slot in ['evening','night'] and rand(0.25)"
"has('flowers') and location.privacy in ['medium','high']"
"arcs.emma_corruption.stage in ['experimenting','corrupted']"
"get('flags.protection_available', false) == true"
```

### 6.9. Runtime Variables (Condition Context)

All conditions are evaluated against a read-only **turn context** built by the engine.
The following variables and namespaces are available:

#### Time & Calendar
- `time.day` (int) — narrative day counter (≥1)
- `time.slot` (string) — current slot (e.g., "morning")
- `time.time_hhmm` (string) — "HH:MM" in clock/hybrid modes
- `time.weekday` (string) — e.g., "monday"

#### Location
- `location.zone` (string) — zone id
- `location.id` (string) — location id
- `location.privacy` (enum) — none | low | medium | high

#### Characters & Presence
- `characters` (list of ids) — NPC ids known in game
- `present` (list of ids) — NPC ids present in current location
  - Prefer `npc_present('emma')` for clarity.

#### Meters
- `meters.player.<meter_id>` (number)
- `meters.<npc_id>.<meter_id>` (number)
  - Example: `meters.emma.trust`, `meters.player.energy`

#### Flags
- `flags.<flag_key>` — boolean/number/string (as defined)
  - Example: `flags.first_kiss == true`

#### Modifiers (active)
- `modifiers.player` (list[string]) — active modifier ids
- `modifiers.<npc_id>` (list[string])
  - Often checked via gates or effects rather than here.

#### Inventory
- `inventory.player.<item_id>` (int count)
- `inventory.<npc_id>.<item_id>` (int count)
  - Prefer `has('flowers')` for player possession checks.

#### Clothing (runtime state)
- `clothing.<npc_id>.layers.<layer_id>` — `"intact" | "displaced" | "removed"`
- `clothing.<npc_id>.outfit` — current outfit id

#### Gates (consent/behavior)
- `gates.<npc_id>.<gate_id>` (bool)
  - Gate values are derived from meters/flags/privacy; use this instead of re-implementing checks.
  - Example: `gates.emma.accept_kiss`

#### Arcs
- `arcs.<arc_id>.stage` (string) — current stage id
- `arcs.<arc_id>.history` (list[string]) — prior stages

#### Player
- `player.energy` (number) — convenience mirror of meters.player.energy if configured
- Additional mirrored fields may exist per game config (document them if added).

### 6.10. Authoring Guidelines
- Prefer checking **gates** (`gates.emma.accept_kiss`) over raw meter math for consent/NSFW.
- Keep expressions short; move complexity into flags/arcs or precomputed gates.
- Use `get(...)` when a path might not exist yet (e.g., optional flags).
- Randomness: use `rand(p)` sparingly and only where replay determinism is acceptable.

### 6.11. Validation & Errors
- Unknown variables/paths → resolve to `null` (falsey) and log a warning in dev builds.
- Type errors (e.g., `"foo" + 1`) → expression evaluates false; warning logged.
Exceeding size/nesting caps → expression rejected at a load or first evaluation.


---
## 7. Characters

### 7.1. Definition
A **character** is any entity (NPC or player avatar) that participates in the story. 
Characters are defined in YAML with **identity**, **meters**, **consent gates**, **wardrobe**, and **availability**.

Characters cannot exist without a valid `id`, `name`, and `age`. 
All other aspects (meters, outfits, behaviors) are optional but strongly recommended.

Characters provide the core state the Writer and Checker operate on: they drive interpersonal progression, gating, and narrative consistency

### 7.2. Character Template
```yaml
# Character definition lives under: characters: [ ... ]
- id: "<string>"                  # REQUIRED. Unique stable ID.
  name: "<string>"                # REQUIRED. Display name.
  age: <int>                      # REQUIRED. Must be >= 18.
  gender: "<string>"              # OPTIONAL. Free text or enum ("female","male","nonbinary").
  description: "<string>"         # OPTIONAL. Author-facing description (cards, logs).
  tags: ["<string>", ...]         # OPTIONAL. Semantic labels (e.g., "shy","athletic").

  # --- Meters (per-character) ---
  meters:                         # OPTIONAL. Overrides / additions to character_template meters.
    trust: { min: 0, max: 100, default: 10 }
    attraction: { min: 0, max: 100, default: 0 }
    arousal: { min: 0, max: 100, default: 0 }
    boldness: { min: 0, max: 100, default: 20 }

  # --- Flags (per-character) ---
  flags:                          # OPTIONAL. Scoped flags which are unique to this character.
    met_player: { type: "bool", default: false }

# --- Consent & behavior ---
  behaviors:                        # REQUIRED for NSFW characters.
    gates:                          # A list of consent/behavior gates.
      - id: "<string>"              # REQUIRED. The unique ID for the gate (e.g., "accept_kiss").
        when: "<expr>"              # OPTIONAL. A single condition that must be true.
        when_any: ["<expr>", ...]   # OPTIONAL. A list of conditions where at least one must be true.
        when_all: ["<expr>", ...]   # OPTIONAL. A list of conditions where all must be true.
    refusals:                       # OPTIONAL. Templated responses for when a gate fails.
      generic: "<string>"
      low_trust: "<string>"
      wrong_place: "<string>"

  # --- Wardrobe ---
  wardrobe:                       # OPTIONAL. See the Clothing & Wardrobe section.
    rules:
      layer_order: ["outerwear","top","bottom","feet","underwear_top","underwear_bottom"]
    outfits: [ ... ]

  # --- Schedule & availability ---
  schedule:                       # OPTIONAL. Controls where the character is by time/day.
    - when: "time.slot == 'morning'"
      location: "library"
    - when: "time.slot == 'night'"
      location: "dorm_room"

  # --- Movement willingness ---
  movement:                       # OPTIONAL. Rules for following player to other zones/locations.
    willing_zones:
      - { zone: "campus", when: "always" }
      - { zone: "downtown", when: "meters.{id}.trust >= 50" }
    willing_locations:
      - { location: "player_room", when: "meters.{id}.trust >= 40" }

  # --- Inventory (per-character) ---
  inventory:                      # OPTIONAL. Items carried by this character.
    flowers: 1

  # --- Author notes ---
  author_notes: "<string>"        # OPTIONAL. For writers/testers only.

```

### 7.3. Runtime State (excerpt)
```yaml
state.characters:
  emma:
    meters: { trust: 45, attraction: 35, arousal: 10, boldness: 20 }
    flags: { met_player: true }
    outfit: "casual_day"
    clothing:
      top: "intact"
      bottom: "intact"
      underwear_top: "intact"
      underwear_bottom: "intact"
    modifiers: []
    location: "library"
```
### 7.4. Example Character
```yaml
- id: "emma"
  name: "Emma Chen"
  age: 19
  gender: "female"
  description: "A shy and conservative literature student, gradually opening up."
  tags: ["student","shy","conservative"]

  meters:
    trust:      { min: 0, max: 100, default: 10 }
    attraction: { min: 0, max: 100, default: 0 }
    arousal:    { min: 0, max: 100, default: 0 }
    boldness:   { min: 0, max: 100, default: 20 }

  behaviors:
    gates:
      - id: "accept_date"
        when: "meters.emma.trust >= 30"
      - id: "accept_kiss"
        when_any:
          - "meters.emma.trust >= 40 and meters.emma.attraction >= 30"
          - "meters.emma.corruption >= 40" # Example of an alternative path
      - id: "accept_sex"
        when_all:
          - "meters.emma.trust >= 70"
          - "meters.emma.attraction >= 70"
          - "meters.emma.arousal >= 50"
          - "location.privacy == 'high'"
    refusals:
      generic: "She pulls back, cheeks warm. 'Not yet.'"
      low_trust: "She shakes her head. 'Slow down… please.'"
      wrong_place: "She glances around. 'Not here.'"
  
  wardrobe:
    outfits:
      - id: "casual_day"
        name: "Casual Outfit"
        layers:
          top: { item: "tank top", color: "white" }
          bottom: { item: "jeans", style: "skinny" }
          underwear_top: { item: "bra", style: "plain" }
          underwear_bottom: { item: "panties", style: "cotton" }

  schedule:
    - when: "time.slot == 'morning'"
      location: "library"
    - when: "time.slot == 'night'"
      location: "dorm_room"
```
### 7.5. Authoring Guidelines

- **Always set** `age >= 18` — validation rejects underage characters.
- Define **gates explicitly**: they control intimacy and prevent unsafe AI output.
- Use **character-scoped meters** sparingly; prefer template defaults unless diverging.
- Keep wardrobe minimal unless outfits are narratively important.
- Use **schedule** for predictable presence; events can override temporarily.
- For romance/NSFW arcs, define **both trust and attraction** as core meters.
- Gates use the Expression DSL (see ‘Expression DSL & Condition Context’).

---

## 8. Meters

### 8.1. Definition

A **meter** is a numeric variable that tracks a continuous aspect of the player or an NPC. 
Meters represent qualities such as trust, attraction, energy, health, arousal, or corruption. 
They are:
- **Bounded** — every meter has min, max, and a default value.
- **Visible** or **hidden** — some are shown in the UI, others stay hidden until conditions reveal them.
- **Thresholded** — meters can define labeled ranges (e.g., stranger → friend → intimate) for easier gating and narrative logic.
- **Dynamic** — values can change through authored effects, Checker deltas, or automatic decay/growth rules.
- **Central to gating** — NPC behavior gates often check meter thresholds to decide whether an action is allowed.

Meters are always defined in the game configuration and are validated at load time.

```yaml
# Single Meter Definition (template)
# Place under: meters.player.<id> or meters.character_template.<id>

<meter_id>:
  min: <int>            # REQUIRED. Absolute floor (inclusive).
  max: <int>            # REQUIRED. Absolute ceiling (inclusive). Must be > min.
  default: <int>        # REQUIRED. Initial value. Must be within [min, max].

  # --- Visibility & UI ---
  visible: <bool>       # OPTIONAL. Default: true for player meters, false for hidden NPC meters.
  hidden_until: "<expr>"# OPTIONAL. Expression DSL. When true, the meter may be shown in UI/logs.
  icon: "<string>"      # OPTIONAL. Short icon/emoji or UI key, e.g., "⚡" or "heart".
  format: "<enum>"      # OPTIONAL. UI hint: "integer" (default) | "percent" | "currency".

  # --- Behavior & Dynamics ---
  decay_per_day: <int>  # OPTIONAL. Applied at day rollover; negative = decay, positive = regen.
  delta_cap_per_turn: <int>  # OPTIONAL. Max absolute change allowed per turn for this meter.
                             # Overrides any game-wide default cap for this meter only.

  # --- Threshold Labels (authoring sugar) ---
  thresholds:           # OPTIONAL. Labeled ranges for gating & cards. Non-overlapping, ordered.
    <label_a>: [<int_lo>, <int_hi>]  # inclusive bounds; must lie within [min, max]
    <label_b>: [<int_lo>, <int_hi>]

  # --- Notes (author-facing only; ignored by engine) ---
  description: "<string>"   # OPTIONAL. Brief author guidance about meaning and usage.

```
### 8.2. Example (NPC meter)
```yaml
meters:
  character_template:
    trust:
      min: 0
      max: 100
      default: 10
      thresholds:
        stranger: [0, 19]
        acquaintance: [20, 39]
        friend: [40, 69]
        close: [70, 89]
        intimate: [90, 100]
      delta_cap_per_turn: 3
      description: "Social comfort with the player; drives access to dates/kissing."
```

---

## 9. Flags

### 9.1. Definition
A **flag** is a small, named piece of state that marks discrete facts or progress (met someone, completed a step, 
unlocked a route, etc.). Flags are lightweight, easy to query in conditions, and are validated at load time. 
They can be boolean, number, or string, but should remain simple and stable over a whole run.

```yaml
# Single Flag Definition (template)
# Place under: flags.<flag_key>

<flag_key>:
  type: "<enum>"         # REQUIRED. One of: "bool" | "number" | "string".
  default: <value>       # REQUIRED. Initial value (must match 'type').

  # --- Visibility & UI ---
  visible: <bool>        # OPTIONAL. Show in debug/author UIs. Default: false.
  label: "<string>"      # OPTIONAL. Human-friendly name for tools/docs.
  description: "<string>"# OPTIONAL. Author note on what this flag means.

  # --- Lifecycle ---
  sticky: <bool>         # OPTIONAL. If true, persists across some resets/checkpoints (tooling hook).
  reveal_when: "<expr>"  # OPTIONAL. Expression DSL; when true, UI may show this flag.

  # --- Validation (optional helpers) ---
  allowed_values:        # OPTIONAL. Only for string/number; reject values outside this set/range.
    - <valueA>
    - <valueB>
```

### 9.2. Constraints & Notes

- **Types**:
  - bool → true / false
  - number → integer (prefer) or limited-range numeric
  - string → short identifiers; consider allowed_values for stability
- **Naming**: use clear, stable keys (e.g., `emma_met`, `route_locked`, `first_kiss`).
- **Usage**: reference in expressions like `flags.first_kiss == true` or `flags.route_locked != true`.
- **Scope**: flags are **global** ; if you need NPC-scoped facts, either prefix (`emma_*`) or use NPC's meters.

### 9.3. Examples

```yaml
flags:
  emma_met:
    type: "bool"
    default: false
    visible: true
    label: "Met Emma"
    description: "Set true after the first introduction scene."

  first_kiss:
    type: "bool"
    default: false
    description: "Marks the first successful kiss with Emma."

  route_locked:
    type: "bool"
    default: false
    description: "Prevents switching arcs once a route is committed."

  study_reputation:
    type: "string"
    default: "neutral"
    allowed_values: ["bad","neutral","good","excellent"]
    description: "Lightweight reputation tag shown in some dialogue branches."
```

**Typical conditions**

```yaml
"flags.emma_met == true and time.slot in ['evening','night']"
"flags.first_kiss == true or meters.emma.attraction >= 60"
"flags.study_reputation in ['good','excellent']"
```

---

## 10. Modifiers

### 10.1. Definition
A **modifier** is a named, (usually) temporary state that overlays appearance/behavior rules 
without directly rewriting canonical facts. Think **aroused**, **drunk**, **injured**, **tired**.
Modifiers can auto-activate from conditions, be applied/removed by effects, stack or exclude each other, 
and may carry a default duration. They influence gates, dialogue tone, and presentation 
but don’t invent hard state changes by themselves.

> Modifiers live in a game definition and appear in runtime state only when active.

```yaml
# Single Modifier Definition (template)
# Place under: modifier_system.library.<modifier_id>

<modifier_id>:
  # --- Identity ---
  group: "<string>"          # OPTIONAL but recommended. Category for stacking/exclusions (e.g., "intoxication", "emotional").
  tags: ["<string>", ...]    # OPTIONAL. Freeform labels for tools/search.

  # --- Activation ---
  when: "<expr>"             # OPTIONAL. Auto-activation condition (evaluated each turn).
  duration_default_min: <int># OPTIONAL. Default runtime duration in minutes when applied without explicit duration.

  # --- Appearance & Behavior overlays (soft influence) ---
  appearance:                # OPTIONAL. Small deltas for cards/descriptions; never hard state edits.
    <key>: <string>          # e.g., cheeks: "flushed", eyes: "glossy"

  behavior:                  # OPTIONAL. Biases for Writer/engine heuristics (not mandatory to render).
    dialogue_style: "<string>"   # e.g., "breathless", "slurred"
    inhibition: <int>            # integer bias; engine/tooling interpret consistently
    coordination: <int>          # integer bias
    # adds other numeric/text knobs as your game defines

  # --- Safety & Gates (hard constraints) ---
  safety:                    # OPTIONAL. Hard limits that the engine enforces.
    disallow_gates: ["<gate_id>", ...]  # e.g., forbid "accept_sex" while drunk
    allow_gates: ["<gate_id>", ...]     # rarely used; prefer arcs/gates unless tightly controlled

  # --- Systemic Rules ---
  clamp_meters:              # OPTIONAL. Enforce temporary boundaries on meters while active.
    <meter_id>: { min: <int>, max: <int> } # e.g., arousal: { max: 60 }

  # --- One-shot hooks (optional sugar) ---
  entry_effects:             # OPTIONAL. Apply once when the modifier becomes active.
    - { type: <effect_type>, ... }
  exit_effects:              # OPTIONAL. Apply once when it ends.

  # --- Author notes ---
  description: "<string>"    # OPTIONAL. Short guidance for authors/tools. Not shown to players.

```
### 10.2. System-Level Controls (where these live)
Defined once under **modifier_system**, not per modifier:
```yaml
modifier_system:
  stacking:
    default: "highest"             # how multiple modifiers in the same group combine: highest|additive|multiplicative
    per_group:
      intoxication: "highest"
      emotional: "additive"

  exclusions:
    - group: "intoxication"        # only one intoxication modifier can be active at a time
      exclusive: true

  priority:
    groups:
      - name: "status"             # evaluation/rendering priority
        priority: 100
        members: ["unconscious","paralyzed"]
```
### 10.3. Constraints & Notes
- **Source of truth**: modifiers overlay behavior/appearance; use **effects** if you need concrete state changes (meters, flags, clothing).
- **Activation**: a modifier can be **auto-activated** by `when` each turn, or explicitly applied via an effect:
```yaml
- type: apply_modifier
  character: "<npc_id>|player"
  modifier_id: "<modifier_id>"
  duration_min: <int>     # optional override
 
```
Remove with:
```yaml
- type: remove_modifier
  character: "<npc_id>|player"
  modifier_id: "<modifier_id>"
```
- **Duration**: ticks down in minutes/turns depending on your time mode; expires → runs exit_effects (if any).
- **Stacking**: group strategy decides how same-group modifiers combine; use exclusions to forbid coexistence.
- **Safety**: safety.disallow_gates always wins; the engine blocks those actions even if prose suggests them.
- **Determinism**: evaluation happens in the standard turn order (after safety checks, before/after effects as specified in your engine), ensuring replayable outcomes.

### 10.4. Examples
```yaml
modifier_system:
  library:
    aroused:
      group: "emotional"
      when: "meters.{character}.arousal >= 40"
      appearance: { cheeks: "flushed" }
      behavior:
        dialogue_style: "breathless"
        inhibition: -1
      description: "Heightened desire; softens refusals but doesn’t bypass consent."

    drunk:
      group: "intoxication"
      duration_default_min: 120
      appearance: { eyes: "glossy" }
      behavior: { inhibition: -3, coordination: -2 }
      safety:
        disallow_gates: ["accept_sex"]   # hard stop while intoxicated
      description: "Impaired judgment/coordination; blocks sex gates."

    injured_light:
      group: "status"
      duration_default_min: 240
      behavior: { coordination: -1 }
      entry_effects:
        - { type: meter_change, target: "player", meter: "energy", op: "subtract", value: 10 }
      exit_effects:
        - { type: flag_set, key: "injury_healed", value: true }
      description: "Minor injury; drains energy and slows actions."

```

---

## 11. Inventory & Items

### 11.1. Definition

An **item** is a defined object (gift, key, consumable, equipment, trophy, etc.) that can be owned 
by the player or NPCs. The inventory is the per-owner mapping of item IDs to counts 
(and, if needed, equipment slots). Items are the canonical way to model concrete affordances—buying, 
gifting, unlocking doors, consuming potions—while flags remain for abstract progress. 
Items and inventory are declared in game YAML and validated at load time.

```yaml
# Single Item Definition (template)
# Place under: items: [ ... ]  (list of item objects)

- id: "<string>"                # REQUIRED. Stable unique ID (kebab/snake case).
  name: "<string>"              # REQUIRED. Display name.
  category: "<enum>"            # REQUIRED. "consumable" | "equipment" | "key" | "gift" | "trophy" | "misc"

  # --- Presentation & Classification ---
  description: "<string>"       # OPTIONAL. Short author-facing/player-visible description.
  tags: ["<string>", ...]       # OPTIONAL. Freeform labels for search/filters (e.g., ["romance","rare"]).
  icon: "<string>"              # OPTIONAL. UI hint (emoji or asset key).

  # --- Economy (optional) ---
  value: <int>                  # OPTIONAL. Shop/economy price; non-negative.
  stackable: <bool>             # OPTIONAL. Default: true. If false, each unit is unique.
  droppable: <bool>             # OPTIONAL. Default: true.

  # --- Usage semantics (optional) ---
  consumable: <bool>            # OPTIONAL. If true, the item is destroyed on use.
  target: "<enum>"              # OPTIONAL. "player" | "character" | "any" (who it can be used on).
  use_text: "<string>"          # OPTIONAL. Flavor text when used.
  effects_on_use:               # OPTIONAL. Effects applied when used; see Effects catalog.
    - { type: <effect_type>, ... }

  # --- Gifting (optional) ---
  can_give: <bool>              # OPTIONAL. If true, the item can be gifted via choices/UI.
  gift_effects:                 # OPTIONAL. Effects applied when gifted (often NPC-specific).
    - { type: <effect_type>, ... }

  # --- Unlocks / Keys (optional) ---
  unlocks:                      # OPTIONAL. Declarative helper for keys/passes.
    location: "<location_id>"   # Example: unlock a location/door.
    # You may extend with: outfit, feature, node, etc. (tooling hooks)

  # --- Equipment (optional) ---
  slots: ["<slot_id>", ...]     # OPTIONAL. Valid equipment slots if category == "equipment"
  stat_mods:                    # OPTIONAL. Numeric biases while equipped (engine/tooling defined).
    <meter_id>: <int>

  # --- Acquisition constraints (optional) ---
  obtain_conditions:            # OPTIONAL. Expression DSL list; all must pass to obtain.
    - "<expr>"

  # --- Notes (ignored by engine) ---
  author_notes: "<string>"      # OPTIONAL. Guidance for writers/testers.

```

### 11.2. Constraints & Notes

- `id` must be unique across all items; referenced by inventory, nodes, effects.
- Use **effects** to model concrete outcomes (money change, meter changes, flags) on use/gift.
- Prefer **keys/unlocks** for access gating; use flags only if no physical artifact is desired.
- Keep `description` concise; long lore should live in node prose.


### 11.3. Inventory structure

```yaml
# Where inventories live at runtime (state)
# owners: "player" and any NPC id

state:
  inventory:
    player:
      <item_id_A>: <int_count>         # e.g., flowers: 1
      <item_id_B>: <int_count>
    <npc_id>:
      <item_id_C>: <int_count>

  equipment:                           # OPTIONAL runtime map if using equipment
    player:
      <slot_id>: "<item_id_or_null>"   # e.g., outfit: "formal_suit"
    <npc_id>:
      <slot_id>: "<item_id_or_null>"
```

Effects that mutate inventory (authorable + Checker deltas):

```yaml
- { type: inventory_add,    owner: "player|<npc_id>", item: "<item_id>", count: 1 }
- { type: inventory_remove, owner: "player|<npc_id>", item: "<item_id>", count: 1 }
```

### 11.4. Examples

#### Gift item

```yaml
- id: "flowers"
  name: "Bouquet of Flowers"
  category: "gift"
  value: 20
  stackable: true
  can_give: true
  gift_effects:
    - { type: meter_change, target: "emma", meter: "attraction", op: "add", value: 10 }
    - { type: flag_set, key: "emma_received_flowers", value: true }
```

#### Key item

```yaml
- id: "dorm_key"
  name: "Dorm Key"
  category: "key"
  droppable: false
  unlocks: { location: "dorm_room" }
```

#### Consumable with on-use effects

```yaml
- id: "energy_drink"
  name: "Energy Drink"
  category: "consumable"
  consumable: true
  target: "player"
  use_text: "You crack the can and chug the sweet, fizzy boost."
  effects_on_use:
    - { type: meter_change, target: "player", meter: "energy", op: "add", value: 25 }
```

#### Equipment with slot + stat mod

```yaml
- id: "lucky_charm"
  name: "Lucky Charm"
  category: "equipment"
  slots: ["accessory"]
  stat_mods:
    boldness: 5
```

---

## 12. Clothing & Wardrobe

### 12.1. Definition
The **clothing system** represents what characters wear, how outfits are composed, and how layers can change
state during play. Clothing provides narrative grounding (outfits described in prose), 
mechanical gating (privacy, consent, embarrassment), and state tracking (layer `intact` / `displaced` / `removed`).


Wardrobe definitions live in the `characters` node under each NPC (and optionally the player), 
with a shared ontology of layers. Runtime state tracks which outfit is equipped and the state of each layer.

**Single outfit**
```yaml
# Outfit definition lives under: characters[].wardrobe.outfits[]
- id: "<string>"                 # REQUIRED. Stable outfit ID for reference/unlocks.
  name: "<string>"               # REQUIRED. Display name.
  tags: ["<string>", ...]        # OPTIONAL. Semantic labels (e.g., "casual","sexy","formal").
  description: "<string>"        # OPTIONAL. Author notes (not shown verbatim to players).

  # --- Unlock rules ---
  unlock_when: "<expr>"          # OPTIONAL. Expression DSL; if true, outfit becomes selectable.
  locked: <bool>                 # OPTIONAL. Default false. Explicit lock toggle.

  # --- Clothing layers ---
  layers:                        # REQUIRED. Ontology must match the game. See the example below.
    outerwear:       { item: "<string>", color: "<string>", style: "<string>" }
    dress:           { item: "<string>", color: "<string>", style: "<string>" }
    top:             { item: "<string>", color: "<string>", style: "<string>" }
    bottom:          { item: "<string>", color: "<string>", style: "<string>" }
    feet:            { item: "<string>", style: "<string>" }
    underwear_top:   { item: "<string>", style: "<string>" }
    underwear_bottom:{ item: "<string>", style: "<string>" }
    accessories:     ["<string>", ...]   # OPTIONAL. Non-layer items (choker, glasses, etc.)
```

**Wardrobe System**
```yaml
wardrobe:
  rules:
    layer_order: ["outerwear","dress","top","bottom","feet","underwear_top","underwear_bottom","accessories"]
    required_layers: ["top","bottom","underwear_top","underwear_bottom"]   # engine checks presence
    removable_layers: ["outerwear","dress","top","bottom","feet","accessories"]
    sexual_layers: ["underwear_top","underwear_bottom"]  # layers relevant for intimacy checks

  outfits: [ ... see above ... ]
```
### 12.2. Clothing State (runtime)
At runtime, each character has:
```yaml
state.clothing:
  <npc_id>:
    outfit: "<outfit_id>"           # currently equipped outfit
    layers:
      outerwear: "intact"           # intact | displaced | removed
      top:       "intact"
      bottom:    "displaced"
      underwear_top: "intact"
      underwear_bottom: "removed"
```

### 12.3. Clothing Effects
Clothing changes are expressed through standard Effects (`outfit_change` and `clothing_set`), see Effects catalog.

**Rules**
- **Consent gates** + **privacy** enforced before applying. If blocked → effect ignored, refusal line triggered.
- **Wardrobe rules** ensure mandatory layers exist and respect layer order.
- **Engine validation**: unknown layers/outfits rejected.

### 12.4. Example
```yaml
characters:
  - id: "emma"
    name: "Emma Chen"
    wardrobe:
      rules:
        layer_order: ["outerwear","dress","top","bottom","feet","underwear_top","underwear_bottom","accessories"]
      outfits:
        - id: "casual_day"
          name: "Casual Outfit"
          tags: ["everyday","modest"]
          layers:
            outerwear: { item: "hoodie", color: "gray" }
            top:       { item: "tank top", color: "white" }
            bottom:    { item: "jeans", style: "skinny" }
            feet:      { item: "sneakers" }
            underwear_top:    { item: "bra", style: "t-shirt" }
            underwear_bottom: { item: "panties", style: "bikini" }
            accessories: ["glasses"]

        - id: "bold_outfit"
          name: "Bold Outfit"
          unlock_when: "meters.emma.corruption >= 40 or meters.emma.boldness >= 60"
          layers:
            top: { item: "crop top", color: "black" }
            bottom: { item: "mini skirt", color: "red" }
            feet: { item: "heels" }
            underwear_top: { item: "push-up bra", style: "lace" }
            underwear_bottom: { item: "thong", style: "g-string" }
            accessories: ["choker"]

```
### 12.5. Authoring Guidelines
- Always provide at least one **default outfit** per character.
- Use `unlock_when` for narrative progression (e.g., bold/corrupted outfits).
- Keep **layer ontology consistent** across all characters.
- Treat **clothing removal/displacement** as state, not narrative fluff — prose must match state.
- For NSFW: intimate acts require underwear layers `removed` or `displaced`, **plus** consent gates and privacy = high.

---

## 13. Effects

### 13.1. Definition

An **effect** is an atomic, declarative instruction that changes the game state. Effects are:
- **Deterministic** — applied in order, validated against schema.
- **Declarative** — authors describe what changes, not how.
- **Guarded** — can include a `when` condition (expression DSL).
- **Validated** — invalid or disallowed effects are ignored and logged.

Effects can be authored in nodes, events, arcs, milestones, or items. The Checker may also emit effects as JSON deltas, which are merged into the same pipeline

```yaml
# Single Effect Definition (template)
- type: "<enum>"            # REQUIRED. Effect kind (see catalog below).
  when: "<expr>"            # OPTIONAL. Guard condition (DSL). Default: "always".

  # Fields depend on type.
```
### 13.2. Catalog of Effect Types

#### Meter change
```yaml
- type: meter_change
  target: "player | <npc_id>"
  meter: "<meter_id>"
  op: "add | subtract | set | multiply | divide"
  value: <int>
  respect_caps: true    # OPTIONAL. Default: true (clamp to min/max).
  cap_per_turn: true    # OPTIONAL. Default: true (respect delta caps).

```

#### Flag set
```yaml
- type: flag_set
  key: "<flag_key>"
  value: true | false | number | string

```

#### Inventory
```yaml
- type: inventory_add
  owner: "player | <npc_id>"
  item: "<item_id>"
  count: <int> =1

- type: inventory_remove
  owner: "player | <npc_id>"
  item: "<item_id>"
  count: <int> =1
```
#### Modifiers
````yaml
- type: outfit_change
  character: "<npc_id>"
  outfit: "<outfit_id>"

- type: clothing_set
  character: "<npc_id>"
  layer: "<layer_id>"       # top | bottom | underwear_top | ...
  state: "intact | displaced | removed"

````
> Engine enforces privacy + consent; disallowed changes are ignored and logged

#### Movement & Time
```yaml
- type: move_to
  location: "<location_id>"
  with_characters: ["<npc_id>", ...]   # consent checked

- type: advance_time
  minutes: <int>
```

#### Flow control
```yaml
- type: goto_node
  node: "<node_id>"

- type: conditional
  when: "<expr>"
  then: [ <effects...> ]
  else: [ <effects...> ]

- type: random
  choices:
    - weight: <int>
      effects: [ <effects...> ]
    - weight: <int>
      effects: [ <effects...> ]
```
#### Unlocks & Utilities
```yaml
- type: unlock_outfit
  character: "<npc_id>"
  outfit: "<outfit_id>"

- type: unlock_actions
  actions: ["<action_id>", ...]

- type: unlock_ending
  ending: "<ending_id>"

```
### 13.3. Execution Order (per turn)

1. **Safety gates** (hard rules, consent).
2. **Node entry_effects** / **event effects** (in order).
3. **Checker deltas** (validated, clamped).
4. **Modifiers resolution** (activation, expiry, stacking).
5. **Advance time** (explicit or defaults).
6. **Node transitions** (forced `goto` → authored `transitions` → fallback).

### 13.4. Constraints & Notes

- Conditions use the Expression DSL.
- Unknown `type` or invalid fields → effect rejected, log warning.
- Invalid references (unknown meter/item/npc/location) → effect rejected.
- `when` guard false → effect skipped silently.
- All randomness is seeded deterministically (`game_id + run_id + turn_index`) for replay stability.
- Effects **must not bypass consent/NSFW rules**; if violated, they are dropped, and refusal text is triggered.

### 13.5. Examples
**Trust boost or penalty**
```yaml
- type: conditional
  when: "player.polite == true"
  then:
    - { type: meter_change, target: "emma", meter: "trust", op: "add", value: 2 }
  else:
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
## 14. Actions

### 14.1. Definition

An Action is a globally defined, reusable player choice that can be unlocked through effects. 
Unlike node-based `choices` which are tied to a specific scene, 
unlocked actions can become available to the player in any context, provided their conditions are met. 
This allows for character growth and new abilities that persist across the game.

Actions are defined in a top-level `actions` list, typically in an `actions.yaml` file.


### 14.2. Action Template

```yaml
# Action definition lives under: actions: [ ... ]
- id: "<string>"                  # REQUIRED. Unique stable ID for unlocking.
  prompt: "<string>"              # REQUIRED. The text shown to the player.
  category: "<string>"            # OPTIONAL. UI hint (e.g., "conversation", "romance").
  conditions: "<expr>"            # OPTIONAL. Expression DSL. Action is only available if true.
  effects: [ <effects...> ]       # OPTIONAL. Effects applied when the action is chosen.
```
### 14.3. Example

```yaml
# actions.yaml
actions:
  - id: "deep_talk_emma"
    prompt: "Ask Emma about her family"
    category: "conversation"
    conditions: "npc_present('emma') and meters.emma.trust >= 60"
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


## 15. Locations & Zones

### 15.1. Definition
The world model is hierarchical:
- **Zones**: broad narrative areas (e.g., Campus, Downtown).
- **Locations**: discrete places within zones (e.g., Library, Dorm Room).

Locations carry **privacy levels** (public → private), **discovery state**, **access rules**, and **connections**.
Zones may define **transport options** and **events** tied to entering or exploring.

This model allows authored content to target specific areas and the engine to enforce rules 
for **movement**, **privacy**, **discovery**, and **NPC willingness**.

### 15.2. Zone template
```yaml
# Zone definition lives under: zones: [ ... ]
- id: "<string>"                  # REQUIRED. Unique stable zone ID.
  name: "<string>"                # REQUIRED. Display name.
  discovered: <bool>              # OPTIONAL. Default false.
  accessible: <bool>              # OPTIONAL. Default true.
  tags: ["<string>", ...]         # OPTIONAL. Semantic classification ("urban","safe").
  properties:                     # OPTIONAL. Zone-level descriptors.
    size: "<string>"              # e.g., "small","medium","large"
    security: "<string>"          # free text or enum
    privacy: "<enum>"             # none | low | medium | high (default: low)

  # --- Transport & travel ---
  transport_connections:          # OPTIONAL. Travel routes between zones.
    - to: "<zone_id>"
      methods: ["bus","car","walk"]
      distance: <int>             # narrative distance (time cost multiplier)

  # --- Inline locations (see below) ---
  locations: [ ... ]

```
### 15.3. Location template
```yaml
# Location definition lives under: zones[].locations[]
- id: "<string>"                  # REQUIRED. Unique stable location ID (zone-local).
  name: "<string>"                # REQUIRED. Display name.
  type: "<string>"                # OPTIONAL. "public","private","special". For author use.
  privacy: "<enum>"               # REQUIRED. none | low | medium | high
  discovered: <bool>              # OPTIONAL. Default false.
  hidden_until_discovered: <bool> # OPTIONAL. Default false (UI hint).
  tags: ["<string>", ...]         # OPTIONAL. Narrative classification.

  # --- Access & discovery ---
  discovery_conditions:           # OPTIONAL. Expressions; if true, location is revealed.
    - "<expr>"
  access:
    locked: <bool>                # OPTIONAL. Default false.
    unlocked_when: "<expr>"       # OPTIONAL. Expression DSL. If true, the location is unlocked.

  # --- Connections (intra-zone travel) ---
  connections:
    - to: "<location_id>"         # target location in the same zone
      type: "<enum>"              # door | street | path | teleport
      distance: "<enum>"          # immediate | short | medium | long
      bidirectional: <bool>=true

  # --- Features (sub-areas, optional) ---
  features: ["<string>", ...]     # e.g., "bed","desk","stage"

  # --- Events (optional) ---
  events:
    on_first_enter:
      narrative: "<string>"
      effects: [ <effects...> ]

```
### 15.4. Runtime State (excerpt)
```yaml
state.location:
  zone: "<zone_id>"
  id: "<location_id>"
  privacy: "<enum>"          # carried into consent checks
```
### 15.5. Discovery & Privacy

- **Discovery**: locations are hidden until flagged; `hidden_until_discovered: true` keeps them invisible in UI until unlocked.
- **Privacy levels:**
  - none → public square, no intimacy possible
  - low → casual public (library)
  - medium → semi-private (park at night)
  - high → private rooms, intimacy is allowed
- Privacy influences which **gates** can pass (e.g., `accept_kiss` in medium+, `accept_sex` only in high).

### 15.6. Example
```yaml
zones:
  - id: "campus"
    name: "University Campus"
    discovered: true
    properties: { size: "large", security: "medium", privacy: "low" }
    transport_connections:
      - to: "downtown"
        methods: ["bus","walk"]
        distance: 2
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
            distance: "immediate"
            bidirectional: true
        features: ["bed","desk"]

      - id: "library"
        name: "Campus Library"
        type: "public"
        privacy: "low"
        discovered: true
        connections:
          - to: "courtyard"
            type: "path"
            distance: "short"

```

### 15.7. Authoring Guidelines
- Always give each zone at least one **safe fallback location** (prevents dead-ends).
- Tag high-privacy locations carefully; they gate NSFW actions.
- Use unlock_methods for keys/invitations instead of flags where possible (keeps fiction grounded).
- Keep **connections** simple — only model meaningful travel steps.
- Inline **features** are narrative aids, not separate locations.

---

## 16. Movement Rules

### 16.1. Definition
The **movement system** governs how the player (and companions) travel between locations and zones. 
Movement consumes **time** and may cost **energy**, requires **access conditions** to be met, 
and checks **NPC consent** when traveling with companions.
- **Local movement**: moving between locations inside the same zone.
- **Zone travel**: moving between different zones (campus → downtown).
- **Companions**: NPC willingness depends on trust/attraction/gates.
- **Restrictions**: unconscious state, low energy, or locked access block travel.

```yaml
movement:
  # --- Local movement within a zone ---
  local:
    base_time: <int>              # REQUIRED. Minutes consumed for immediate move.
    distance_modifiers:           # OPTIONAL. Time multipliers by connection distance.
      immediate: 0
      short: 1
      medium: 3
      long: 5

  # --- Zone-to-zone travel ---
  zone_travel:
    requires_exit_point: <bool>   # OPTIONAL. Default false. If true, must reach the exit node first.
    time_formula: "<expr>"        # REQUIRED. Expression DSL, e.g., "base_time * distance".
    allow_companions: <bool>      # OPTIONAL. Default true.

  # --- Restrictions (global checks) ---
  restrictions:
    requires_consciousness: true  # Default true. Block travel if the player is unconscious.
    min_energy: <int>             # Optional. Block travel if below a threshold.
    check_npc_consent: true       # Default true. Validate gates before moving with NPCs.

```
### 16.2. Runtime Example
```yaml
state:
  location: { zone: "campus", id: "library", privacy: "low" }
  time: { day: 3, slot: "afternoon", time_hhmm: "14:30" }
  meters:
    player: { energy: 35 }
```
If player moves from `library` → `dorm_room`:
- `distance: short` → `base_time (1) * short (1) = 1 minute`.
- `energy ≥ min_energy (5)` → allowed.
- If `emma accompanies`, engine checks her `movement.willing_locations` and consent gates.

### 16.3. Example Config

```yaml
movement:
  local:
    base_time: 1
    distance_modifiers: { immediate: 0, short: 1, medium: 3, long: 5 }

  zone_travel:
    requires_exit_point: true
    time_formula: "5 * distance"
    allow_companions: true

  restrictions:
    requires_consciousness: true
    min_energy: 5
    check_npc_consent: true

```

### 16.4. Companion Consent Rules

Defined per character in `characters` node:
```yaml
movement:
  willing_zones:
    - { zone: "campus", when: "always" }
    - { zone: "downtown", when: "meters.emma.trust >= 50" }
  willing_locations:
    - { location: "player_room", when: "meters.emma.trust >= 40" }
  transport:
    walk: "always"
    bus:  "always"
    car:  "meters.emma.trust >= 30"
  follow_thresholds:
    eager: 70      # attraction + trust
    willing: 40
    reluctant: 20
  refusal_text:
    low_trust: "I don't feel comfortable going there with you yet."
    wrong_time: "Now isn’t a good time."

```

### 16.5. Authoring Guidelines

- **Always include fallback travel routes** to avoid dead-ends.
- Balance **time cost**: keep local moves cheap, zone travel meaningful.
- Use **consent thresholds** for NPC companions (trust + attraction).
- Apply **privacy rules** at the target location, not during movement.
- Keep `min_energy` low enough to avoid soft-locking players.

---

## 17. Time & Calendar

### 17.1. Definition

The **time system** governs pacing, scheduling, and event triggers. It supports three modes:
- **Slots** — day divided into named parts (morning, afternoon, evening, night).
- **Clock** — continuous minute-based time (HH:MM).
- **Hybrid** — both: slots exist, but minutes are tracked within them.

Time advances through **actions**, **movement**, **effects**, and **sleep**,
and is referenced by **events**, **schedules**, and **arcs**.

### 17.2. Time Config Template
```yaml
time:
  mode: "<enum>"                  # REQUIRED. "slots" | "clock" | "hybrid"

  # --- Slots mode ---
  slots: ["morning","afternoon","evening","night"]   # REQUIRED for slots/hybrid
  actions_per_slot: <int>        # OPTIONAL. Auto-advance after N actions. Default: ∞
  auto_advance: <bool>           # OPTIONAL. If true, time moves automatically at the slot end.

  # --- Clock/hybrid mode ---
  clock:
    minutes_per_day: <int>       # REQUIRED for clock/hybrid. E.g., 1440
    slot_windows:                # REQUIRED for hybrid. Map slots → HH:MM ranges.
      morning:   { start: "06:00", end: "11:59" }
      afternoon: { start: "12:00", end: "17:59" }
      evening:   { start: "18:00", end: "21:59" }
      night:     { start: "22:00", end: "05:59" }

  # --- Calendar (optional) ---
  calendar:
    epoch: "2025-01-01"          # Narrative start date
    week_days: ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
    start_day_index: 2           # Day of week index at epoch start
    weeks_enabled: <bool>        # Enable week-based schedules

  # --- Starting point ---
  start:
    day: <int>                   # REQUIRED. Day counter at start (1-based).
    slot: "<slot_id>"             # REQUIRED for slots/hybrid.
    time: "HH:MM"                 # REQUIRED for clock/hybrid.

```

### 17.3. Runtime State (excerpt)
```yaml
state.time:
  day: 3                 # narrative day counter
  slot: "afternoon"      # slot derived from mode
  time_hhmm: "14:35"     # HH:MM (clock/hybrid only)
  weekday: "wednesday"   # derived from calendar

```

### 17.4. Time Effects
```yaml
- type: advance_time
  minutes: 30
```
Engine applies minutes, updates slot/weekday automatically. If day rolls over, slot and calendar fields update.

### 17.5. Examples

#### Simple slots model
```yaml
time:
  mode: "slots"
  slots: ["morning","noon","afternoon","evening","night","late_night"]
  actions_per_slot: 3
  start: { day: 1, slot: "morning" }

```

#### Hybrid model
```yaml
time:
  mode: "hybrid"
  slots: ["morning","afternoon","evening","night"]
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
    weeks_enabled: true
    week_days: ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
    start_day_index: 2
  start:
    day: 1
    slot: "morning"
    time: "08:30"

```

### 17.6. Authoring Guidelines

- Use **hybrid mode** by default: slot-friendly authoring + precise event triggers.
- Keep slot names short and consistent (`morning`, not `early_morning`).
- For events and schedules, rely on `time.slot`, `time.hhmm`, or `time.weekday`.
- Always define a **starting slot/time** in `start`.
- Test pacing: ensure players can rest to recover meters before exhaustion.

---

## 18. Nodes

### 18.1. Definition

A **node** is the authored backbone of a PlotPlay story.
Each node represents a discrete story unit — a scene, a hub, an encounter, or an ending. 
Nodes combine **authored beats and choices** with **freeform AI prose**, 
and control how the story progresses via **transitions**.

Nodes are where most author effort goes: they set context for the Writer, define conditions and effects, and connect to other nodes

### 18.2. Node Types

- **scene** — A focused moment with authored beats and freeform AI prose.
- **hub** — A menu-like node for navigation or repeated interactions.
- **encounter** — Short, often event-driven vignette; usually returns to a hub.
- **ending** — Terminal node; resolves the story and stops play.

### 18.3. Node Template

```yaml
# Node definition lives under: nodes: [ ... ]
- id: "<string>"                    # REQUIRED. Unique across the game.
  type: "<enum>"                    # REQUIRED. scene | hub | encounter | ending
  title: "<string>"                 # REQUIRED. Display name in UI/logs.
  present_characters: ["<string>", ...] # OPTIONAL. Explicitly list character IDs present in this node.

  # --- Availability ---
  preconditions: "<expr>"           # OPTIONAL. Expression DSL; must be true to enter.
  once: <bool>                      # OPTIONAL. If true, the node only plays once per run.

  # --- Writer guidance ---
  narration_override:               # OPTIONAL. Override defaults from game.yaml.
    pov: "<first|second|third>"
    tense: "<present|past>"
    paragraphs: "1-2"
    writer_profile: "<cheap|luxe|custom>"

  beats:                            # OPTIONAL. Bullets for Writer (not shown to players).
    - "Author-facing story cues."
    - "Establish tone, context, or presence of NPCs."

  # --- Effects ---
  entry_effects: [ <effects...> ]   # Applied once when the node is entered.

  # --- Actions & choices ---
  choices:                          # Preauthored menu buttons.
    - id: "<string>"
      prompt: "<string>"            # Shown to player.
      conditions: "<expr>"          # OPTIONAL.
      effects: [ <effects...> ]     # OPTIONAL.
      goto: "<node_id>"             # OPTIONAL. Forced transition on select.

  dynamic_choices:                  # Appear only when conditions become true.
    - id: "<string>"
      prompt: "<string>"
      conditions: "<expr>"
      effects: [ <effects...> ]
      goto: "<node_id>"

  action_filters:                   # OPTIONAL. Restrictions on freeform input.
    banned_freeform:
      - pattern: "<string>"         # Simple contains or regex.
        reason: "<string>"
    banned_topics: ["<string>", ...]

  # --- Transitions ---
  transitions:
    - when: "<expr>"                # Expression DSL. e.g., "always"
      to: "<node_id>"               # Target node ID
      reason: "<string>"            # OPTIONAL. For logs/debugging.

  # --- Ending-specific ---
  ending_id: "<string>"             # REQUIRED if type == ending.
  ending_meta:                      # OPTIONAL. Tags for UIs/achievements.
    character: "<npc_id>"
    tone: "<good|neutral|bad|secret|joke>"
    route: "<string>"
  credits:                          # OPTIONAL. Epilogue text.
    summary: "<string>"
    epilogue: ["<string>", ...]

```

### 18.4. Runtime State (excerpt)
```yaml
state.current_node: "<node_id>"
```

### 18.5. Examples

#### Scene 
```yaml
- id: "intro_courtyard"
  type: "scene"
  title: "First Day on Campus"
  preconditions: "time.day == 1 and time.slot == 'morning'"
  beats:
    - "Set the scene in the campus courtyard."
    - "Emma is visible but shy."
  transitions:
    - { when: "always", to: "player_room_intro" }
```
#### Hub
```yaml
- id: "player_room"
  type: "hub"
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
  preconditions: "meters.emma.trust >= 80 and meters.emma.attraction >= 80"
  entry_effects:
    - { type: flag_set, key: "ending_reached", value: "emma_good" }
  credits:
    summary: "You and Emma start a genuine relationship."
    epilogue:
      - "Over the next weeks, she grows more confident."
      - "You share love without losing her innocence."

```

### 18.6. Authoring Guidelines

- Always provide at least one **fallback transition** (`when: always`) to prevent dead-ends.
- Keep **beats** concise — bullets of intent, not prose.
- Use **choices** for deliberate actions; **dynamic_choices** for reactive unlocking.
- Use **gates** (in `characters` node) instead of raw meter checks where possible.
- For endings, always set a stable `ending_id`; use `ending_meta` for UI grouping.
- Restrict **banned_freeform** to keep Writer outputs within tone/setting.

---

## 19. Events

### 19.1. Definition

An **event** is authored content that can **interrupt**, **inject**, or **overlay** narrative 
outside the main node flow. Events add pacing, variety, and reactivity. 
They are triggered by **time**, **conditions**, **randomness**, or **milestones** and can fire once, repeat, or cycle with cooldowns.

Events differ from nodes:
- **Nodes** are the backbone of the story (explicit story beats).
- **Events** are side-triggers, often opportunistic or reactive.

### 19.2. Event Template

```yaml
# Event definition lives under: events: [ ... ]
- id: "<string>"                  # REQUIRED. Unique event ID.
  title: "<string>"               # REQUIRED. Display name (for logs/UI).
  description: "<string>"         # OPTIONAL. Author note, not shown to player.

  # --- Triggering ---
  trigger:
    scheduled:                    # OPTIONAL. Time/date slots.
      - when: "<expr>"            # Expression DSL (time/day/weekday).
    conditional:                  # OPTIONAL. State-based checks.
      - when: "<expr>"
    random:                       # OPTIONAL. Weighted pool trigger.
      weight: <int>               # Non-negative integer weight.
      cooldown: <int>             # Minutes or slots before re-eligibility.

  # --- Scope ---
  location_scope:                 # OPTIONAL. Restrict to certain zones/locations.
    zones: ["<zone_id>", ...]
    locations: ["<location_id>", ...]

  once: <bool>                    # OPTIONAL. If true, fires only once per run.

  # --- Payload ---
  narrative: "<string>"           # REQUIRED. Author seed text for Writer.
  beats: ["<string>", ...]        # OPTIONAL. Extra Writer guidance.
  effects: [ <effects...> ]       # OPTIONAL. Applied if the event fires.
  choices:                        # OPTIONAL. Local player decisions.
    - id: "<string>"
      prompt: "<string>"
      effects: [ <effects...> ]
      goto: "<node_id>"           # Optional transition.

```

### 19.3. Runtime Behavior

- Engine evaluates all events **each turn** after node resolution, before the next node selection.
- Eligible events are collected into a pool; if multiple random events qualify, weighted RNG selects.
- Events can either:
  - **Inject prose** into the current node (overlay),
  - **Interrupt** and redirect to a dedicated event node,
  - **Apply effects silently** (background change).

### 19.4. Runtime State (excerpt)

```yaml
state.events:
  triggered: ["emma_text_day1"]     # log of fired events
  cooldowns:
    "emma_text_day1": 1440          # minutes until eligible again
```

### 19.5. Examples

#### Scheduled event
```yaml
- id: "emma_text_day1"
  title: "Emma Texts You"
  trigger:
    scheduled:
      - when: "time.slot == 'night' and time.day == 1"
  narrative: "Your phone buzzes — Emma wants to meet tomorrow."
  effects:
    - { type: flag_set, key: "emma_texted", value: true }
```
#### Conditional encounter
```yaml
- id: "library_meet"
  title: "Chance Meeting in Library"
  trigger:
    conditional:
      - when: "state.location.id == 'library' and meters.emma.trust >= 20"
  narrative: "Emma waves shyly from behind a book."
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
  title: "Rumor at the Courtyard"
  trigger:
    random:
      weight: 30
      cooldown: 720     # 12h before next chance
  location_scope:
    zones: ["campus"]
  narrative: "You overhear whispers of your name among the students."
  effects:
    - { type: flag_set, key: "rumor_active", value: true }

```

### 19.6. Authoring Guidelines

- Always define **cooldowns** for random events to prevent spam.
- Use **location_scope** to tie events naturally to a setting.
- Keep **scheduled triggers** simple (slot/day/weekday).
- Avoid chaining too many effects — events should be light and modular.
- For **story-critical beats**, prefer nodes to events.
- Mark one-time story events with `once: true` to avoid repeats.

---

## 20. Arcs & Milestones

### 20.1. Definition

An **arc** is a long-term progression track that represents a character route, corruption path, relationship stage,
or overarching plotline. Each arc consists of ordered **milestones** (stages).
- **Arcs** define the big picture: multi-stage progressions with conditions.
- **Milestones** are checkpoints inside an arc: when conditions are met, the arc advances.
- Advancing a milestone can **unlock content**, **trigger effects**, or **open endings**.

Arcs ensure that stories have clear progression, and that endings are unlocked in a controlled, authored way.

### 20.2. Arc Template

```yaml
# Arc definition lives under: arcs: [ ... ]
- id: "<string>"                     # REQUIRED. Unique arc ID.
  title: "<string>"                  # REQUIRED. Display name for authoring.
  description: "<string>"            # OPTIONAL. Author notes.

  # --- Metadata ---
  character: "<npc_id>"              # OPTIONAL. Link arc to a character.
  category: "<string>"               # OPTIONAL. e.g., "romance","corruption","plot"
  repeatable: <bool>                 # OPTIONAL. Default false.

  # --- Stages / milestones ---
  stages:
    - id: "<string>"                 # REQUIRED. Stage ID.
      title: "<string>"              # REQUIRED. Stage name.
      description: "<string>"        # OPTIONAL. Author note.

      # --- Advancement ---
      advance_when: "<expr>"         # REQUIRED. DSL condition. Checked each turn.
      once: <bool>                   # OPTIONAL. Default true. Fires once.

      # --- Effects ---
      effects_on_enter: [ <effects...> ]   # Applied once when the stage begins.
      effects_on_exit:  [ <effects...> ]   # Applied once when leaving stage.
      effects_on_advance: [ <effects...> ] # Applied when transitioning into the next stage.

      # --- Unlocks ---
      unlocks:
        nodes: ["<node_id>", ...]    # OPTIONAL. Nodes become available.
        outfits: ["<outfit_id>", ...]
        endings: ["<ending_id>", ...]
```

### 20.3. Runtime State (excerpt)
```yaml
state.arcs:
  emma_corruption:
    stage: "curious"
    history: ["innocent","curious"]
```

### 20.4. Examples

#### Romance arc
```yaml
- id: "emma_romance"
  title: "Emma Romance Path"
  character: "emma"
  category: "romance"
  stages:
    - id: "acquaintance"
      title: "Just Met"
      advance_when: "flags.emma_met == true"
      effects_on_enter:
        - { type: meter_change, target: "emma", meter: "trust", op: "add", value: 5 }

    - id: "dating"
      title: "Dating"
      advance_when: "meters.emma.trust >= 50 and flags.first_kiss == true"
      effects_on_advance:
        - { type: unlock_ending, ending: "emma_good" }

    - id: "in_love"
      title: "In Love"
      advance_when: "meters.emma.trust >= 80 and meters.emma.attraction >= 80"
      effects_on_enter:
        - { type: flag_set, key: "emma_in_love", value: true }
      effects_on_advance:
        - { type: unlock_ending, ending: "emma_best" }
```

### 20.5. Corruption arc

```yaml
- id: "emma_corruption"
  title: "Emma Corruption Path"
  character: "emma"
  category: "corruption"
  stages:
    - id: "innocent"
      title: "Innocent"
      advance_when: "meters.emma.corruption < 20"

    - id: "curious"
      title: "Curious"
      advance_when: "20 <= meters.emma.corruption and meters.emma.corruption < 40"

    - id: "experimenting"
      title: "Experimenting"
      advance_when: "40 <= meters.emma.corruption and meters.emma.corruption < 70"
      effects_on_enter:
        - { type: unlock_outfit, character: "emma", outfit: "bold_outfit" }

    - id: "corrupted"
      title: "Corrupted"
      advance_when: "meters.emma.corruption >= 70"
      effects_on_enter:
        - { type: unlock_ending, ending: "emma_corrupted" }

```
### 20.6. Authoring Guidelines
- Always order stages so they evaluate from lowest to highest.
- Keep advance_when expressions simple (use flags/meters).
- Use effects_on_enter for immediate narrative unlocks.
- Use effects_on_advance for one-off triggers (new choices, outfits, endings).
- Mark arcs as **non-repeatable** unless designed for loops.
- Each arc should normally have **at least one ending unlock**.

---

## 21. AI Contracts (Writer & Checker)

### 21.1. Definition

The game engine uses a **two-model architecture** every turn:
 - **Writer**: expands authored beats, generates prose & dialogue in style/POV, and respects state/gates.
 - **Checker**: parses the Writer’s text into structured **state deltas** (meters, flags, clothing, inventory), validates consent & safety, and proposes transitions if justified.

Both run each turn; the engine merges outputs into the game state.

### 21.2. Turn Context Envelope

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
### 21.3. Writer Contract

- **Input**: node metadata, beats, character cards, last dialogue, UI choices, player action, events.
- **Output**: **plain text prose** (≤ target paragraphs).

#### Requirements
- Follow POV/tense from `game.yaml`.
- Respect gates & privacy (use refusal lines if needed).
 - Keep to the paragraph budget.
- No raw state changes (money, clothing, items) — imply only.

#### Example Output
```
Heat spills from the tavern. Alex smiles from behind the bar, polishing a glass.  

“Company’s free,” she teases, “but the drink will cost you.”

```
### 21.4. Checker Contract

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
- Only output changes justified by prose or authored effects.
- Clamp to meter caps.
- Refuse disallowed acts (set `safety.ok=false`, log violation).
- No extra keys, no comments.

### 21.5. Prompt templates

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
### 21.6. Safety & Consent
- All characters must be 18+.
- Non-con and minors are blocked hard.
- Intimate acts require:
  - Proper gate (`accept_*`).
  - Location privacy is high enough.
  - Meter thresholds satisfied.
- Violations cause Writer to use **refusal text** and Checker to flag `safety.ok=false`.

### 21.7. Memory
- `memory.append` holds compact factual reminders (e.g., “Alex teased you at the tavern”).
- Engine keeps rolling window (last 6–10).
- Avoid explicit sex details unless milestone/flag.

### 21.8. Error Recovery
 - Malformed JSON → cleanup pass.
 - Still bad → retry with “Return JSON only”
 - On double failure → skip deltas, log error, continue.

### 21.9. Cost Profiles
 - **cheap**: small, fast models.
 - **luxe**: larger models, richer prose.
 - **custom**: override in game.yaml.

