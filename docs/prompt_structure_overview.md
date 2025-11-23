# PromptBuilder Output Structure Overview

## Quick Reference

The PromptBuilder creates **two main prompts** for each turn:

1. **Writer Prompt** - Generates narrative prose (2-5 seconds, ~400 tokens)
2. **Checker Prompt** - Validates state changes (1-2 seconds, ~300 tokens)

Both prompts include **Character Cards** - detailed NPC context with gates, meters, and refusals.

---

## 📝 Writer Prompt Structure

### Components (in order)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. SPEC TEMPLATE (POV/Tense/Rules)                         │
├─────────────────────────────────────────────────────────────┤
│ 2. TURN CONTEXT ENVELOPE                                    │
│    ├─ Game metadata                                         │
│    ├─ Time context (day/slot/time/weekday)                  │
│    ├─ Location (zone/privacy)                               │
│    ├─ Node (id/title/type)                                  │
│    ├─ Player inventory                                      │
│    └─ Present characters                                    │
├─────────────────────────────────────────────────────────────┤
│ 3. CHARACTER CARDS                                          │
│    └─ For each present NPC (see details below)             │
├─────────────────────────────────────────────────────────────┤
│ 4. RECENT HISTORY (last 3 narratives)                       │
├─────────────────────────────────────────────────────────────┤
│ 5. NODE BEATS (if present)                                  │
├─────────────────────────────────────────────────────────────┤
│ 6. PLAYER ACTION                                            │
├─────────────────────────────────────────────────────────────┤
│ 7. INSTRUCTION (write narrative)                            │
└─────────────────────────────────────────────────────────────┘
```

### Example Writer Prompt

```
You are the PlotPlay Writer. POV: second. Tense: present. Write 2 short paragraph(s) max.
Never describe state changes (items, money, clothes). Use refusal lines if a gate blocks.
Keep dialogue natural. Stay within beats and character cards.

Game: coffeeshop_date (v0.1.0)
Time: Day 1, morning, 10:30, Monday
Location: Cozy Corner Cafe (zone: downtown, privacy: low)
Node: cafe_arrival - "Morning at the Cafe" (type: scene)
Player inventory: {money:20, phone(item)}
Present characters: player, emma

Recent history:
  - You push open the door to the cafe, warmth and the scent of coffee greeting you.
  - Emma looks up from wiping the counter, her face brightening into a genuine smile.
  - "First time here?" she asks, her voice warm and friendly.

Character cards:

card:
  id: "emma"
  name: "Emma"
  summary: "Bright-eyed barista with auburn hair tied back, warm smile..."
  appearance: "Bright-eyed barista with auburn hair tied back, warm smile, coffee-stained apron"
  personality: "Friendly, witty, secretly nerdy about coffee science"
  meters: {trust: 10/100 (stranger), attraction: 5/100 (none), arousal: 0/100 (none)}
  outfit: "barista_uniform"
  modifiers: [well_rested:high]
  dialogue_style: "teasing, warm, uses coffee puns"
  gates: {allow: [accept_chat], deny: [accept_flirt, accept_kiss]}
  refusals: {accept_flirt: "Slow down there, we just met!", accept_kiss: "Whoa, let's get to know each other first."}

Node beats: introduction, establish_setting, first_impression

Player action: I walk up to the counter and smile at Emma.

Write the next narrative beat (2 paragraphs max).
```

---

## 🔍 Checker Prompt Structure

### Components (in order)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. SPEC TEMPLATE (Role/Rules/Schema)                       │
├─────────────────────────────────────────────────────────────┤
│ 2. IMPORTANT RULES                                          │
│    ├─ Delta format (+N/-N, =N)                              │
│    ├─ Safety violations (set ok=false)                      │
│    ├─ Clamp values (min/max bounds)                         │
│    └─ Only justified changes                                │
├─────────────────────────────────────────────────────────────┤
│ 3. TURN CONTEXT                                             │
│    ├─ Player action                                         │
│    └─ AI narrative (Writer output)                          │
├─────────────────────────────────────────────────────────────┤
│ 4. CURRENT STATE                                            │
│    ├─ Location (with privacy)                               │
│    ├─ Time (day/slot/time/weekday)                          │
│    └─ Present characters                                    │
├─────────────────────────────────────────────────────────────┤
│ 5. ACTIVE GATES (per character)                             │
├─────────────────────────────────────────────────────────────┤
│ 6. STATE SNAPSHOT (compact)                                 │
├─────────────────────────────────────────────────────────────┤
│ 7. OUTPUT SCHEMA TEMPLATE (JSON)                            │
└─────────────────────────────────────────────────────────────┘
```

### Example Checker Prompt

```
You are the PlotPlay Checker. Extract ONLY justified deltas.
Respect consent gates and privacy. Output strict JSON with keys:
[safety, meters, flags, inventory, clothing, modifiers, location, events_fired, node_transition, memory].

IMPORTANT RULES:
- Use +N/-N for deltas, =N for absolutes (e.g., "trust": "+5", "money": "-10")
- If prose depicts a blocked act: set safety.ok = false, add violations: ["gate:<id>"], emit no deltas
- Clamp values within defined min/max bounds
- Only output changes justified by the scene and allowed by gates/privacy

TURN CONTEXT:
Action: I walk up to the counter and smile at Emma.
Scene: Emma's eyes light up as you approach the counter, her hands still moving efficiently despite her attention on you. "Good morning!" she says, her smile widening. "First timer or regular I haven't met yet?" Her voice carries a playful lilt, and you catch the faint scent of espresso and cinnamon from her workspace.

CURRENT STATE:
Location: cafe_counter (zone: downtown, privacy: low)
Time: Day 1, morning, 10:30, Monday
Present characters: player, emma

ACTIVE GATES:
emma: allow=[accept_chat], deny=[accept_flirt, accept_kiss]

STATE SNAPSHOT:
Meters: {player=[energy:80, mood:70], emma=[trust:10, attraction:5, arousal:0]...}
Flags: {first_visit: true, emma_met: false}...
Inventory: player={money:20, phone:1}
Clothing: {player=casual_outfit, emma=barista_uniform}
Modifiers: {emma=[well_rested]}

OUTPUT STRICT JSON ONLY (no comments, no extra keys):
{
  "safety": {"ok": true, "violations": []},
  "meters": {},
  "flags": {},
  "inventory": [],
  "clothing": [],
  "movement": [],
  "modifiers": {"add": [], "remove": []},
  "discoveries": {"locations": [], "zones": [], "actions": [], "endings": []},
  "events_fired": [],
  "node_transition": null,
  "memory": {"append": []}
}
```

---

## 👤 Character Card Structure

### Full Character Card Format

```yaml
card:
  id: "character_id"                    # Unique identifier
  name: "Display Name"                  # Full character name
  summary: "Short description..."       # 50 chars from appearance
  appearance: "Full physical desc..."   # Complete appearance text
  personality: "Character traits..."    # Personality description

  # Meters with thresholds
  meters: {
    trust: 42/100 (acquaintance),       # Current/Max (threshold label)
    attraction: 38/100 (interested),
    arousal: 10/100 (none)
  }

  # Current outfit/clothing
  outfit: "outfit_id"                   # Current outfit name

  # Active modifiers with intensity
  modifiers: [
    aroused:light,                      # modifier_id:intensity
    drunk:moderate,
    well_rested:high
  ]

  # Dialogue guidance
  dialogue_style: "teasing, warm, uses coffee puns"

  # Gates (CRITICAL for consent)
  gates: {
    allow: [accept_chat, accept_compliment],
    deny: [accept_flirt, accept_kiss, accept_sex]
  }

  # Refusal text (CRITICAL for boundaries)
  refusals: {
    accept_flirt: "Slow down there, we just met!",
    accept_kiss: "Whoa, let's get to know each other first.",
    accept_sex: "Absolutely not. I don't even know your name."
  }
```

### Character Card Fields Explained

| Field | Purpose | Example | Why Important |
|-------|---------|---------|---------------|
| **id** | Unique identifier | `"emma"` | References in state/effects |
| **name** | Display name | `"Emma"` | Narrative readability |
| **summary** | Quick description | `"Bright-eyed barista with auburn hair..."` | Writer context at a glance |
| **appearance** | Full physical description | `"Bright-eyed barista with auburn hair tied back, warm smile, coffee-stained apron"` | Visual narrative details |
| **personality** | Character traits | `"Friendly, witty, secretly nerdy about coffee science"` | Behavioral guidance |
| **meters** | Current state with labels | `trust: 42/100 (acquaintance)` | Relationship progression context |
| **outfit** | Current clothing | `"barista_uniform"` | Visual continuity |
| **modifiers** | Active status effects | `[aroused:light, drunk:moderate]` | Behavioral modifications |
| **dialogue_style** | Speech patterns | `"teasing, warm, uses coffee puns"` | Voice consistency |
| **gates.allow** | Permitted actions | `[accept_chat, accept_compliment]` | What's allowed |
| **gates.deny** | Blocked actions | `[accept_flirt, accept_kiss]` | What's forbidden |
| **refusals** | Boundary text | `"Slow down there, we just met!"` | **HOW to narrate blocked actions** |

---

## 🎯 Meter Threshold Labels

Meters show **contextual relationship status** instead of raw numbers:

### Example Meter States

```yaml
# Trust meter (0-100)
trust: 10/100 (stranger)      # Just met
trust: 42/100 (acquaintance)  # Getting to know each other
trust: 68/100 (friend)        # Comfortable together
trust: 85/100 (close friend)  # Deep trust

# Attraction meter (0-100)
attraction: 5/100 (none)           # No romantic interest
attraction: 38/100 (interested)    # Starting to notice
attraction: 62/100 (attracted)     # Clear interest
attraction: 85/100 (infatuated)    # Strong feelings

# Arousal meter (0-100)
arousal: 0/100 (none)         # Not aroused
arousal: 25/100 (light)       # Mild interest
arousal: 55/100 (moderate)    # Building tension
arousal: 85/100 (high)        # Very aroused
```

**Why This Matters:**
- Writer knows **relationship context** ("still strangers" vs "close friends")
- Writer can narrate **progression** ("warming up to you")
- Writer avoids **inappropriate escalation** (can't write romance at trust:10)

---

## 🔒 Gates & Refusals (Critical Feature)

### How Gates Work

**Gates = Consent Boundaries**

```yaml
# Gates control what actions are permitted
gates: {
  allow: [accept_chat, accept_compliment],   # ✅ These are OK
  deny: [accept_flirt, accept_kiss]          # ❌ These are blocked
}

# Refusals = What to say when blocked
refusals: {
  accept_flirt: "Slow down there, we just met!",
  accept_kiss: "Whoa, let's get to know each other first."
}
```

### Writer Use of Refusals

**Scenario:** Player tries to kiss Emma (trust: 10, accept_kiss: DENIED)

**Without Refusal Text (BAD):**
```
Writer: "You lean in for a kiss. Emma pulls away awkwardly."
❌ Generic, no character voice, unclear why
```

**With Refusal Text (GOOD):**
```
Writer: "You lean in for a kiss. Emma gently places a hand on your chest,
stopping you with a soft laugh. 'Whoa, let's get to know each other first,'
she says, her smile still warm but her boundaries clear."
✅ Uses character's voice, clear boundary, maintains warmth
```

### Checker Use of Gates

**Scenario:** Writer narrative depicts blocked action

**Checker Output:**
```json
{
  "safety": {
    "ok": false,                      // ❌ Violation detected
    "violations": ["gate:accept_kiss"] // Specific gate violated
  },
  "meters": {},  // No state changes applied
  "flags": {}    // Everything rejected
}
```

**Engine Response:**
- Logs safety violation
- Rejects all state changes
- Can regenerate narrative or warn player

---

## 📊 Modifier Display

### Modifier Intensity Levels

```yaml
# Basic modifier (no intensity)
modifiers: [caffeinated]

# Modifier with intensity
modifiers: [
  aroused:light,     # Slight arousal
  drunk:moderate,    # Tipsy, not wasted
  tired:high         # Exhausted
]
```

**Writer Context:**
- `aroused:light` → "pulse quickening slightly"
- `aroused:moderate` → "breath catching, cheeks flushed"
- `aroused:high` → "body trembling with desire"

---

## 🌍 Turn Context Envelope

### Full Context Structure

```yaml
Game: coffeeshop_date (v0.1.0)           # Game ID + version
Time: Day 1, morning, 10:30, Monday      # day, slot, time, weekday
Location: Cozy Corner Cafe               # Location name
  zone: downtown                         # Zone ID
  privacy: low                           # Privacy level (low/medium/high)
Node: cafe_arrival - "Morning at the Cafe"  # Node ID - Title
  type: scene                            # Node type
Player inventory: {money:20, phone(item)}   # What player has
Present characters: player, emma         # Who's in the scene

Recent history:
  - You push open the door to the cafe...
  - Emma looks up from wiping the counter...
  - "First time here?" she asks...
```

### Privacy Levels Impact

| Privacy | Description | Gates Affected | Example Location |
|---------|-------------|----------------|------------------|
| **low** | Public space | Most intimacy blocked | Cafe, street, park |
| **medium** | Semi-private | Some intimacy allowed | Private booth, car |
| **high** | Private space | Most intimacy allowed | Bedroom, apartment |

**Example:**
- `accept_kiss` gate might require `privacy >= medium`
- `accept_sex` gate might require `privacy == high`
- Writer won't escalate beyond privacy level

---

## 📝 Node Beats

### What Are Beats?

**Beats = Story Structure Guidance**

```yaml
Node: cafe_arrival
Beats:
  - introduction        # Introduce Emma
  - establish_setting   # Describe the cafe
  - first_impression    # Initial chemistry/interaction
```

**Writer Use:**
- Stays within these narrative goals
- Doesn't skip ahead to later story points
- Maintains authored story structure

**Without Beats:**
```
Writer might jump ahead: "You spend hours talking, becoming close friends..."
❌ Skips authored progression
```

**With Beats:**
```
Writer follows structure: "Emma introduces herself as you take in the cozy cafe.
The first moment of connection hangs in the air..."
✅ Follows authored beats
```

---

## 🎨 Example Complete Prompt Flow

### 1. Player Action
```
Player: "I smile and compliment Emma's coffee-making skills"
```

### 2. Writer Prompt Sent
```
[Full prompt with context, character cards, beats, action]
→ OpenRouter API (Mixtral 8x7B)
→ Streaming response: ~2-3 seconds
```

### 3. Writer Output
```
Emma's eyes light up at the compliment, and she leans against the counter
with a knowing smile. "Oh, you noticed? Most people just want their caffeine
fix, but I'm kind of obsessed with the science behind it." She gestures to
the espresso machine behind her. "This morning I dialed in a new Ethiopian
blend - want to try it?"

Her warmth is genuine, and you notice the way she unconsciously plays with
the end of her apron tie when she's excited about something.
```

### 4. Checker Prompt Sent
```
[Full prompt with context, Writer output, gates, state snapshot]
→ OpenRouter API (Mixtral 8x7B)
→ JSON response: ~1-2 seconds
```

### 5. Checker Output
```json
{
  "safety": {"ok": true, "violations": []},
  "meters": {
    "emma": {
      "trust": "+2",
      "attraction": "+1"
    }
  },
  "flags": {
    "complimented_coffee_skills": true
  },
  "inventory": [],
  "clothing": [],
  "movement": [],
  "modifiers": {"add": [], "remove": []},
  "discoveries": {},
  "events_fired": [],
  "node_transition": null,
  "memory": {"append": ["You complimented Emma's coffee expertise, making her light up."]}
}
```

### 6. Engine Applies Changes
```
✅ Emma trust: 10 → 12 (stranger, moving toward acquaintance)
✅ Emma attraction: 5 → 6 (slight interest)
✅ Flag set: complimented_coffee_skills = true
✅ Memory added to history
```

### 7. Player Sees
```
Narrative: "Emma's eyes light up at the compliment..."

Choices:
→ "I'd love to try it" (choice)
→ Say something else (say)
→ Order something (choice)

Emma: trust 12/100 (stranger), attraction 6/100 (none)
```

---

## 📊 Summary Stats

### Prompt Sizes

| Prompt Type | Typical Size | Generation Time |
|-------------|--------------|-----------------|
| Writer | 800-1500 tokens | 2-5 seconds |
| Checker | 600-1000 tokens | 1-2 seconds |
| Character Card (each) | 150-250 tokens | N/A |

### Token Breakdown (Typical Turn)

```
Writer Prompt (~1200 tokens):
  - Spec template: 50 tokens
  - Turn context: 150 tokens
  - Character cards: 200 tokens per NPC (x2 = 400)
  - Recent history: 200 tokens
  - Node beats: 50 tokens
  - Player action: 20 tokens
  - Instructions: 30 tokens

Checker Prompt (~800 tokens):
  - Spec template: 100 tokens
  - Turn context: 300 tokens
  - Current state: 150 tokens
  - Active gates: 100 tokens
  - State snapshot: 100 tokens
  - Schema template: 50 tokens
```

### Cost Estimate (OpenRouter/Mixtral)

```
Writer call: ~1200 input + ~400 output = ~1600 tokens
Checker call: ~800 input + ~300 output = ~1100 tokens
Total per turn: ~2700 tokens

At $0.00027/1k tokens (Mixtral):
Cost per turn: ~$0.0007 (less than 1 cent)
Cost per 100 turns: ~$0.07 (7 cents)
Cost per playthrough (200 turns): ~$0.14 (14 cents)
```

---

## 🎯 Key Improvements Over Basic Prompts

| Aspect | Before PromptBuilder | After PromptBuilder |
|--------|---------------------|---------------------|
| **Time Context** | ❌ None | ✅ Day/slot/time/weekday |
| **Privacy** | ❌ Not included | ✅ Privacy level for consent |
| **Gate Refusals** | ❌ Generic rejections | ✅ Character-specific voice |
| **Meter Thresholds** | ❌ Raw numbers only | ✅ "acquaintance", "friend" labels |
| **Node Beats** | ❌ Ignored | ✅ Story structure enforced |
| **Player Inventory** | ❌ Not visible | ✅ Items player can reference |
| **Safety Schema** | ❌ No tracking | ✅ Violation detection |
| **Dialogue Style** | ❌ Inconsistent | ✅ Per-character voice |
| **Modifier Intensity** | ❌ Binary on/off | ✅ "light", "moderate", "high" |
| **POV/Tense** | ❌ Unspecified | ✅ Explicit guidance |

---

## 🚀 Production Quality Impact

**Before PromptBuilder:**
```
Generic narrative: "She responds positively to your action.
The interaction progresses naturally."
❌ No character voice, vague, boring
```

**After PromptBuilder:**
```
Contextual narrative: "Emma's eyes light up at the compliment,
and she leans against the counter with a knowing smile. 'Oh, you noticed?
Most people just want their caffeine fix, but I'm kind of obsessed with
the science behind it.' Her warmth is genuine, and you notice the way
she unconsciously plays with the end of her apron tie when she's excited."
✅ Character voice, specific details, emotional depth
```

**The difference:** Full context = Better AI output = Better player experience
