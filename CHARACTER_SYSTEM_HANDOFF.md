# Character System & Memory Tagging Implementation - Handoff Document

**Date**: 2025-10-29
**Status**: Backend Complete ✅ | Frontend Ready for Implementation ⏳

---

## 🎯 Project Overview

This document describes the implementation of a **character-tagged memory system** and **improved character UI** for PlotPlay. The system allows:

1. **AI-generated memories** tagged with character IDs (via Checker model)
2. **Per-character memory filtering** (show only memories involving that character)
3. **Compact character cards** (reduced space usage by 60%)
4. **Character Notebook** modal with full profiles, gates, and memory timeline
5. **Story Events** page for general atmosphere/world memories

---

## ✅ Completed Work

### Phase 1: Memory System Backend (COMPLETE)

**Files Modified**:
- `backend/app/core/state_manager.py` (line 90)
- `backend/app/engine/prompt_builder.py` (lines 597-615, 100-118)
- `backend/app/engine/turn_manager.py` (lines 135-181, 466-512)

**What Changed**:

1. **Memory Structure**:
   ```python
   # OLD: memory_log: list[str]
   # NEW: memory_log: list[str | dict]

   # New format:
   {
       "text": "Alex shared her dream of opening a bookshop-café",
       "characters": ["alex"],  # Character IDs involved/mentioned
       "day": 1
   }
   ```

2. **Checker Prompt Updates**:
   - Checker now returns structured memory objects with character tags
   - Instructions to tag ALL characters involved or mentioned
   - Use "player" for player, NPC IDs for NPCs
   - Empty `characters` array for general atmosphere memories

3. **Memory Processing**:
   - Validates character IDs exist in game
   - Handles both legacy string and new dict formats (backward compatible)
   - Keeps last 20 memories in state
   - Limits to 1-2 memories per turn

**Tests**: ✅ All 199 backend tests passing

---

### Phase 2: Character API Endpoints (COMPLETE)

**Files Modified**:
- `backend/app/api/game.py` (lines 524-676)
- `frontend/src/services/gameApi.ts` (lines 199-256, 478-491)

**New Endpoints**:

#### 1. `GET /session/{id}/characters`
Returns list of all characters for notebook sidebar.

**Response**:
```json
{
  "player": {
    "id": "player",
    "name": "You"
  },
  "characters": [
    {
      "id": "alex",
      "name": "Alex Ramos",
      "present": true,
      "location": "cafe_patio"
    }
  ]
}
```

#### 2. `GET /session/{id}/character/{character_id}`
Returns full character data with filtered memories.

**Key Features**:
- **Player**: Gets ALL memories (tagged and untagged)
- **NPCs**: Get only memories where they're tagged (last 5)
- **Gates**: Evaluated with current allow/deny status
- **State**: Current meters, modifiers, attire, wardrobe

**Response**:
```json
{
  "id": "alex",
  "name": "Alex Ramos",
  "age": 24,
  "gender": "female",
  "pronouns": ["she", "her"],
  "personality": {
    "core_traits": "friendly, perceptive, quietly ambitious",
    "quirks": "taps the rim of her mug when thinking",
    "values": "honesty, thoughtful gestures"
  },
  "appearance": "Alex's wavy brown hair...",
  "dialogue_style": "Warm, observant...",
  "gates": [
    {
      "id": "accept_flirt",
      "allow": true,
      "condition": "meters.alex.comfort >= 40",
      "acceptance": "She leans closer...",
      "refusal": "She laughs softly but glances away..."
    }
  ],
  "memories": [
    {
      "text": "Alex shared her dream of opening a bookshop-café",
      "characters": ["alex"],
      "day": 1
    },
    {
      "text": "You and Alex clinked mugs in a playful toast",
      "characters": ["player", "alex"],
      "day": 1
    }
  ],
  "meters": {
    "comfort": {"value": 75, "min": 0, "max": 100, ...},
    "interest": {"value": 65, "min": 0, "max": 100, ...}
  },
  "modifiers": [{"id": "relaxed", ...}],
  "attire": "Sweater and jeans",
  "wardrobe_state": {"top": "intact", "bottom": "intact", ...},
  "present": true,
  "location": "cafe_patio"
}
```

#### 3. `GET /session/{id}/story-events`
Returns general memories (empty `characters` array).

**Response**:
```json
{
  "memories": [
    {
      "text": "The café started getting crowded",
      "characters": [],
      "day": 1
    }
  ]
}
```

**TypeScript Interfaces**: All defined in `gameApi.ts` (lines 199-256)

**Tests**: ✅ All 7 API tests passing

---

## ⏳ Remaining Work: Frontend Implementation (Phase 3)

### Component Architecture

```
src/components/
├── CharacterCard.tsx          (NEW - compact card, ~100px height)
├── CharacterNotebook.tsx      (NEW - modal with sidebar + detail)
│   ├── NotebookSidebar.tsx    (NEW - character list navigation)
│   ├── CharacterProfile.tsx   (NEW - full character with memories)
│   └── StoryEventsPage.tsx    (NEW - general memories timeline)
└── CharacterPanel.tsx         (UPDATE - use CharacterCard)
```

### Implementation Steps

#### Step 1: Update gameStore (1-2 hours)

**File**: `frontend/src/stores/gameStore.ts`

Add state for character notebook:
```typescript
interface GameStore {
    // ... existing fields ...

    // Character notebook state
    notebookOpen: boolean;
    selectedNotebookView: 'character' | 'story-events';
    selectedCharacterId: string | null;  // Which character to show

    // Actions
    openNotebook: (characterId?: string) => void;
    closeNotebook: () => void;
    selectCharacter: (characterId: string) => void;
    selectStoryEvents: () => void;
}
```

Implementation:
```typescript
export const useGameStore = create<GameStore>((set, get) => ({
    // ... existing state ...
    notebookOpen: false,
    selectedNotebookView: 'character',
    selectedCharacterId: null,

    openNotebook: (characterId = 'player') => {
        set({
            notebookOpen: true,
            selectedNotebookView: 'character',
            selectedCharacterId: characterId,
        });
    },

    closeNotebook: () => {
        set({ notebookOpen: false });
    },

    selectCharacter: (characterId: string) => {
        set({
            selectedNotebookView: 'character',
            selectedCharacterId: characterId,
        });
    },

    selectStoryEvents: () => {
        set({
            selectedNotebookView: 'story-events',
            selectedCharacterId: null,
        });
    },
}));
```

---

#### Step 2: Create CharacterCard Component (2-3 hours)

**File**: `frontend/src/components/CharacterCard.tsx`

**Purpose**: Compact character display for CharacterPanel

**Design Specs**:
- Height: ~100px (vs. 300px currently)
- Shows: Name + age/gender/pronouns + clothing summary + active modifiers (max 2)
- **NO meters** (meters are dynamic, not shown in compact view)
- Click to open notebook to that character

**Implementation**:
```typescript
import React from 'react';
import { SnapshotCharacter } from '../services/gameApi';
import { useGameStore } from '../stores/gameStore';
import { Shirt, ShirtOff } from 'lucide-react';

interface CharacterCardProps {
    character: SnapshotCharacter & {
        age?: number;
        gender?: string;
        pronouns?: string[] | null;
    };
    onClick?: () => void;
}

export function CharacterCard({ character, onClick }: CharacterCardProps) {
    const openNotebook = useGameStore(state => state.openNotebook);

    const handleClick = () => {
        if (onClick) {
            onClick();
        } else {
            openNotebook(character.id);
        }
    };

    // Summarize clothing
    const clothingSummary = summarizeClothing(character.attire);

    // Get top 2 modifiers
    const topModifiers = character.modifiers?.slice(0, 2) || [];

    return (
        <div
            onClick={handleClick}
            className="p-3 bg-gray-800 border border-gray-700 rounded-lg cursor-pointer transition-all hover:bg-gray-750 hover:border-gray-600 hover:scale-102 active:scale-98"
        >
            {/* Header: Name + presence indicator */}
            <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-gray-100">{character.name}</h3>
                <div className="w-2 h-2 rounded-full bg-green-500" title="Present" />
            </div>

            {/* Basic info */}
            {(character.age || character.gender || character.pronouns) && (
                <p className="text-sm text-gray-400 mb-2">
                    {[
                        character.age,
                        character.gender,
                        character.pronouns?.join('/')
                    ].filter(Boolean).join(' • ')}
                </p>
            )}

            {/* Clothing summary */}
            <div className="flex items-center gap-2 mb-2 text-sm">
                {clothingSummary.icon}
                <span className={clothingSummary.color}>
                    {clothingSummary.text}
                </span>
            </div>

            {/* Active modifiers */}
            {topModifiers.length > 0 && (
                <div className="flex flex-wrap gap-2">
                    {topModifiers.map(mod => (
                        <span
                            key={mod.id}
                            className="px-2 py-1 text-xs rounded-full bg-blue-900/30 text-blue-300"
                        >
                            {mod.id}
                        </span>
                    ))}
                </div>
            )}
        </div>
    );
}

function summarizeClothing(attire: string | Record<string, any> | null | undefined): {
    icon: React.ReactNode;
    text: string;
    color: string;
} {
    if (!attire) {
        return { icon: <Shirt className="w-4 h-4" />, text: 'Unknown', color: 'text-gray-500' };
    }

    if (typeof attire === 'string') {
        const lower = attire.toLowerCase();

        if (lower.includes('naked') || lower.includes('nude')) {
            return { icon: <ShirtOff className="w-4 h-4" />, text: 'Unclothed', color: 'text-red-400' };
        }
        if (lower.includes('underwear only') || lower.includes('lingerie only')) {
            return { icon: <Shirt className="w-4 h-4" />, text: 'Underwear only', color: 'text-orange-400' };
        }
        if (lower.includes('partially') || lower.includes('displaced')) {
            return { icon: <Shirt className="w-4 h-4" />, text: 'Partially dressed', color: 'text-yellow-400' };
        }

        // Fully dressed or specific description
        return { icon: <Shirt className="w-4 h-4" />, text: attire.slice(0, 30) + (attire.length > 30 ? '...' : ''), color: 'text-green-400' };
    }

    // Handle wardrobe_state object
    const states = Object.values(attire);
    const removed = states.filter(s => s === 'removed').length;
    const displaced = states.filter(s => s === 'displaced').length;

    if (removed === states.length) {
        return { icon: <ShirtOff className="w-4 h-4" />, text: 'Unclothed', color: 'text-red-400' };
    }
    if (removed > 0 || displaced > 0) {
        return { icon: <Shirt className="w-4 h-4" />, text: 'Partially dressed', color: 'text-yellow-400' };
    }
    return { icon: <Shirt className="w-4 h-4" />, text: 'Fully dressed', color: 'text-green-400' };
}
```

**Styling Notes**:
- Uses Tailwind CSS (4-space indentation)
- Hover effect: slight scale-up + border color change
- Active effect: slight scale-down
- Height: ~100px (compare to current ~300px)

---

#### Step 3: Update CharacterPanel (1 hour)

**File**: `frontend/src/components/CharacterPanel.tsx`

Replace the current verbose character display with CharacterCard:

```typescript
import { CharacterCard } from './CharacterCard';
import { useGameStore } from '../stores/gameStore';
import { Book } from 'lucide-react';

export function CharacterPanel() {
    const snapshot = useGameStore(state => state.gameState?.snapshot);
    const openNotebook = useGameStore(state => state.openNotebook);

    if (!snapshot?.characters || snapshot.characters.length === 0) {
        return (
            <div className="p-4 bg-gray-800 rounded-lg">
                <p className="text-gray-500 italic">No characters present</p>
            </div>
        );
    }

    return (
        <div className="space-y-3">
            {/* Header with notebook button */}
            <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-200">
                    Characters Present ({snapshot.characters.length})
                </h2>
                <button
                    onClick={() => openNotebook()}
                    className="p-2 rounded-lg hover:bg-gray-700 transition-colors"
                    title="Open Character Notebook"
                >
                    <Book className="w-5 h-5 text-gray-400" />
                </button>
            </div>

            {/* Compact character cards */}
            <div className="space-y-2">
                {snapshot.characters.map(char => (
                    <CharacterCard
                        key={char.id}
                        character={char}
                    />
                ))}
            </div>
        </div>
    );
}
```

---

#### Step 4: Create Character Notebook (4-6 hours)

This is the most complex component. Break it into sub-components:

##### 4.1: NotebookSidebar.tsx

**File**: `frontend/src/components/NotebookSidebar.tsx`

```typescript
import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { gameApi, CharactersListResponse } from '../services/gameApi';
import { useGameStore } from '../stores/gameStore';
import { Search, Book, User } from 'lucide-react';

export function NotebookSidebar() {
    const sessionId = useGameStore(state => state.sessionId);
    const selectedCharacterId = useGameStore(state => state.selectedCharacterId);
    const selectedView = useGameStore(state => state.selectedNotebookView);
    const selectCharacter = useGameStore(state => state.selectCharacter);
    const selectStoryEvents = useGameStore(state => state.selectStoryEvents);

    const [searchQuery, setSearchQuery] = useState('');

    const { data: charactersList } = useQuery<CharactersListResponse>({
        queryKey: ['characters-list', sessionId],
        queryFn: () => sessionId ? gameApi.getCharactersList(sessionId) : Promise.reject(),
        enabled: !!sessionId,
    });

    if (!charactersList) return <div className="w-64 p-4">Loading...</div>;

    // Filter characters by search
    const filteredCharacters = charactersList.characters.filter(char =>
        char.name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    // Group by presence
    const presentChars = filteredCharacters.filter(c => c.present);
    const awayChars = filteredCharacters.filter(c => !c.present);

    return (
        <div className="w-64 border-r border-gray-700 flex flex-col h-full bg-gray-850">
            {/* Search */}
            <div className="p-4 border-b border-gray-700">
                <div className="relative">
                    <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-500" />
                    <input
                        type="text"
                        placeholder="Search characters..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-10 pr-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm focus:outline-none focus:border-blue-500"
                    />
                </div>
            </div>

            {/* Character list */}
            <div className="flex-1 overflow-y-auto p-3 space-y-4">
                {/* Player */}
                <div>
                    <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">
                        You
                    </h3>
                    <button
                        onClick={() => selectCharacter('player')}
                        className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                            selectedView === 'character' && selectedCharacterId === 'player'
                                ? 'bg-blue-600 text-white'
                                : 'hover:bg-gray-800 text-gray-300'
                        }`}
                    >
                        <User className="w-4 h-4" />
                        <span className="font-medium">{charactersList.player.name}</span>
                    </button>
                </div>

                {/* Present characters */}
                {presentChars.length > 0 && (
                    <div>
                        <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">
                            Present ({presentChars.length})
                        </h3>
                        <div className="space-y-1">
                            {presentChars.map(char => (
                                <button
                                    key={char.id}
                                    onClick={() => selectCharacter(char.id)}
                                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                                        selectedView === 'character' && selectedCharacterId === char.id
                                            ? 'bg-blue-600 text-white'
                                            : 'hover:bg-gray-800 text-gray-300'
                                    }`}
                                >
                                    <div className="w-2 h-2 rounded-full bg-green-500" />
                                    <span className="font-medium">{char.name}</span>
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {/* Away characters */}
                {awayChars.length > 0 && (
                    <div>
                        <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">
                            Away ({awayChars.length})
                        </h3>
                        <div className="space-y-1">
                            {awayChars.map(char => (
                                <button
                                    key={char.id}
                                    onClick={() => selectCharacter(char.id)}
                                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                                        selectedView === 'character' && selectedCharacterId === char.id
                                            ? 'bg-blue-600 text-white'
                                            : 'hover:bg-gray-800 text-gray-300'
                                    }`}
                                >
                                    <div className="w-2 h-2 rounded-full bg-gray-600" />
                                    <span className="font-medium">{char.name}</span>
                                </button>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* Story Events button */}
            <div className="p-3 border-t border-gray-700">
                <button
                    onClick={selectStoryEvents}
                    className={`w-full flex items-center gap-3 px-3 py-3 rounded-lg transition-colors ${
                        selectedView === 'story-events'
                            ? 'bg-blue-600 text-white'
                            : 'hover:bg-gray-800 text-gray-300'
                    }`}
                >
                    <Book className="w-5 h-5" />
                    <span className="font-medium">Story Events</span>
                </button>
            </div>
        </div>
    );
}
```

##### 4.2: CharacterProfile.tsx

**File**: `frontend/src/components/CharacterProfile.tsx`

(See full implementation in original proposal - this is ~200 lines with all sections)

Key sections to include:
1. Header (avatar, name, age/gender/pronouns)
2. Personality (core traits, quirks, values)
3. Appearance
4. Dialogue Style
5. Relationship Gates (with lock/unlock indicators)
6. Current State (meters + modifiers)
7. Clothing (attire + wardrobe state)
8. **Shared Memories** ⭐ (last 5, or all for player)

##### 4.3: StoryEventsPage.tsx

**File**: `frontend/src/components/StoryEventsPage.tsx`

```typescript
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { gameApi, CharacterMemory } from '../services/gameApi';
import { useGameStore } from '../stores/gameStore';
import { Book } from 'lucide-react';

export function StoryEventsPage() {
    const sessionId = useGameStore(state => state.sessionId);

    const { data: storyEvents, isLoading } = useQuery({
        queryKey: ['story-events', sessionId],
        queryFn: () => sessionId ? gameApi.getStoryEvents(sessionId) : Promise.reject(),
        enabled: !!sessionId,
    });

    if (isLoading) {
        return (
            <div className="flex-1 p-6">
                <div className="animate-pulse">Loading story events...</div>
            </div>
        );
    }

    if (!storyEvents || storyEvents.memories.length === 0) {
        return (
            <div className="flex-1 p-6">
                <div className="flex items-center gap-3 mb-6">
                    <Book className="w-8 h-8 text-gray-400" />
                    <h2 className="text-2xl font-bold">Story Events</h2>
                </div>
                <p className="text-gray-500 italic">No story events recorded yet.</p>
            </div>
        );
    }

    // Group memories by day
    const memoriesByDay = storyEvents.memories.reduce((acc, memory) => {
        const day = memory.day;
        if (!acc[day]) acc[day] = [];
        acc[day].push(memory);
        return acc;
    }, {} as Record<number, CharacterMemory[]>);

    const days = Object.keys(memoriesByDay).map(Number).sort((a, b) => a - b);

    return (
        <div className="flex-1 p-6 overflow-y-auto">
            <div className="flex items-center gap-3 mb-6">
                <Book className="w-8 h-8 text-gray-400" />
                <h2 className="text-2xl font-bold">Story Events</h2>
            </div>

            <p className="text-gray-400 mb-6">
                General events and atmosphere that shaped your journey
            </p>

            <div className="space-y-6">
                {days.map(day => (
                    <div key={day} className="border-l-2 border-blue-500 pl-4">
                        <h3 className="text-sm font-semibold text-blue-400 mb-3">
                            Day {day}
                        </h3>
                        <div className="space-y-2">
                            {memoriesByDay[day].map((memory, idx) => (
                                <div key={idx} className="flex items-start gap-2">
                                    <span className="text-gray-500 mt-1">•</span>
                                    <p className="text-gray-300">{memory.text}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
```

##### 4.4: CharacterNotebook.tsx (Main Component)

**File**: `frontend/src/components/CharacterNotebook.tsx`

```typescript
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { gameApi } from '../services/gameApi';
import { useGameStore } from '../stores/gameStore';
import { X } from 'lucide-react';
import { NotebookSidebar } from './NotebookSidebar';
import { CharacterProfile } from './CharacterProfile';
import { StoryEventsPage } from './StoryEventsPage';

export function CharacterNotebook() {
    const notebookOpen = useGameStore(state => state.notebookOpen);
    const closeNotebook = useGameStore(state => state.closeNotebook);
    const selectedView = useGameStore(state => state.selectedNotebookView);
    const selectedCharacterId = useGameStore(state => state.selectedCharacterId);
    const sessionId = useGameStore(state => state.sessionId);

    const { data: characterData, isLoading: charLoading } = useQuery({
        queryKey: ['character', sessionId, selectedCharacterId],
        queryFn: () => {
            if (!sessionId || !selectedCharacterId) return Promise.reject();
            return gameApi.getCharacter(sessionId, selectedCharacterId);
        },
        enabled: !!sessionId && !!selectedCharacterId && selectedView === 'character',
    });

    if (!notebookOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <div className="w-[90vw] max-w-6xl h-[80vh] bg-gray-900 rounded-lg shadow-2xl flex flex-col overflow-hidden">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
                    <h1 className="text-2xl font-bold">Character Notebook</h1>
                    <button
                        onClick={closeNotebook}
                        className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
                    >
                        <X className="w-6 h-6" />
                    </button>
                </div>

                {/* Content */}
                <div className="flex flex-1 overflow-hidden">
                    <NotebookSidebar />

                    <div className="flex-1 overflow-y-auto">
                        {selectedView === 'character' && (
                            charLoading ? (
                                <div className="flex items-center justify-center h-full">
                                    <div className="animate-pulse">Loading character...</div>
                                </div>
                            ) : characterData ? (
                                <CharacterProfile character={characterData} />
                            ) : (
                                <div className="flex items-center justify-center h-full">
                                    <p className="text-gray-500">Select a character to view their profile</p>
                                </div>
                            )
                        )}

                        {selectedView === 'story-events' && (
                            <StoryEventsPage />
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
```

---

#### Step 5: Integration & Testing (2-3 hours)

1. **Add CharacterNotebook to GameInterface**:
   ```typescript
   // In GameInterface.tsx
   import { CharacterNotebook } from './CharacterNotebook';

   // Add inside return statement
   <CharacterNotebook />
   ```

2. **Add keyboard shortcut** (optional):
   ```typescript
   // In useKeyboardShortcuts hook or GameInterface
   useEffect(() => {
       const handleKeyPress = (e: KeyboardEvent) => {
           if (e.key === 'c' && !e.ctrlKey && !e.metaKey) {
               openNotebook();
           }
       };
       window.addEventListener('keydown', handleKeyPress);
       return () => window.removeEventListener('keydown', handleKeyPress);
   }, [openNotebook]);
   ```

3. **Test checklist**:
   - [ ] Compact character cards render correctly
   - [ ] Click card opens notebook to that character
   - [ ] Notebook sidebar shows all characters
   - [ ] Sidebar grouping (present/away) works
   - [ ] Search filters characters
   - [ ] Character profile displays all sections
   - [ ] Memories are filtered correctly (player gets all, NPCs get tagged only)
   - [ ] Gates show lock/unlock status
   - [ ] Story Events page shows general memories
   - [ ] ESC key closes notebook
   - [ ] Mobile responsive (sidebar collapses to drawer)

4. **Run frontend tests**:
   ```bash
   cd frontend
   npm test
   npm run build  # Verify TypeScript compilation
   ```

---

## 🎨 Design Specifications

### Colors & Style

- **Background**: `bg-gray-900` (main), `bg-gray-800` (panels), `bg-gray-850` (sidebar)
- **Borders**: `border-gray-700`
- **Text**: `text-gray-100` (headers), `text-gray-300` (body), `text-gray-400` (secondary), `text-gray-500` (muted)
- **Accents**: `bg-blue-600` (selected), `text-blue-400` (links)
- **Status Colors**:
  - Green: Present/unlocked (`bg-green-500`, `text-green-400`)
  - Red: Unclothed/locked (`text-red-400`)
  - Orange: Partially dressed (`text-orange-400`)
  - Yellow: Displaced (`text-yellow-400`)

### Spacing & Layout

- **4-space indentation** for all code
- **Padding**: `p-3` (compact), `p-4` (standard), `p-6` (spacious)
- **Gaps**: `gap-2` (tight), `gap-3` (standard), `gap-4` (loose)
- **Rounded corners**: `rounded-lg` (standard), `rounded-full` (badges)

### Animations

```css
/* Hover scale */
hover:scale-102  /* 2% scale up */
active:scale-98  /* 2% scale down */

/* Fade in */
animation: fade-in 200ms ease-out;

/* Slide in */
animation: slide-in-right 250ms ease-out;
```

---

## 🧪 Testing Strategy

### Backend Tests (DONE ✅)

All passing:
- `pytest backend/tests/` → 199/199 passing
- `pytest backend/tests/test_api_game.py` → 7/7 passing

### Frontend Tests (TODO)

Create tests for:
1. `CharacterCard.test.tsx` - rendering, onClick, clothing summary
2. `NotebookSidebar.test.tsx` - search, filtering, selection
3. `CharacterProfile.test.tsx` - all sections render, gates display
4. `StoryEventsPage.test.tsx` - grouping by day, empty state
5. `gameStore.test.ts` - notebook state management

Run with:
```bash
cd frontend
npm test
```

---

## 📊 Success Metrics

### Performance

- **Character card render**: < 16ms (60fps)
- **Notebook modal open**: < 200ms
- **Search filter**: < 50ms for 100 characters
- **Memory filtering**: < 10ms per character

### UX

- **Space savings**: 60% reduction in CharacterPanel height
- **Information density**: 3-4 characters visible before scroll (vs. 1-2 currently)
- **Click depth**: 1 click to full character profile (vs. scrolling through verbose display)

### Quality

- **TypeScript**: No compilation errors
- **Tests**: All passing
- **Responsive**: Works on mobile (sidebar collapses to drawer)
- **Accessible**: Keyboard navigation, screen reader labels

---

## 🚀 Future Enhancements

These are **not required** for the initial implementation but could be added later:

1. **Meter history sparklines** - Show meter trends over time
2. **Character comparison** - Side-by-side comparison of 2 characters
3. **Favorites system** - Star favorite characters for quick access
4. **Memory search** - Full-text search within memories
5. **Discovery system** - Hide undiscovered characters (requires backend gate system)
6. **Export character data** - Download character sheet as JSON/PDF
7. **Relationship graph** - Visual network of character relationships
8. **Memory annotations** - Add player notes to memories

---

## 📝 Notes for Implementation

### Common Pitfalls to Avoid

1. **Don't forget backward compatibility**: Handle both legacy string and new dict memory formats
2. **Validate character IDs**: Ensure character exists before fetching
3. **Handle loading states**: Show spinners while fetching character data
4. **Error boundaries**: Wrap CharacterNotebook in error boundary
5. **Z-index conflicts**: Modal should be z-50 or higher
6. **Mobile tap targets**: Min 44x44px for touch
7. **Null checks**: Always check if snapshot/data exists before rendering

### React Query Configuration

```typescript
// In main.tsx or App.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            staleTime: 30000,  // 30 seconds
            refetchOnWindowFocus: false,
        },
    },
});

// Wrap app with provider
<QueryClientProvider client={queryClient}>
    <App />
</QueryClientProvider>
```

### Cache Invalidation

When game state updates, invalidate character queries:

```typescript
// In gameStore after process_action
queryClient.invalidateQueries({ queryKey: ['characters-list'] });
queryClient.invalidateQueries({ queryKey: ['character'] });
```

---

## 🔗 Related Files

### Backend
- `backend/app/core/state_manager.py:90` - Memory log structure
- `backend/app/engine/prompt_builder.py:597-615` - Checker prompt contract
- `backend/app/engine/turn_manager.py:135-181, 466-512` - Memory processing
- `backend/app/api/game.py:524-676` - Character API endpoints

### Frontend (Existing)
- `frontend/src/services/gameApi.ts` - API client + TypeScript interfaces
- `frontend/src/stores/gameStore.ts` - Global state management
- `frontend/src/components/GameInterface.tsx` - Main game UI
- `frontend/src/components/CharacterPanel.tsx` - Current character display (to be updated)

### Frontend (To Be Created)
- `frontend/src/components/CharacterCard.tsx`
- `frontend/src/components/CharacterNotebook.tsx`
- `frontend/src/components/NotebookSidebar.tsx`
- `frontend/src/components/CharacterProfile.tsx`
- `frontend/src/components/StoryEventsPage.tsx`

---

## 📞 Questions or Issues?

If you encounter issues during implementation:

1. **Backend memory format confusion**: Check `state.memory_log` structure - should be list of dicts with `text`, `characters`, `day`
2. **API 404 errors**: Verify session ID is valid and character ID exists
3. **TypeScript errors**: Ensure you've imported types from `gameApi.ts`
4. **React Query not fetching**: Check `enabled` flag and `queryKey` uniqueness
5. **Modal not appearing**: Check z-index and ensure `notebookOpen` state is true

**Test endpoints manually**:
```bash
# Get characters list
curl http://localhost:8000/api/game/session/{SESSION_ID}/characters

# Get character detail
curl http://localhost:8000/api/game/session/{SESSION_ID}/character/alex

# Get story events
curl http://localhost:8000/api/game/session/{SESSION_ID}/story-events
```

---

## ✅ Completion Checklist

Before considering this feature complete:

### Backend
- [x] Memory structure supports character tags
- [x] Checker prompt requests character tags
- [x] Turn manager validates and processes tagged memories
- [x] All backend tests passing (199/199)
- [x] Character API endpoints implemented
- [x] API endpoints tested (7/7 passing)

### Frontend
- [ ] TypeScript interfaces defined (✅ DONE in gameApi.ts)
- [ ] API client methods added (✅ DONE in gameApi.ts)
- [ ] gameStore updated with notebook state
- [ ] CharacterCard component created
- [ ] CharacterPanel updated
- [ ] CharacterNotebook modal created
- [ ] NotebookSidebar component created
- [ ] CharacterProfile component created
- [ ] StoryEventsPage component created
- [ ] Components integrated into GameInterface
- [ ] Frontend tests passing
- [ ] TypeScript builds without errors
- [ ] Visual QA on desktop
- [ ] Visual QA on mobile
- [ ] Performance benchmarks met

---

## 🎯 Estimated Time Remaining

- **gameStore updates**: 1-2 hours
- **CharacterCard component**: 2-3 hours
- **CharacterPanel update**: 1 hour
- **CharacterNotebook + sub-components**: 4-6 hours
- **Testing & polish**: 2-3 hours

**Total**: ~10-15 hours of focused development

---

**Good luck with the implementation! The backend is solid and ready to support the new UI. 🚀**
