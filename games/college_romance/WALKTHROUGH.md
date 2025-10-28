# Campus Hearts - Testing Walkthrough

**Game:** college_romance
**Version:** 1.1.0
**Purpose:** Quick testing guide for core functionality

---

## Path 1: Emma Romance Route

**Goal:** Meet Emma, build relationship, achieve Emma ending

### Steps:

1. **Start Game**
   - Location: campus_dorm_room
   - Time: Day 1, Morning, 08:00
   - Flags: met_emma=false, met_zoe=false

2. **Morning Choice**
   - Choose: "Grab your backpack and cross the quad before class"
   - **Expected:** Move to campus_quad
   - **Expected:** Meet Emma (met_emma=true)
   - **Expected:** Emma trust increases to 21

3. **Quad Scene**
   - Choose: "Offer to walk through the stats problem set together"
   - **Expected:** emma_study_session=true
   - **Expected:** Emma trust=27, player mind=38

4. **Afternoon Loop**
   - Choose: "Head to the library to follow up with Emma"
   - **Expected:** Emma trust=35

5. **Library Scene**
   - Choose: "Share a personal anecdote about bombing your first presentation"
   - **Expected:** Emma trust=40, attraction=14
   - Returns to afternoon loop

6. **Afternoon Loop (again)**
   - Choose: "Call it here and figure out tonight"

7. **Evening Choice**
   - Choose: "Text Emma and plan a quiet walk"
   - **Expected:** Emma trust=48

8. **Evening Walk**
   - Choose: "Tell Emma you're excited about where this is heading"
   - **Expected:** emma_final_choice=true
   - **Expected:** Emma attraction=24

9. **Ending**
   - **Expected:** Emma ending achieved
   - **Expected:** Title: "Shared Notes"

---

## Path 2: Zoe Romance Route

**Goal:** Meet Zoe, build relationship, achieve Zoe ending

### Steps:

1. **Start Game**
   - Location: campus_dorm_room
   - Time: Day 1, Morning, 08:00

2. **Morning Choice**
   - Choose: "Detour to the student cafe for caffeine and gossip"
   - **Expected:** Meet Zoe (met_zoe=true)
   - **Expected:** Zoe trust=19

3. **Cafe Scene**
   - Choose: "Introduce yourself with equally corny barista banter"
   - **Expected:** Zoe attraction=17, player charm=44

4. **Afternoon Loop**
   - Choose: "Swing by the cafe during Zoe's rehearsal break"
   - **Expected:** Zoe attraction=23

5. **Rehearsal Scene**
   - Choose: "Give thoughtful feedback on her new song"
   - **Expected:** zoe_band_invite=true
   - **Expected:** Zoe trust=26

6. **Evening Choice**
   - Choose: "Head downtown to catch Zoe's set"
   - **Expected:** Zoe attraction=32

7. **Basement Show**
   - Choose: "Stay after the set to help pack gear"
   - **Expected:** zoe_final_choice=true
   - **Expected:** Zoe trust=34

8. **Ending**
   - **Expected:** Zoe ending achieved
   - **Expected:** Title: "Second Encore"

---

## Quick Verification Points

### Location Changes
- intro_dorm → campus_quad (when choosing Emma)
- Location displays correctly in UI header

### Character Schedules
- Emma appears in campus_quad only after met_emma=true
- Zoe appears in campus_cafe only after met_zoe=true

### Time Display
- UI shows both "Morning" slot and "08:00" time
- Updates as game progresses

### Meters
- Emma: trust starts at 15, attraction at 10
- Zoe: trust starts at 15, attraction at 10
- Player: mind starts at 35, charm at 40

---

**Last Updated:** 2025-10-28
