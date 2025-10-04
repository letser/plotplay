// frontend/src/services/gameApi.ts
import axios from 'axios';

const API_BASE = '/api';

// Add request interceptor for debugging
axios.interceptors.request.use(request => {
    console.log('Making request to:', request.url, 'with data:', request.data);
    return request;
});

// Add a response interceptor for debugging
axios.interceptors.response.use(
    response => {
        console.log('Response received:', response);
        return response;
    },
    error => {
        console.error('Request failed:', error.response?.status, error.response?.data);
        return Promise.reject(error);
    }
);

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
    description: string | null;
    appearance?: {
        cheeks?: string;
        eyes?: string;
        posture?: string;
    }
}

export interface Item {
    id: string;
    name: string;
    description: string | null;
    icon: string | null;
    stackable: boolean;
    effects_on_use: any[] | null;
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

export interface GameState {
    day: number;
    time: string;
    time_hhmm?: string;
    location: string;
    present_characters: string[];
    character_details: Record<string, CharacterDetails>;
    player_details: PlayerDetails;
    meters: Record<string, Record<string, Meter>>;
    inventory: Record<string, number>;
    inventory_details: Record<string, Item>; // <-- The missing field
    flags: Record<string, Flag>;
    modifiers: Record<string, Modifier[]>;
}

export interface GameResponse {
    session_id: string;
    narrative: string;
    choices: GameChoice[];
    state_summary: GameState;
    time_advanced: boolean;
    location_changed: boolean;
}

export interface LogResponse {
    content: string;
    size: number;
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

    async sendAction(
        sessionId: string,
        actionType: string,
        actionText: string | null,
        target?: string | null,
        choiceId?: string | null,
        itemId?: string | null
    ): Promise<GameResponse> {
        const response = await axios.post(`${API_BASE}/game/action/${sessionId}`, {
            action_type: actionType,
            action_text: actionText,
            target: target,
            choice_id: choiceId,
            item_id: itemId,
        });
        return response.data;
    }

    async getState(sessionId: string): Promise<any> {
        const response = await axios.get(`${API_BASE}/game/session/${sessionId}/state`);
        return response.data;
    }

    async getLogs(sessionId: string, since: number): Promise<LogResponse> {
        const response = await axios.get(`${API_BASE}/debug/logs/${sessionId}?since=${since}`);
        return response.data;
    }
}

export const gameApi = new GameAPI();