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
}

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

export interface SnapshotLocation {
    id: string | null;
    name: string;
    zone: string | null;
    privacy: string | null;
    summary?: string | null;
    description?: string | null;
    has_shop: boolean;
    exits: SnapshotExit[];
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
    inventory_details: Record<string, Item>;
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

    async move(sessionId: string, payload: MovementRequest): Promise<DeterministicActionResponse> {
        const response = await axios.post(`${API_BASE}/game/move/${sessionId}`, payload);
        return response.data;
    }

    async purchase(sessionId: string, itemId: string, count = 1, price?: number, sellerId?: string): Promise<DeterministicActionResponse> {
        const response = await axios.post(`${API_BASE}/game/shop/${sessionId}/purchase`, {
            buyer_id: 'player',
            seller_id: sellerId,
            item_id: itemId,
            count,
            price,
        });
        return response.data;
    }

    async sell(sessionId: string, itemId: string, count = 1, price?: number, buyerId?: string): Promise<DeterministicActionResponse> {
        const response = await axios.post(`${API_BASE}/game/shop/${sessionId}/sell`, {
            seller_id: 'player',
            buyer_id: buyerId,
            item_id: itemId,
            count,
            price,
        });
        return response.data;
    }

    async takeItem(sessionId: string, itemId: string, count = 1, ownerId = 'player'): Promise<DeterministicActionResponse> {
        const response = await axios.post(`${API_BASE}/game/inventory/${sessionId}/take`, {
            owner_id: ownerId,
            item_id: itemId,
            count,
        });
        return response.data;
    }

    async dropItem(sessionId: string, itemId: string, count = 1, ownerId = 'player'): Promise<DeterministicActionResponse> {
        const response = await axios.post(`${API_BASE}/game/inventory/${sessionId}/drop`, {
            owner_id: ownerId,
            item_id: itemId,
            count,
        });
        return response.data;
    }

    async giveItem(sessionId: string, itemId: string, targetId: string, count = 1, sourceId = 'player'): Promise<DeterministicActionResponse> {
        const response = await axios.post(`${API_BASE}/game/inventory/${sessionId}/give`, {
            source_id: sourceId,
            target_id: targetId,
            item_id: itemId,
            count,
        });
        return response.data;
    }

    async getState(sessionId: string): Promise<DebugStateResponse> {
        const response = await axios.get(`${API_BASE}/game/session/${sessionId}/state`);
        return response.data;
    }

    async getLogs(sessionId: string, since: number): Promise<LogResponse> {
        const response = await axios.get(`${API_BASE}/debug/logs/${sessionId}?since=${since}`);
        return response.data;
    }
}

export const gameApi = new GameAPI();
