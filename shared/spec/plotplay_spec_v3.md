# PlotPlay Game Authoring Specification v3.0

## Table of Contents
1. [Overview](#overview)
2. [Core Concepts](#core-concepts)
3. [Game Configuration](#1-game-configuration-configyaml)
4. [Character Definitions](#2-character-definitions-charactersyaml)
5. [Effects and Modifiers](#3-effects-and-modifiers-system)
6. [Locations](#4-locations-locationsyaml)
7. [Items](#5-items-itemsyaml)
8. [Story Nodes](#6-story-nodes-nodesyaml)
9. [Random Events](#7-random-events-eventsyaml)
10. [Milestones](#8-milestones-arcsyaml)
11. [AI Integration](#9-ai-integration-instructions)
12. [Runtime State](#10-runtime-state-structure)
13. [Save System](#11-save-system)
14. [Implementation Notes](#12-implementation-notes)

---

## Overview

PlotPlay is an AI-driven text adventure engine that combines pre-authored branching narratives with dynamic AI-generated prose. The system supports mature/NSFW content with sophisticated character behavior, state management, and progression mechanics.

### Key Features
- **Hybrid Narrative**: Mix of pre-written story nodes and AI-generated content
- **Dynamic Characters**: State-based appearance and behavior modifications
- **Game-Defined Meters**: Each game defines its own trackable values
- **Consent System**: Character behavior gates based on relationship meters
- **Modifier System**: Temporary and permanent effects on characters
- **Rich State Management**: Track clothing, inventory, flags, and complex conditions
- **Flexible world structure**: Multilevel location with different types of movement and exploration

### Design Philosophy
- **Defined Endings**: Games have specific goals and endings, not endless sandbox
- **State Coherence**: AI respects current game state and character conditions
- **Player Agency**: Meaningful choices that affect story progression
- **Content Gating**: Progressive intimacy based on relationship development

---

## Core Concepts

### State-Driven Narrative
The game engine maintains a comprehensive state that includes:
- **Meters**: Numeric values tracking relationships, stats, and conditions
- **Flags**: Boolean and value storage for story progression
- **Modifiers**: Active effects changing character appearance/behavior
- **Inventory**: Items the player possesses
- **Location**: Current position in the game world
- **Time**: Day/time tracking with scheduled events

### Character Cards
Dynamic character descriptions that change based on:
- Current meter values (arousal, trust, corruption, etc.)
- Active modifiers (drunk, injured, happy, etc.)
- Clothing state
- Environmental context
- Recent events

### AI Integration
Two-model approach for narrative generation:
- **Writer Model**: Generates narrative prose based on game state
- **Checker Model**: Extracts state changes from narrative

---

## 1. Game Configuration (`config.yaml`)

The main configuration file defines game metadata, meters, and core settings.

```yaml
game:
  id: "unique_game_id"
  title: "Game Title"
  version: "1.0.0"
  author: "Author Name"
  content_rating: "explicit"  # all_ages | teen | mature | explicit
  tags: ["romance", "fantasy", "adventure"]
  
  # Game-specific meters definition
  meters:
    # Player meters
    player:
      health:
        min: 0
        max: 100
        default: 100
        visible: true
        icon: "❤️"
        decay_rate: 0  # Per day
      energy:
        min: 0
        max: 100
        default: 100
        visible: true
        icon: "⚡"
        decay_rate: -20  # Negative = increases
      money:
        min: 0
        max: 99999
        default: 100
        visible: true
        icon: "💰"
        format: "currency"  # Shows as $100
      confidence:
        min: 0
        max: 100
        default: 50
        visible: true
        icon: "💪"
    
    # Character meter template (applied to all NPCs)
    character_template:
      # Relationship meters
      trust:
        min: 0
        max: 100
        default: 0
        visible: true
        icon: "🤝"
        thresholds:
          stranger: [0, 19]
          acquaintance: [20, 39]
          friend: [40, 69]
          close: [70, 89]
          intimate: [90, 100]
      
      attraction:
        min: 0
        max: 100
        default: 0
        visible: true
        icon: "💕"
        thresholds:
          none: [0, 19]
          interested: [20, 39]
          attracted: [40, 69]
          infatuated: [70, 89]
          in_love: [90, 100]
      
      arousal:
        min: 0
        max: 100
        default: 0
        visible: false  # Hidden until discovered
        reveal_condition: "state.meters.{character}.attraction >= 30"
        icon: "🔥"
        decay_rate: 10  # Per day
        thresholds:
          none: [0, 19]
          interested: [20, 39]
          aroused: [40, 59]
          highly_aroused: [60, 79]
          desperate: [80, 100]
      
      corruption:
        min: 0
        max: 100
        default: 0
        visible: false
        reveal_condition: "state.flags.corruption_revealed == true"
        icon: "😈"
        decay_rate: 0  # Doesn't decay
        thresholds:
          pure: [0, 19]
          curious: [20, 39]
          experimenting: [40, 59]
          corrupted: [60, 79]
          depraved: [80, 100]
      
      boldness:
        min: 0
        max: 100
        default: 20  # Most characters start shy
        visible: false
        reveal_condition: "state.meters.{character}.trust >= 40"
        icon: "🦁"
        thresholds:
          timid: [0, 19]
          shy: [20, 39]
          normal: [40, 59]
          confident: [60, 79]
          bold: [80, 100]
    
  # Meter interactions and relationships
  meter_interactions:
    # Arousal affects boldness
    - source: "{character}.arousal"
      target: "{character}.boldness"
      condition: "source >= 60"
      effect: "target.temporary_modifier = +20"
      
    # High corruption reduces trust requirements
    - source: "{character}.corruption"
      target: "{character}.trust"
      condition: "source >= 60"
      effect: "target.requirement_modifier = -20"
      
    # Energy affects the arousal cap
    - source: "player.energy"
      target: "all.arousal"
      condition: "source < 30"
      effect: "target.max = 60"
      
  # Core game settings
  settings:
    starting_location: "intro"
    starting_time: "morning"
    starting_day: 1
    starting_node: "start"
    
  # Save system
  save_system:
    auto_save: true
    save_slots: 10
    checkpoint_nodes: ["chapter_1_end", "chapter_2_end"]
    
  # Time system
  time_system:
    slots: ["morning", "afternoon", "evening", "night", "late_night"]
    auto_advance: true
    actions_per_slot: 3
    
  # Difficulty/gameplay modifiers
  difficulty:
    meter_caps:
      default: [0, 100]
    meter_decay_multiplier: 1.0
    money_multiplier: 1.0
    hint_system: true
```

---

## 2. Character Definitions (`characters.yaml`)

### 2.1 Base Character Structure

```yaml
characters:
  - id: "emma"
    name: "Emma Chen"
    full_name: "Emma Xiaoli Chen"
    age: 20
    gender: "female"
    pronouns: ["she", "her", "hers"]
    orientation: "bisexual"
    role: "love_interest"  # primary_love_interest | love_interest | friend | rival | mentor
    
    # Character-specific meter overrides/additions
    meters:
      # Override defaults
      trust:
        default: 10  # Starts as an acquaintance
      boldness:
        default: 15  # Particularly shy
      
      # Character-specific meter
      academic_stress:
        min: 0
        max: 100
        default: 30
        visible: true
        icon: "📚"
        decay_rate: -5  # Increases over time
        
    # Base personality (static traits)
    personality:
      core_traits: ["intelligent", "shy", "curious", "kind"]
      values: ["honesty", "loyalty", "academic success"]
      fears: ["rejection", "failure", "public embarrassment"]
      desires: ["genuine connection", "academic achievement", "new experiences"]
      quirks: ["bites lip when thinking", "plays with hair when nervous"]
      
    # Background for AI context
    background: |
      Second-generation Chinese-American, grew up in suburban Boston.
      Parents are both doctors with high expectations. Studying computer science
      but secretly interested in creative writing. Plays violin but hasn't
      told anyone at college. Virgin but curious about sexuality.
```

### 2.2 Dynamic State Modifiers

```yaml
    # State modifiers that change appearance/behavior
    state_modifiers:
      # Arousal-based modifiers
      - id: "slightly_aroused"
        trigger: "auto"  # auto | manual | event
        conditions:
          all:
            - "state.meters.emma.arousal >= 30"
            - "state.meters.emma.arousal < 60"
        priority: 5
        
        appearance_modifiers:
          skin: "slightly flushed"
          eyes: "occasionally darting to you"
          breathing: "a bit quicker than normal"
          posture: "shifting in her seat"
          lips: "occasionally licking them"
          
        behavior_modifiers:
          dialogue_style: "occasionally stumbles over words"
          personal_space: -1  # Stands closer
          eye_contact: "brief but intense"
          gestures: "playing with hair"
          initiative: +1
          
        description_addon: "She seems a bit distracted, her cheeks showing a hint of color."
        
      - id: "highly_aroused"
        trigger: "auto"
        conditions:
          all:
            - "state.meters.emma.arousal >= 60"
        priority: 10
        
        appearance_modifiers:
          skin: "flushed, warm to touch"
          eyes: "dilated pupils, heavy-lidded"
          lips: "parted, slightly swollen"
          breathing: "shallow and quick"
          posture: "leaning towards you"
          chest: "rising and falling noticeably"
          
        behavior_modifiers:
          dialogue_style: "breathless, direct"
          personal_space: -2
          eye_contact: "intense, prolonged"
          initiative: +3
          inhibition: -3
          touches_self: true  # Unconscious self-touching
          
        description_addon: "Her arousal is obvious - flushed skin, quickened breathing, and eyes that keep finding yours."
        
      # Corruption-based modifiers
      - id: "corrupted_behavior"
        trigger: "auto"
        conditions:
          all:
            - "state.meters.emma.corruption >= 60"
        priority: 8
        
        appearance_modifiers:
          eyes: "knowing look"
          smile: "mischievous"
          posture: "confident, provocative"
          
        behavior_modifiers:
          dialogue_style: "suggestive, teasing"
          initiative: +2
          inhibition: -4
          kink_acceptance: +3
          
        description_addon: "There's something different about her - a knowing confidence that wasn't there before."
        
      # Boldness-based modifiers
      - id: "feeling_bold"
        trigger: "auto"
        conditions:
          any:
            - "state.meters.emma.boldness >= 60"
            - "state.flags.emma_drunk == true"
        priority: 6
        
        behavior_modifiers:
          initiative: +2
          dialogue_style: "confident, flirty"
          inhibition: -2
          personal_space: -1
          
      # Combined state modifiers
      - id: "desperate_need"
        trigger: "auto"
        conditions:
          all:
            - "state.meters.emma.arousal >= 80"
            - "state.meters.emma.corruption >= 40"
            - "state.meters.emma.boldness >= 40"
        priority: 15
        
        appearance_modifiers:
          whole_body: "trembling with need"
          eyes: "pleading"
          skin: "flushed and sensitive"
          
        behavior_modifiers:
          dialogue_style: "begging, desperate"
          initiative: +5
          inhibition: -5
          
        description_addon: "She's past the point of restraint, her need overwhelming any remaining inhibitions."
```

### 2.3 Appearance System

```yaml
    appearance:
      # Base appearance (static attributes)
      base:
        height: "5'4" (162cm)"
        build: "petite, athletic from yoga"
        ethnicity: "Chinese-American"
        hair:
          color: "black"
          length: "shoulder-length"
          texture: "straight, silky"
          style: "usually in ponytail"
          alt_styles: ["loose", "messy bun", "braided", "bed head"]
        eyes:
          color: "dark brown"
          shape: "almond-shaped"
          details: "expressive, with long lashes"
        face:
          shape: "heart-shaped"
          features: "delicate features, high cheekbones"
        skin:
          tone: "light tan"
          texture: "smooth, clear"
        distinguishing_features:
          - "small scar on left eyebrow from childhood accident"
          - "dimples when smiling"
          - "beauty mark on left shoulder"
        body_details:
          chest: "B-cup, perky"
          waist: "slim"
          hips: "narrow but shapely"
          legs: "toned from running"
          
      # Contextual appearance descriptions
      appearance_contexts:
        - id: "first_meeting"
          conditions: "state.flags.emma_met != true"
          description: |
            A petite Asian woman catches your attention. She's dressed casually 
            in jeans and a MIT hoodie, her black hair pulled back in a ponytail. 
            Dark brown eyes glance up from her laptop, meeting yours briefly 
            before returning to her screen. There's something endearing about 
            the way she chews her lip while concentrating.
            
        - id: "morning_after"
          conditions:
            all:
              - "state.flags.emma_spent_night == true"
              - "state.time_slot == 'morning'"
          description: |
            Emma looks beautiful in the morning light, her usually neat hair 
            adorably mussed, falling around her face in soft waves. She's wearing 
            your t-shirt which hangs loosely on her petite frame, barely covering 
            her thighs. There's a satisfied glow to her skin and a new confidence 
            in her smile.
            
        - id: "highly_corrupted"
          conditions: "state.meters.emma.corruption >= 80"
          description: |
            Emma has transformed from the shy girl you first met. She carries 
            herself with sultry confidence, her movements deliberately sensual. 
            Her clothing choices have become bolder, showing more skin. The 
            innocence in her eyes has been replaced with knowing desire.
```

### 2.4 Wardrobe System

```yaml
    wardrobe:
      # Clothing rules
      clothing_rules:
        layer_order: ["outerwear", "dress", "top", "bottom", "feet", "underwear_top", "underwear_bottom", "accessories"]
        weather_sensitive: true
        context_sensitive: true  # Different outfits for different locations
        
      outfits:
        - id: "casual_day"
          name: "Casual outfit"
          tags: ["everyday", "comfortable", "modest"]
          weather: ["any"]
          locations: ["campus", "library", "cafeteria"]
          
          layers:
            outerwear:
              item: "MIT hoodie"
              color: "gray"
              material: "cotton blend"
              state: "slightly worn"
              removable: true
            top:
              item: "tank top"
              color: "white"
              material: "cotton"
              fit: "fitted"
              transparency: "opaque"
            bottom:
              item: "jeans"
              color: "dark blue"
              style: "skinny"
              state: "slightly faded"
            feet:
              item: "sneakers"
              color: "white"
              brand: "Converse"
            underwear_top:
              item: "bra"
              style: "simple t-shirt bra"
              color: "nude"
              material: "cotton"
              appeal: "practical"
            underwear_bottom:
              item: "panties"
              style: "bikini"
              color: "nude"
              material: "cotton"
              appeal: "practical"
            accessories:
              - "glasses (black frames)"
              - "fitbit"
              - "small backpack"
              - "phone in back pocket"
              
        - id: "revealing_outfit"
          name: "Bold outfit"
          tags: ["sexy", "revealing", "confident"]
          unlocked_condition: "state.meters.emma.corruption >= 40 or state.meters.emma.boldness >= 60"
          weather: ["warm", "hot"]
          
          layers:
            top:
              item: "crop top"
              color: "black"
              material: "stretchy fabric"
              fit: "tight"
              details: "shows midriff"
            bottom:
              item: "mini skirt"
              color: "red"
              length: "very short"
              material: "pleated"
              details: "barely covers her ass"
            feet:
              item: "heels"
              color: "black"
              height: "4 inch"
              style: "strappy"
            underwear_top:
              item: "push-up bra"
              style: "lace"
              color: "black"
              material: "lace and satin"
              appeal: "sexy"
            underwear_bottom:
              item: "thong"
              style: "g-string"
              color: "black"
              material: "lace"
              appeal: "very sexy"
            accessories:
              - "choker necklace"
              - "bold red lipstick"
```

### 2.5 Behavior System

```yaml
    behaviors:
      # Progressive consent gates
      gates:
        - id: "accept_compliment"
          conditions: "always"
          
        - id: "accept_flirting"
          conditions: "state.meters.emma.trust >= 20 or state.meters.emma.corruption >= 30"
          
        - id: "accept_date"
          conditions:
            any:
              - condition:
                  all:
                    - "state.meters.emma.attraction >= 40"
                    - "state.meters.emma.trust >= 30"
              - condition:
                  all:
                    - "state.meters.emma.corruption >= 40"
                    - "state.meters.emma.attraction >= 30"
                    
        - id: "accept_kiss"
          conditions:
            any:
              - condition:
                  all:
                    - "state.meters.emma.attraction >= 60"
                    - "state.meters.emma.trust >= 50"
                    - "state.flags.first_date_done == true"
              - condition:
                  all:
                    - "state.meters.emma.corruption >= 50"
                    - "state.meters.emma.arousal >= 40"
                    
        - id: "accept_groping"
          conditions:
            any:
              - condition:
                  all:
                    - "state.meters.emma.arousal >= 60"
                    - "state.meters.emma.trust >= 60"
                    - "state.meters.emma.attraction >= 70"
              - condition:
                  all:
                    - "state.meters.emma.corruption >= 60"
                    - "state.meters.emma.arousal >= 50"
                    
        - id: "accept_oral"
          conditions:
            all:
              - "state.meters.emma.arousal >= 70"
              - condition:
                  any:
                    - "state.meters.emma.trust >= 70"
                    - "state.meters.emma.corruption >= 60"
              - "state.privacy == 'high'"
              
        - id: "accept_sex"
          conditions:
            all:
              - "state.meters.emma.arousal >= 80"
              - condition:
                  any:
                    - condition:
                        all:
                          - "state.meters.emma.trust >= 80"
                          - "state.meters.emma.attraction >= 80"
                    - "state.meters.emma.corruption >= 70"
              - "state.privacy == 'high'"
              - "state.flags.protection_available == true or state.meters.emma.corruption >= 80"
        
        - id: "accept_anal"
          conditions:
            all:
              - "state.meters.emma.corruption >= 80"
              - "state.meters.emma.arousal >= 90"
              - "state.meters.emma.boldness >= 60"
              - "state.flags.anal_discussed == true"
              
        - id: "accept_public"
          conditions:
            all:
              - "state.meters.emma.corruption >= 70"
              - "state.meters.emma.boldness >= 70"
              - "state.meters.emma.arousal >= 80"
```

### 2.6 Dialogue and Schedule

```yaml
    dialogue:
      base_style: "intelligent but casual, occasional nervousness when flustered"
      
      vocabulary:
        normal: ["like", "maybe", "I guess", "sort of"]
        aroused: ["please", "need", "want", "god"]
        corrupted: ["fuck", "cock", "pussy", "dirty"]
        
      speech_patterns:
        shy: "trailing off sentences, lots of 'um' and 'uh'"
        confident: "direct statements, less hedging"
        aroused: "breathless, incomplete sentences"
        corrupted: "suggestive, double entendres"
        
    schedule:
      weekday:
        morning:
          location: "cafeteria"
          activity: "having breakfast"
          availability: "high"
        afternoon:
          location: "library"
          activity: "studying"
          availability: "medium"
        evening:
          location: "emma_room"
          activity: "relaxing"
          availability: "high"
        night:
          location: "emma_room"
          activity: "sleeping"
          availability: "none"
        late_night:
          location: "emma_room"
          activity: "sleeping"
          availability: "none"
      weekend:
        morning:
          location: "emma_room"
          activity: "sleeping in"
          availability: "low"
```
### 2.7 Movement Behavior

```yaml
    movement_preferences:
      # Where NPC is willing to go
      willing_zones:
        - zone: "campus"
          condition: "always"
        - zone: "downtown"
          condition: "meters.emma.trust >= 50 or meters.emma.corruption >= 40"
        - zone: "redlight"
          condition: "meters.emma.corruption >= 70"
          
      willing_locations:
        - location: "player_room"
          condition: "meters.emma.trust >= 40"
        - location: "hotel_room"
          condition: "meters.emma.arousal >= 70"
          
      transport_preferences:
        walk: "always"
        bus: "always"
        car: "meters.emma.trust >= 30"
        motorcycle: "meters.emma.boldness >= 60"
        
      follow_behavior:
        eager_threshold: 70  # attraction + trust
        willing_threshold: 40
        reluctant_threshold: 20
        
      refusal_reasons:
        trust_too_low: "I don't think I should go there with you..."
        inappropriate_location: "That's not really my kind of place."
        too_dangerous: "That seems dangerous. Let's not."
        wrong_time: "Not at this hour!"
```

---

## 3. Effects and Modifiers System

### 3.1 Effect Types

```yaml
# Meter modification
- type: "meter_change"
  target: "{character}"  # Can use variables
  meter: "arousal"
  operation: "add"  # add | subtract | set | multiply
  value: 10
  cap: true  # Respect min/max
  
# Apply temporary modifier
- type: "apply_modifier"
  target: "emma"
  modifier_id: "drunk"
  duration: 180  # minutes
  
# Apply permanent modifier
- type: "apply_permanent_modifier"
  target: "emma"
  modifier_id: "corrupted"
  
# Remove modifier
- type: "remove_modifier"
  target: "emma"
  modifier_id: "drunk"
  
# Conditional effect
- type: "conditional"
  condition: "state.meters.emma.trust >= 50"
  then:
    - type: "meter_change"
      target: "emma"
      meter: "arousal"
      value: 20
  else:
    - type: "meter_change"
      target: "emma"
      meter: "trust"
      value: -10
      
# Random effect
- type: "random"
  chances:
    - weight: 70
      effects:
        - type: "meter_change"
          target: "emma"
          meter: "attraction"
          value: 5
    - weight: 30
      effects:
        - type: "meter_change"
          target: "emma"
          meter: "attraction"
          value: -5
          
# Cascading effects
- type: "cascade"
  effects:
    - type: "meter_change"
      target: "emma"
      meter: "arousal"
      value: 10
    - type: "trigger"
      event: "emma_aroused"
      if: "state.meters.emma.arousal >= 50"
      
# Flag modification
- type: "flag_set"
  flag: "emma_kissed"
  value: true
  
# Inventory modification
- type: "inventory_add"
  item: "emma_panties"
  count: 1
  
# Time advancement
- type: "advance_time"
  slots: 1
  
# Location change
- type: "move_to"
  location: "emma_room"
  with_characters: ["emma"]
  
# Outfit change
- type: "outfit_change"
  character: "emma"
  outfit: "revealing_outfit"
  
# Clothing removal
- type: "clothing_remove"
  character: "emma"
  layers: ["outerwear", "top"]
  
# Node transition
- type: "goto_node"
  node: "emma_bedroom_scene"
```

### 3.2 Modifier Rules

```yaml
modifier_system:
  # How modifiers combine
  stacking_rules:
    default: "highest"  # highest | additive | multiplicative | replace
    
    specific_rules:
      arousal_modifiers: "additive"
      inhibition_modifiers: "multiplicative"
      
  # Priority resolution
  priority_groups:
    - name: "status_effects"
      priority: 100
      members: ["poisoned", "paralyzed", "unconscious"]
    - name: "intoxication"
      priority: 90
      members: ["drunk", "high", "drugged"]
    - name: "emotional_states"
      priority: 50
      members: ["aroused", "angry", "sad", "happy"]
    - name: "relationship_states"
      priority: 30
      members: ["trusting", "suspicious", "in_love"]
    - name: "environmental"
      priority: 20
      members: ["hot", "cold", "wet", "tired"]
      
  # Conflicting modifiers
  exclusions:
    - group: "intoxication"
      exclusive: true  # Only one active at a time
    - group: "temperature"
      exclusive: true
      members: ["freezing", "cold", "hot", "overheated"]
      
  # Modifier interactions
  interactions:
    - source: "drunk"
      target: "aroused"
      effect: "target.effectiveness *= 1.5"
    - source: "tired"
      target: "aroused"
      effect: "target.effectiveness *= 0.5"
```

---
## 4. World Structure and Locations

### 4.1 Hierarchical World System

The game world uses a three-tier spatial hierarchy:

1. **World Level**: Contains all zones, manages inter-zone travel
2. **Zone Level**: Thematic areas containing multiple locations
3. **Location Level**: Individual rooms/areas where scenes occur

### 4.2 World Configuration (`world.yaml`)

```yaml
world_config:
  id: "game_world"
  name: "City and Campus"
  
  # World-level settings
  settings:
    time_passes_during_travel: true
    npcs_have_own_movement: true
    weather_affects_movement: true
    random_travel_events: true
    fog_of_war: true  # Undiscovered areas hidden
    
  # Global travel methods
  transport_methods:
    walk:
      always_available: true
      base_time: 30  # minutes per zone
      energy_cost: 20
      weather_affected: true
      
    bike:
      requires: "inventory.bike"
      base_time: 15
      energy_cost: 10
      weather_affected: true
      unavailable_conditions: ["weather == 'storm'"]
      
    car:
      requires: "inventory.car_keys and flag.has_license"
      base_time: 10
      fuel_cost: 1
      money_cost: 2  # parking
      capacity: 4  # can bring 3 NPCs
      
    bus:
      available_times: ["morning", "afternoon", "evening"]
      base_time: 20
      money_cost: 5
      routes_defined: true  # specific zone connections
      
    taxi:
      always_available: true
      base_time: 12
      money_cost_formula: "15 * distance"
      surge_pricing:
        night: 1.5
        weekend: 1.3
        
  # Distance matrix for zone travel
  zone_distances:
    campus:
      downtown: 2
      suburbs: 3
      industrial: 4
    downtown:
      campus: 2
      suburbs: 2
      industrial: 1
```

### 4.3 Zone Definitions (`zones.yaml`)

```yaml
zones:
  - id: "campus"
    name: "University Campus"
    type: "educational"
    
    # Discovery and access
    unlock:
      discovered: true  # Known from start
      accessible: true  # Can enter from start
      
    unlock_conditions:
      discovered: "always"
      accessible: "always"
      
    # Zone properties
    properties:
      size: "large"
      security: "medium"
      privacy: "low"
      law_enforcement: "campus_security"
      
    # Zone-wide rules
    zone_rules:
      reputation_matters: true
      dress_code: "casual"
      restricted_hours:
        late_night: ["library", "cafeteria"]
        
    # Entry/exit points
    world_connections:
      - id: "main_gate"
        location: "campus_entrance"
        allows: ["walk", "bike", "car", "taxi"]
        bidirectional: true
        
      - id: "bus_stop"
        location: "campus_square"
        allows: ["bus"]
        schedule: "every_30_minutes"
        
    # Zone events
    events:
      on_first_enter:
        narrative: "The campus sprawls before you."
        effects:
          - type: "flag_set"
            flag: "entered_campus"
            
  - id: "downtown"
    name: "City Downtown"
    type: "urban"
    
    unlock:
      discovered: false
      accessible: false
      
    unlock_conditions:
      discovered:
        any:
          - "flag.heard_about_downtown"
          - "day >= 3"
      accessible:
        all:
          - "zone.downtown.discovered"
          - any:
              - "money >= 20"
              - "inventory.bike"
              
    properties:
      size: "very_large"
      security: "low"
      privacy: "very_low"
      crime_rate: "medium"
      
    zone_rules:
      night_dangers: true
      commercial_zone: true
      
    world_connections:
      - id: "subway_station"
        location: "downtown_station"
        allows: ["subway"]
        
      - id: "highway_exit"
        location: "downtown_parking"
        allows: ["car", "taxi"]
```

### 4.4 Location Definitions (`locations.yaml`)

```yaml
locations:
  # Transition location (zone entry/exit)
  - id: "campus_entrance"
    name: "Campus Main Gate"
    zone: "campus"
    type: "transition"
    
    properties:
      discovered: true
      always_accessible: true
      privacy: "none"
      
    # Local connections within zone
    connections:
      - to: "campus_square"
        type: "path"
        bidirectional: true
        distance: "short"
        visibility: "clear"  # destination known
        
      - to: "security_booth"
        type: "door"
        bidirectional: true
        distance: "immediate"
        visibility: "clear"
        
    # World exit point
    world_exit:
      enabled: true
      transport_options: ["walk", "bike", "car", "taxi"]
      
    description:
      default: "The main gate stands open."
      night: "The gate is lit by streetlamps."
      
  # Standard room
  - id: "dorm_room"
    name: "Your Dorm Room"
    zone: "campus"
    type: "room"
    
    properties:
      discovered: true
      privacy: "high"
      owned_by: "player"
      
    access:
      locked: true
      unlock_methods:
        - item: "dorm_key"
        - flag: "window_open"
          
    connections:
      - to: "dorm_hallway"
        type: "door"
        bidirectional: true
        distance: "immediate"
        visibility: "clear"
        lockable: true
        
    features: ["bed", "desk", "computer"]
    
  # Hidden/unexplored location
  - id: "mysterious_door"
    name: "Unmarked Door"
    zone: "campus"
    type: "room"
    
    properties:
      discovered: true  # Can see door
      explored: false  # Don't know what's inside
      
    display:
      unexplored_name: "Unmarked Door"
      explored_name: "Storage Room"
      unexplored_description: "A plain door."
      explored_description: "A dusty storage room."
      
    exploration:
      type: "blind"  # Must enter to discover
      reveal_on_entry: true
      
    access:
      locked: true
      unlock_methods:
        - item: "master_key"
        - skill_check:
            skill: "lockpicking"
            difficulty: 40
            
    revelation_effects:
      - type: "flag_set"
        flag: "found_storage_room"
        
  # NPC room with special access
  - id: "emma_room"
    name: "Emma's Room"
    zone: "campus"
    type: "room"
    
    properties:
      discovered: false
      privacy: "high"
      owned_by: "emma"
      
    discovery_conditions:
      any:
        - "flag.emma_mentioned_room"
        - "meters.emma.trust >= 30"
        
    access:
      locked: true
      unlock_methods:
        - flag: "emma_invites_in"
          requires_presence: "emma"
        - item: "emma_spare_key"
          condition: "flag.emma_gave_key"
          
    connections:
      - to: "dorm_hallway"
        type: "door"
        bidirectional: false  # Can't enter from hallway
        from_inside: true  # Can always leave
        visibility: "hidden"  # Unknown until discovered
        
    hidden_until_discovered: true
```

### 4.5 Movement System

```yaml
movement_system:
  # Zone-level travel
  zone_travel:
    requires_exit_point: true
    consumes_time: true
    allows_companions: true
    
    time_calculation: "base_time * distance * weather_modifier"
    
    interruption_events:
      enabled: true
      types: ["encounter", "breakdown", "weather"]
      
  # Local movement (within zone)
  local_movement:
    base_time: 1  # minute
    
    time_modifiers:
      distance:
        immediate: 0
        short: 1
        medium: 3
        long: 5
      movement_type:
        door: 0
        stairs: 1
        path: 2
        climb: 3
      conditions:
        injured: 2.0
        drunk: 1.5
        running: 0.5
        
  # Movement restrictions
  restrictions:
    energy_minimum: 5
    requires_consciousness: true
    check_npc_consent: true
    respect_boundaries: true
    
  # Group movement
  group_movement:
    leader_decides: true
    followers_can_refuse: true
    apply_slowest_speed: true
    
    npc_willingness:
      check_conditions: true
      based_on_relationship: true
      based_on_destination: true
```

### 4.6 Exploration and Discovery

```yaml
exploration:
  # Discovery methods
  discovery:
    proximity:
      enabled: true
      auto_reveal_adjacent: true
      
    social:
      learn_from_npcs: true
      overhear_conversations: true
      find_maps: true
      
    active_search:
      action: "explore_area"
      energy_cost: 10
      time_cost: 30
      reveal_hidden: true
      
  # Visibility levels
  visibility:
    clear:
      shows_destination: true
      shows_requirements: true
      
    obscured:
      shows_destination: true
      shows_requirements: false
      
    hidden:
      shows_destination: false
      shows_requirements: false
      
  # Map system
  map:
    fog_of_war: true
    reveal_on_discovery: true
    show_connections: "only_known"
    show_details: "only_explored"
    
  # Unlock progression
  progression:
    zones:
      story_based: true  # Unlock through plot
      exploration_based: true  # Find through exploring
      social_based: true  # Learn from NPCs
      purchase_based: true  # Buy access
      
    locations:
      automatic_nearby: true
      key_items: true
      relationship_gates: true
      time_gates: true
      skill_checks: true
```

### 4.7 Movement Actions

```yaml
# Movement action structure
movement_actions:
  # Local movement (within zone)
  - type: "move_local"
    from: "current_location"
    to: "target_location"
    validate:
      - connection_exists
      - meets_requirements
      - has_energy
    effects:
      - advance_time: "calculated"
      - reduce_energy: "calculated"
      - trigger_events: "on_enter"
      
  # Zone travel
  - type: "travel_zone"
    from: "current_zone"
    to: "target_zone"
    method: "transport_type"
    validate:
      - zone_accessible
      - has_exit_point
      - can_afford_transport
      - meets_transport_requirements
    effects:
      - advance_time: "base * distance"
      - reduce_resources: "by_transport"
      - move_companions: "if_willing"
      - trigger_events: "travel_events"
      
  # Exploration
  - type: "explore"
    location: "current"
    validate:
      - has_energy: 10
      - has_time: true
    effects:
      - discover_connections: true
      - reveal_hidden: "chance_based"
      - advance_time: 30
      - reduce_energy: 10
      
  # Fast travel
  - type: "fast_travel"
    to: "known_location"
    validate:
      - location_discovered: true
      - not_in_combat: true
      - not_in_scene: true
    effects:
      - instant_move: true
      - advance_time: "calculated"
      - skip_encounters: true
```

### 4.8 Location-Based Events

```yaml
location_events:
  # Triggered by entering locations
  on_enter:
    first_time:
      check: "not flag.location_{id}_visited"
      effects:
        - flag_set: "location_{id}_visited"
        - discovery_xp: 10
        
    conditional:
      - condition: "time_slot == 'night'"
        narrative_modifier: "night_description"
      - condition: "weather == 'rain'"
        narrative_modifier: "rain_description"
        
  # Random encounters
  random_encounters:
    chance: 0.1
    types:
      - npc_meeting
      - item_discovery
      - mini_event
      
  # Scheduled events
  scheduled:
    - location: "library"
      time: "afternoon"
      day: 7
      event: "midterm_study_panic"
      
  # NPC presence
  npc_schedules:
    emma:
      morning:
        cafeteria: 0.8
        emma_room: 0.2
      afternoon:
        library: 0.7
        campus_square: 0.3
      evening:
        emma_room: 0.9
        gym: 0.1
```

---

## 5. Items (`items.yaml`)

```yaml
items:
  - id: "aphrodisiac"
    name: "Strange Pink Pill"
    category: "consumable"
    description: "A small pink pill with unknown effects"
    value: 100
    tags: ["drug", "corruption"]
    
    effects_on_use:
      target: "character"  # or "player"
      effects:
        - type: "meter_change"
          meter: "arousal"
          value: 50
        - type: "meter_change"
          meter: "corruption"
          value: 10
        - type: "apply_modifier"
          modifier_id: "aphrodisiac_effect"
          duration: 120
          
    can_give: true
    single_use: true
    
  - id: "emma_panties"
    name: "Emma's Panties"
    category: "trophy"
    description: "A pair of Emma's panties, still warm"
    value: 0
    tags: ["intimate", "emma"]
    droppable: false
    
    obtain_conditions:
      all:
        - "state.meters.emma.corruption >= 60"
        - "state.flags.emma_undressed == true"
```

---

## 6. Story Nodes (`nodes.yaml`)

### 6.1 Node Types

```yaml
nodes:
  - id: "intro"
    type: "scene"  # scene | interactive | branch | ending
    category: "main_story"
    
    # Entry conditions
    preconditions:
      all:
        - "state.day == 1"
        - "state.time_slot == 'morning'"
        
    # What happens when entering
    entry_effects:
      - type: "flag_set"
        flag: "game_started"
        value: true
        
    # Narrative content
    narrative:
      text: |
        You wake up in your dorm room, sunlight streaming through the window.
        Today is the first day of the new semester.
        
    # Choices presented
    choices:
      - text: "Get up and get ready"
        effects:
          - type: "advance_time"
            slots: 1
        goto: "morning_routine"
      - text: "Sleep in"
        effects:
          - type: "meter_change"
            target: "player"
            meter: "energy"
            value: 20
        goto: "late_morning"
```

### 6.2 Interactive Scenes

```yaml
  - id: "emma_bedroom_intimate"
    type: "interactive"
    category: "romance"
    tags: ["emma", "intimate", "nsfw"]
    
    # Location requirement uses zone/location
    location_requirement:
      zone: "campus"
      location: "library"
      
    # Can specify movement as entry
    entry_movement:
      type: "move_local"
      to: "library_private_room"
      with: ["emma"]
      
    # Zone-aware exits
    exit_options:
      - text: "Leave campus"
        type: "travel_zone"
        to: "downtown"
        method: "bus"
      - text: "Go to your room"
        type: "move_local"
        to: "dorm_room"
    required_privacy: "high"
    
    preconditions:
      all:
        - "emma in state.present_characters"
        - "state.meters.emma.arousal >= 60"
        - "emma.behaviors.accept_intimate"
        
    # Initial state
    scene_state:
      clothing_emma: "current"  # or specific outfit
      position: "standing_close"
      mood: "intimate"
      
    # Dynamic options based on state
    dynamic_actions:
      - id: "kiss"
        text: "Kiss her"
        conditions: "always"
        effects:
          - type: "meter_change"
            target: "emma"
            meter: "arousal"
            value: 10
            
      - id: "undress_top"
        text: "Remove her top"
        conditions:
          all:
            - "state.meters.emma.arousal >= 70"
            - "emma.clothing.top != null"
        effects:
          - type: "clothing_remove"
            character: "emma"
            layers: ["top"]
          - type: "meter_change"
            target: "emma"
            meter: "arousal"
            value: 15
            
      - id: "go_further"
        text: "Go further"
        conditions:
          all:
            - "state.meters.emma.arousal >= 80"
            - "emma.behaviors.accept_sex"
        goto: "emma_sex_scene"
        
    # AI behavior hints
    ai_instructions:
      tone: "sensual, romantic"
      include: ["physical descriptions", "emma's responses", "consent checks"]
      avoid: ["sudden escalation", "out of character behavior"]
      respect_state: true  # Must follow current meters/modifiers
```

---

## 7. Random Events (`events.yaml`)

```yaml
events:
  - id: "emma_drunk_text"
    category: "relationship"
    weight: 10  # Relative probability
    
    preconditions:
      all:
        - "state.time_slot in ['night', 'late_night']"
        - "state.meters.emma.attraction >= 50"
        - "emma not in state.present_characters"
        - "state.day_of_week in ['friday', 'saturday']"
        
    cooldown: 7  # Days before can trigger again
    
    effects:
      - type: "flag_set"
        flag: "emma_drunk_texting"
        value: true
        
    narrative: |
      Your phone buzzes. It's Emma:
      "heyyyy... cant stop thinking bout u... maybe we should talk? 😳"
      
    choices:
      - text: "Come over"
        effects:
          - type: "meter_change"
            target: "emma"
            meter: "corruption"
            value: 5
        goto: "emma_drunk_visit"
      - text: "Let's talk tomorrow"
        effects:
          - type: "meter_change"
            target: "emma"
            meter: "trust"
            value: 10
```

---

## 8. Milestones (`arcs.yaml`)

```yaml
milestones:
  - id: "emma_corruption_path"
    name: "Emma's Corruption"
    category: "character_development"
    
    stages:
      - id: "innocent"
        conditions:
          all:
            - "state.meters.emma.corruption < 20"
        description: "Emma is pure and innocent"
        
      - id: "curious"
        conditions:
          all:
            - "state.meters.emma.corruption >= 20"
            - "state.meters.emma.corruption < 40"
        unlock_effects:
          - type: "unlock_outfit"
            character: "emma"
            outfit: "sexy_underwear"
        description: "Emma is becoming curious about her desires"
        
      - id: "experimenting"
        conditions:
          all:
            - "state.meters.emma.corruption >= 40"
            - "state.meters.emma.corruption < 60"
        unlock_effects:
          - type: "unlock_actions"
            actions: ["suggest_roleplay", "introduce_toys"]
        description: "Emma is actively experimenting"
        
      - id: "corrupted"
        conditions:
          all:
            - "state.meters.emma.corruption >= 60"
            - "state.meters.emma.corruption < 80"
        unlock_effects:
          - type: "unlock_outfit"
            character: "emma"
            outfit: "fetish_outfit"
        description: "Emma has embraced her dark desires"
        
      - id: "depraved"
        conditions:
          all:
            - "state.meters.emma.corruption >= 80"
        unlock_effects:
          - type: "unlock_ending"
            ending: "emma_corruption_ending"
        achievement:
          title: "Complete Corruption"
          description: "Fully corrupted Emma"
```

---

## 9. AI Integration Instructions

### 9.1 Writer Model Prompts

```yaml
writer_prompts:
  standard:
    system: |
      You are narrating an adult interactive fiction game.
      Content rating: {content_rating}
      
      CRITICAL RULES:
      1. Stay in character for all NPCs
      2. Respect current game state and meters
      3. Check consent gates before intimate content
      4. Include sensory details and character reactions
      5. Track clothing state accurately
      6. End with clear moment for player input
      
    template: |
      CURRENT SCENE: {node_id}
      LOCATION: {location_name} (Privacy: {privacy_level})
      TIME: Day {day}, {time_slot}
      
      CHARACTERS PRESENT:
      {character_cards}
      
      RECENT ACTIONS:
      {last_3_actions}
      
      PLAYER ACTION: "{player_input}"
      
      Generate 2-3 paragraphs continuing the scene.
      {special_instructions}
      
  intimate:
    additional_instructions: |
      This is an intimate scene. Include:
      - Physical descriptions and sensations
      - Emotional responses
      - Consent and enthusiasm
      - Current arousal levels affecting behavior
      - Corruption/boldness affecting actions
      Current clothing state: {clothing_state}
```

### 9.2 Checker Model Prompts

```yaml
checker_prompts:
  extract_state_changes:
    system: |
      Extract state changes from narrative text.
      Return valid JSON only.
      
    template: |
      NARRATIVE: "{narrative}"
      PLAYER ACTION: "{player_action}"
      
      Extract and return as JSON:
      {
        "meter_changes": {
          "character_id": {
            "meter_name": change_value
          }
        },
        "clothing_changes": {
          "character_id": {
            "removed": [],
            "displaced": []
          }
        },
        "flags": {
          "flag_name": value
        },
        "modifiers_applied": [
          {"character": "id", "modifier": "modifier_id"}
        ]
      }
```

### 9.3 Character Card Template for AI

```yaml
character_card_template: |
  === {name} ===
  APPEARANCE: {appearance_description}
  OUTFIT: {current_outfit_description}
  
  CURRENT STATE:
  - Trust: {trust_level} ({trust}/100) - {trust_description}
  - Attraction: {attraction_level} ({attraction}/100) - {attraction_description}  
  - Arousal: {arousal_level} ({arousal}/100) - {arousal_description}
  - Corruption: {corruption_level} ({corruption}/100) - {corruption_description}
  - Boldness: {boldness_level} ({boldness}/100) - {boldness_description}
  
  ACTIVE MODIFIERS: {modifier_list}
  
  BEHAVIOR NOTES:
  - Will accept: {acceptable_actions}
  - Will reject: {rejected_actions}
  - Current mood: {mood}
  - Dialogue style: {dialogue_style}
  
  RECENT CONTEXT: {recent_events}
```

---

## 10. Runtime State Structure

```yaml
game_state:
  # Session info
  session_id: "unique_session_id"
  game_id: "college_romance"
  version: "1.0.0"
  
  # Story position
  current_node: "library_study"
  visited_nodes: ["intro", "morning_routine", "meet_emma"]
  
  # Time and location
  day: 3
  time_slot: "afternoon"
  location_current: "library"
  location_previous: "dorm_room"
  
  # Characters
  present_characters: ["emma"]
  
  # Meters (per character + player)
  meters:
    player:
      health: 100
      energy: 75
      money: 250
      confidence: 60
    emma:
      trust: 45
      attraction: 62
      arousal: 35
      corruption: 15
      boldness: 25
      academic_stress: 40
      
  # Active modifiers
  modifiers:
    emma:
      - id: "slightly_aroused"
        remaining: null  # Permanent until condition changes
      - id: "happy"
        remaining: 30  # minutes
        
  # Flags and variables
  flags:
    game_started: true
    emma_met: true
    first_kiss: true
    emma_route: "romance"  # romance | corruption | both
    
  # Inventory
  inventory:
    condoms: 3
    flowers: 1
    wine: 0
    
  # Clothing states
  clothing_states:
    emma:
      current_outfit: "casual_day"
      removed_layers: []
      displaced_layers: []
  
  # Location tracking
  location:
    current_zone: "campus"
    current_location: "library"
    previous_zone: "campus"
    previous_location: "dorm_room"
    
  # Discovery tracking
  discovered:
    zones: ["campus", "downtown"]
    locations: {
      "campus": ["dorm_room", "library", "cafeteria"],
      "downtown": ["downtown_station"]
    }
    
  # Movement state
  movement:
    available_transport: ["walk", "bike"]
    current_vehicle: null
    companion_npcs: ["emma"]
    movement_modifiers: []
    
  # Zone-specific states
  zone_states:
    campus:
      reputation: 50
      security_alert: false
    downtown:
      first_visit: false
      known_locations: 3    
  
  # History for context
  action_history: [
    {action: "compliment emma", response: "she blushed"},
    {action: "suggest coffee", response: "she agreed"},
    {action: "hold hand", response: "she squeezed back"}
  ]
  
  # Stats tracking
  statistics:
    choices_made: 47
    days_played: 3
    emma_interactions: 23
    intimate_scenes: 2
```

---

## 11. Save System

```yaml
save_format:
  version: "3.0.0"
  timestamp: "2024-01-21T15:30:00Z"
  
  metadata:
    slot: 1
    description: "At library with Emma"
    playtime: 3600  # seconds
    completion: 35  # percentage
    thumbnail: "data:image/png;base64,..."  # Optional screenshot
    
  state: 
    # Complete game_state object
    
  config:
    # Game configuration used
    
  # Location data
  location_data:
    current_position:
      zone: "campus"
      location: "library"
    discovered_zones: ["campus", "downtown"]
    discovered_locations: {}  # Map of zone -> location list
    explored_locations: []  # Fully explored
    unlocked_zones: []
    unlocked_locations: []
    
  # Movement data
  movement_data:
    available_transport: []
    owned_vehicles: []
    transport_unlocks: []
    fast_travel_points: []

  settings:
    # Player preferences
    text_speed: "normal"
    auto_save: true
    content_filter: "none"
```

---

## 12. Implementation Notes

### For Game Engine

1. **Meter System**
   - Load game-specific meters from config.yaml
   - Track values per character
   - Evaluate thresholds for named ranges
   - Apply decay rates daily
   - Check reveal conditions each turn

2. **Modifier System**
   - Evaluate modifier conditions each action
   - Apply modifiers based on priority
   - Handle stacking/exclusion rules
   - Update duration-based modifiers
   - Compile effects for character cards

3. **Character Cards**
   - Generate dynamically from current state
   - Include active modifiers in description
   - Adjust behavior based on meters
   - Provide context-appropriate descriptions

4. **State Management**
   - Validate all state changes
   - Cascade related effects
   - Maintain history for AI context
   - Support save/load with full state

### For AI Integration

1. **Writer Model**
   - Include full character cards in prompt
   - Provide recent action history
   - Specify content boundaries based on meters
   - Give clear instructions for tone/style

2. **Checker Model**
   - Use structured extraction prompts
   - Validate JSON output
   - Map keywords to state changes
   - Handle edge cases gracefully

### For Frontend

1. **Display Systems**
   - Show visible meters with icons
   - Update character portraits based on state
   - Display clothing state visually
   - Animate meter changes

2. **Interaction**
   - Show available actions based on conditions
   - Gray out unavailable options
   - Provide hover hints for requirements
   - Quick save/load functionality

### Content Guidelines

1. **Progressive Intimacy**
   - Start with trust building
   - Attraction before arousal
   - Consent gates for all intimate content
   - Corruption provides alternate paths

2. **Meter Balance**
   - Small changes (±5) for minor actions
   - Large changes (±20) for significant events
   - Decay creates urgency
   - Thresholds create clear progression

3. **Modifier Usage**
   - Temporary for states (drunk, aroused)
   - Permanent for achievements (corrupted)
   - Visual cues in descriptions
   - Behavioral changes in AI responses

---


## Appendix: Common Meter Configurations

### Romance Game Meters
```yaml
trust: [0-100]
attraction: [0-100]
arousal: [0-100]
corruption: [0-100]
boldness: [0-100]
love: [0-100]
jealousy: [0-100]
```

### RPG Adventure Meters
```yaml
health: [0-100]
mana: [0-100]
stamina: [0-100]
corruption: [0-100]
reputation: [-100 to 100]
karma: [-100 to 100]
```

### Survival Horror Meters
```yaml
health: [0-100]
sanity: [0-100]
fear: [0-100]
corruption: [0-100]
infection: [0-100]
hunger: [0-100]
```

