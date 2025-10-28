# Movement Sandbox - Testing Game

A comprehensive test game for the PlotPlay zone travel system with entry/exit points and multiple travel methods.

## Purpose

This game demonstrates and allows testing of:

1. **Zone Travel with Entry/Exit Points** (`use_entry_exit: true`)
2. **Multiple Travel Methods** (walk, bike, car)
3. **Method-Specific Zone Connections** (some zones are only reachable by certain methods)
4. **Travel Time Calculation** based on distance and method
5. **Local Movement** within zones

## Game Structure

### Zones

**Downtown District** (Starting zone)
- 4 locations: Central Plaza, Transit Station, Highway On-Ramp, Shopping District
- Entrances: Plaza, Station
- Exit: Highway Ramp
- Connections:
  - To Suburbs: walk/bike/car (3 units)
  - To Industrial: bike/car only (5 units)

**Suburban Neighborhood**
- 5 locations: Park Entrance, Community Park, Main Street, Highway Exit, Cul-de-Sac
- Entrances: Park Entrance, Main Street
- Exit: Highway Exit
- Connections:
  - To Downtown: walk/bike/car (3 units)
  - To Industrial: car only (6 units)

**Industrial District**
- 5 locations: North Gate, South Gate, Central Yard, Main Warehouse, Highway Junction
- Entrances: North Gate, South Gate
- Exit: Highway Junction
- Connections:
  - To Downtown: bike/car (5 units)
  - To Suburbs: car only (6 units)

### Travel Methods

- **Walk**: 5 minutes per distance unit (slowest, pedestrian-friendly)
- **Bike**: 3 minutes per distance unit (medium speed)
- **Car**: 1 minute per distance unit (fastest)

### Example Travel Times

- Walk to Suburbs: 3 × 5 = **15 minutes**
- Bike to Suburbs: 3 × 3 = **9 minutes**
- Car to Suburbs: 3 × 1 = **3 minutes**
- Bike to Industrial: 5 × 3 = **15 minutes**
- Car to Industrial: 5 × 1 = **5 minutes**
- Car: Suburbs → Industrial: 6 × 1 = **6 minutes**

## Testing Scenarios

### 1. Entry Point Selection
- Travel to Suburbs and choose between "Park Entrance" or "Main Street"
- Travel to Industrial and choose between "North Gate" or "South Gate"
- Verify you arrive at the selected entry point

### 2. Travel Method Selection
- Travel to Suburbs using different methods (walk, bike, car)
- Verify travel time changes based on method
- Try to walk to Industrial (should not be available)

### 3. Method Restrictions
- From Suburbs, try to travel to Industrial
- Only "car" should be available as a method
- Verify other methods are not shown

### 4. Local Movement
- Within each zone, use the directional exits (N, S, E, W, etc.)
- Verify local movement takes 2 minutes (base_time)

### 5. Exit Points
- Travel from Downtown using the Highway Ramp
- Travel from Suburbs using the Highway Exit
- Travel from Industrial using the Highway Junction
- (Note: Current implementation uses first entrance if not specified)

## Frontend UI Expected Behavior

When in the Movement panel, you should see:

**Local Exits** (if any):
- Simple directional buttons (N, S, E, W)
- Click to move within the zone

**Zone Travel** (separated by a divider):

For **single method/entry**:
- Simple button: "Travel to {Zone Name}"

For **multiple methods or entries**:
- Zone name at top
- Dropdown for entry location (if multiple available)
- "via" text
- Dropdown for travel method (if multiple available)
- "Go" button

## Configuration Highlights

```yaml
movement:
  base_time: 2              # Minutes for local movement
  use_entry_exit: true      # Enable entry/exit point system
  methods:
    - walk: 5               # 5 minutes per distance unit
    - bike: 3               # 3 minutes per distance unit
    - car: 1                # 1 minute per distance unit
```

## How to Play

1. Start the game with ID: `movement_sandbox`
2. Use the Movement panel to navigate
3. Test different combinations of methods and entry points
4. Observe the time progression
5. Move around within zones to test local movement

## Technical Details

- **Game ID**: `movement_sandbox`
- **Starting Location**: `downtown_plaza` (Central Plaza)
- **Total Locations**: 14 across 3 zones
- **Time System**: Hybrid mode (clock + slots)
- **Economy**: Enabled ($100 starting money)
