import axios from 'axios';

const API_BASE = '/api';

export interface GameInfo {
    id: string;
    title: string;
    author: string;
    content_rating: string;
    version: string;
}

export interface GameChoice {
    id: string;
    text: string;
    type: string;
    disabled?: boolean;
    skip_ai?: boolean;
}

export interface Meter {
    value: number;
    min: number;
    max: number;
    icon: string | null;
    visible: boolean;
}

export interface Flag {
    value: string | number | boolean;
    label: string;
}

export interface Modifier {
    id: string;
    description?: string | null;
    appearance?: Record<string, string | undefined>;
    [key: string]: unknown;
}

export interface Item {
    id: string;
    name: string;
    description: string | null;
    icon: string | null;
    stackable: boolean;
    droppable?: boolean;
    consumable?: boolean;
    on_use?: unknown[] | null;
    effects_on_use?: unknown[] | null;
    type?: 'item' | 'clothing' | 'outfit' | 'unknown';
}

export type ClothingStateValue = 'intact' | 'opened' | 'displaced' | 'removed';

export interface CharacterDetails {
    name: string;
    pronouns: string[] | null;
    wearing: string | null;
}

export interface PlayerDetails {
    name: string;
    pronouns: string[] | null;
    wearing: string | null;
}

export interface SnapshotExit {
    direction: string | null;
    to: string | null;
    name: string;
    discovered: boolean;
    available: boolean;
    locked: boolean;
    description: string | null;
}

export interface ZoneConnectionEntryLocation {
    id: string;
    name: string;
}

export interface ZoneConnection {
    zone_id: string;
    zone_name: string;
    distance: number;
    available_methods: string[];
    entry_locations: ZoneConnectionEntryLocation[];
    locked: boolean;
    available: boolean;
}

export interface SnapshotLocation {
    id: string | null;
    name: string;
    zone: string | null;
    privacy: string | null;
    summary?: string | null;
    description?: string | null;
    has_shop: boolean;
    exits: SnapshotExit[];
    zone_connections: ZoneConnection[];
}

export interface SnapshotTime {
    day: number | null;
    slot: string | null;
    time_hhmm?: string | null;
    weekday?: string | null;
    mode?: 'clock' | 'hybrid' | 'slots';
}

export interface SnapshotCharacter {
    id: string;
    name?: string;
    pronouns?: string[] | null;
    attire?: string | Record<string, string | null> | null;
    meters: Record<string, Meter>;
    modifiers: Modifier[];
    wardrobe_state?: Record<string, string | Record<string, string | null> | null>;
}

export interface StateSnapshot {
    time: SnapshotTime;
    location: SnapshotLocation;
    player: SnapshotCharacter & {
        inventory: Record<string, number>;
    };
    characters: SnapshotCharacter[];
}

export interface EconomyInfo {
    currency: string;
    symbol: string;
    player_money: number | null;
    max_money: number | null;
}

export interface GameState {
    day: number;
    time: string | null;
    time_hhmm?: string | null;
    location: string;
    location_id: string | null;
    zone: string | null;
    present_characters: string[];
    character_details: Record<string, CharacterDetails>;
    player_details: PlayerDetails;
    meters: Record<string, Record<string, Meter>>;
    inventory: Record<string, number>;
    location_inventory?: Record<string, number>;
    inventory_details: Record<string, Item>;
    player_outfits?: string[];
    player_current_outfit?: string | null;
    player_equipped_clothing?: string[];
    location_inventory_details?: Record<string, Item>;
    flags: Record<string, Flag>;
    modifiers: Record<string, Modifier[]>;
    turn_count?: number;
    snapshot?: StateSnapshot;
    economy?: EconomyInfo;
}

export interface GameResponse {
    session_id: string;
    narrative: string;
    choices: GameChoice[];
    state_summary: GameState;
    time_advanced: boolean;
    location_changed: boolean;
    action_summary?: string | null;
}

export interface DeterministicActionResponse {
    session_id: string;
    success: boolean;
    message: string;
    state_summary: GameState;
    action_summary?: string | null;
    details?: Record<string, unknown>;
}

export interface MovementRequest {
    destination_id?: string | null;
    zone_id?: string | null;
    direction?: string | null;
    method?: string | null;  // Travel method for zone travel
    entry_location_id?: string | null;  // Specific entry location for zone travel
    companions?: string[];
}

export interface InventoryTransferRequest {
    item_id: string;
    count?: number;
    owner_id?: string;
    target_id?: string;
    seller_id?: string;
    buyer_id?: string;
    price?: number;
}

export interface LogResponse {
    content: string;
    size: number;
}

export interface CharacterMemory {
    text: string;
    characters: string[];
    day: number;
}

export interface CharacterGate {
    id: string;
    allow: boolean;
    condition: string | null;
    acceptance?: string | null;
    refusal?: string | null;
}

export interface CharacterPersonality {
    core_traits?: string;
    quirks?: string;
    values?: string;
    fears?: string;
}

export interface OutfitData {
    id: string;
    name: string;
    description?: string | null;
    items: string[];  // All item IDs in outfit
    owned_items: string[];  // Items character has
    missing_items: string[];  // Items character doesn't have
    grant_items: boolean;
}

export interface WardrobeState {
    current_outfit: string | null;
    layers: Record<string, string>;  // slot -> state (intact, displaced, removed, opened)
    slot_to_item: Record<string, string>;  // slot -> item_id
}

export interface CharacterFull {
    id: string;
    name: string;
    age: number;
    gender: string;
    pronouns: string[] | null;
    personality?: CharacterPersonality | null;
    appearance?: string | null;
    dialogue_style?: string | null;
    gates: CharacterGate[];
    memories: CharacterMemory[];
    meters: Record<string, Meter>;
    modifiers: Modifier[];
    attire: string;
    wardrobe_state?: WardrobeState | null;
    inventory: Record<string, number>;
    wardrobe: Record<string, number>;  // Individual clothing items
    outfits: OutfitData[];  // Unlocked outfits with ownership status
    item_details: Record<string, Item>;
    present: boolean;
    location?: string | null;
}

export interface CharacterListItem {
    id: string;
    name: string;
    present: boolean;
    location?: string | null;
}

export interface CharactersListResponse {
    player: {
        id: string;
        name: string;
    };
    characters: CharacterListItem[];
}

export interface StoryEventsResponse {
    memories: CharacterMemory[];
}

export interface DebugStateResponse {
    state: Record<string, any>;
    history: string[];
}

class GameAPI {
    async listGames(): Promise<GameInfo[]> {
        const response = await axios.get(`${API_BASE}/game/list`);
        return response.data.games;
    }

    async startGame(gameId: string): Promise<GameResponse> {
        const response = await axios.post(`${API_BASE}/game/start`, { game_id: gameId });
        return response.data;
    }

    async *startGameStream(gameId: string): AsyncGenerator<any, void, unknown> {
        const response = await fetch(`${API_BASE}/game/start/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ game_id: gameId }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body?.getReader();
        if (!reader) {
            throw new Error('No response body');
        }

        const decoder = new TextDecoder();
        let buffer = '';

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6).trim();
                        if (data === '[DONE]') return;

                        try {
                            const parsed = JSON.parse(data);
                            yield parsed;
                        } catch (e) {
                            console.error('Failed to parse SSE data:', data, e);
                        }
                    }
                }
            }
        } finally {
            reader.releaseLock();
        }
    }

    async sendAction(
        sessionId: string,
        actionType: string,
        actionText: string | null,
        target?: string | null,
        choiceId?: string | null,
        itemId?: string | null,
        options?: { skipAi?: boolean }
    ): Promise<GameResponse> {
        const response = await axios.post(`${API_BASE}/game/action/${sessionId}`, {
            action_type: actionType,
            action_text: actionText,
            target,
            choice_id: choiceId,
            item_id: itemId,
            skip_ai: options?.skipAi ?? false,
        });
        return response.data;
    }

    async *sendActionStream(
        sessionId: string,
        actionType: string,
        actionText: string | null,
        target?: string | null,
        choiceId?: string | null,
        itemId?: string | null,
        options?: { skipAi?: boolean }
    ): AsyncGenerator<any, void, unknown> {
        const response = await fetch(`${API_BASE}/game/action/${sessionId}/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                action_type: actionType,
                action_text: actionText,
                target,
                choice_id: choiceId,
                item_id: itemId,
                skip_ai: options?.skipAi ?? false,
            }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body?.getReader();
        if (!reader) {
            throw new Error('No response body');
        }

        const decoder = new TextDecoder();
        let buffer = '';

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');

                // Keep the last incomplete line in the buffer
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6).trim();

                        if (data === '[DONE]') {
                            return;
                        }

                        try {
                            const parsed = JSON.parse(data);
                            yield parsed;
                        } catch (e) {
                            console.error('Failed to parse SSE data:', data, e);
                        }
                    }
                }
            }
        } finally {
            reader.releaseLock();
        }
    }

    // Movement actions using unified endpoint
    async move(sessionId: string, payload: MovementRequest): Promise<GameResponse> {
        let action_type: 'move' | 'goto' | 'travel';
        let direction: string | undefined;
        let location: string | undefined;

        if (payload.direction) {
            action_type = 'move';
            direction = payload.direction;
        } else if (payload.zone_id) {
            action_type = 'travel';
            location = payload.entry_location_id || payload.zone_id;
        } else if (payload.destination_id) {
            action_type = 'goto';
            location = payload.destination_id;
        } else {
            throw new Error('Invalid movement payload');
        }

        const response = await axios.post(`${API_BASE}/game/action/${sessionId}`, {
            action_type,
            direction,
            location,
            with_characters: payload.companions,
            skip_ai: true
        });
        return response.data;
    }

    // Shopping actions using unified endpoint
    async purchase(sessionId: string, itemId: string, count = 1, price?: number, sellerId?: string): Promise<GameResponse> {
        const response = await axios.post(`${API_BASE}/game/action/${sessionId}`, {
            action_type: 'shop_buy',
            item_id: itemId,
            target: sellerId,
            action_text: `Buy ${count}x ${itemId}${price ? ` for ${price}` : ''}`,
            skip_ai: true
        });
        return response.data;
    }

    async sell(sessionId: string, itemId: string, count = 1, price?: number, buyerId?: string): Promise<GameResponse> {
        const response = await axios.post(`${API_BASE}/game/action/${sessionId}`, {
            action_type: 'shop_sell',
            item_id: itemId,
            target: buyerId,
            action_text: `Sell ${count}x ${itemId}${price ? ` for ${price}` : ''}`,
            skip_ai: true
        });
        return response.data;
    }

    // Inventory actions using unified endpoint
    async takeItem(sessionId: string, itemId: string, count = 1, _ownerId = 'player'): Promise<GameResponse> {
        const response = await axios.post(`${API_BASE}/game/action/${sessionId}`, {
            action_type: 'inventory',
            item_id: itemId,
            action_text: `Take ${count}x ${itemId}`,
            skip_ai: true
        });
        return response.data;
    }

    async dropItem(sessionId: string, itemId: string, count = 1, _ownerId = 'player'): Promise<GameResponse> {
        const response = await axios.post(`${API_BASE}/game/action/${sessionId}`, {
            action_type: 'inventory',
            item_id: itemId,
            action_text: `Drop ${count}x ${itemId}`,
            skip_ai: true
        });
        return response.data;
    }

    async giveItem(sessionId: string, itemId: string, targetId: string, count = 1, _sourceId = 'player'): Promise<GameResponse> {
        const response = await axios.post(`${API_BASE}/game/action/${sessionId}`, {
            action_type: 'give',
            item_id: itemId,
            target: targetId,
            action_text: `Give ${count}x ${itemId} to ${targetId}`,
            skip_ai: true
        });
        return response.data;
    }

    // Clothing actions using unified endpoint
    async putOnClothing(sessionId: string, clothingId: string, characterId = 'player', state?: ClothingStateValue): Promise<GameResponse> {
        const response = await axios.post(`${API_BASE}/game/action/${sessionId}`, {
            action_type: 'clothing',
            item_id: clothingId,
            target: characterId,
            action_text: `Put on ${clothingId}${state ? ` (${state})` : ''}`,
            skip_ai: true
        });
        return response.data;
    }

    async takeOffClothing(sessionId: string, clothingId: string, characterId = 'player'): Promise<GameResponse> {
        const response = await axios.post(`${API_BASE}/game/action/${sessionId}`, {
            action_type: 'clothing',
            item_id: clothingId,
            target: characterId,
            action_text: `Take off ${clothingId}`,
            skip_ai: true
        });
        return response.data;
    }

    async setClothingState(sessionId: string, clothingId: string, state: ClothingStateValue, characterId = 'player'): Promise<GameResponse> {
        const response = await axios.post(`${API_BASE}/game/action/${sessionId}`, {
            action_type: 'clothing',
            item_id: clothingId,
            target: characterId,
            action_text: `Set ${clothingId} to ${state}`,
            skip_ai: true
        });
        return response.data;
    }

    async putOnOutfit(sessionId: string, outfitId: string, characterId = 'player'): Promise<GameResponse> {
        const response = await axios.post(`${API_BASE}/game/action/${sessionId}`, {
            action_type: 'clothing',
            item_id: outfitId,
            target: characterId,
            action_text: `Put on outfit ${outfitId}`,
            skip_ai: true
        });
        return response.data;
    }

    async takeOffOutfit(sessionId: string, outfitId: string, characterId = 'player'): Promise<GameResponse> {
        const response = await axios.post(`${API_BASE}/game/action/${sessionId}`, {
            action_type: 'clothing',
            item_id: outfitId,
            target: characterId,
            action_text: `Take off outfit ${outfitId}`,
            skip_ai: true
        });
        return response.data;
    }

    // Debug endpoint - keeping for now but may be removed later
    async getState(sessionId: string): Promise<DebugStateResponse> {
        const response = await axios.get(`${API_BASE}/game/session/${sessionId}/state`);
        return response.data;
    }

    async getLogs(sessionId: string, since: number): Promise<LogResponse> {
        const response = await axios.get(`${API_BASE}/debug/logs/${sessionId}?since=${since}`);
        return response.data;
    }

    // Character API methods
    async getCharactersList(sessionId: string): Promise<CharactersListResponse> {
        const response = await axios.get(`${API_BASE}/game/session/${sessionId}/characters`);
        return response.data;
    }

    async getCharacter(sessionId: string, characterId: string): Promise<CharacterFull> {
        const response = await axios.get(`${API_BASE}/game/session/${sessionId}/character/${characterId}`);
        return response.data;
    }

    async getStoryEvents(sessionId: string): Promise<StoryEventsResponse> {
        const response = await axios.get(`${API_BASE}/game/session/${sessionId}/story-events`);
        return response.data;
    }
}

export const gameApi = new GameAPI();
