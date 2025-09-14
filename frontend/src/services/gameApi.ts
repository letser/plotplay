import axios from 'axios';

const API_BASE = '/api';

// Add request interceptor for debugging
axios.interceptors.request.use(request => {
    console.log('Making request to:', request.url);
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
    nsfw_level: string;
}

export interface GameChoice {
    id: string;
    text: string;
    type: string;
}

export interface GameState {
    day: number;
    time: string;
    location: string;
    present_characters: string[];
    meters: Record<string, Record<string, number>>;
    inventory: Record<string, number>;
}

export interface GameResponse {
    session_id: string;
    narrative: string;
    choices: GameChoice[];
    state_summary: GameState;
    appearances?: Record<string, any>;
}

class GameAPI {
    async listGames(): Promise<GameInfo[]> {
        const response = await axios.get(`${API_BASE}/game/list`);
        return response.data.games;
    }

    async startGame(gameId: string): Promise<GameResponse> {
        const response = await axios.post(`${API_BASE}/game/start/${gameId}`);
        return response.data;
    }

    async sendAction(sessionId: string, actionType: string, actionText: string, target?: string | null, choiceId?: string | null): Promise<GameResponse> {
        const response = await axios.post(`${API_BASE}/game/action/${sessionId}`, {
            action_type: actionType,
            action_text: actionText,
            target: target,
            choice_id: choiceId,
        });
        return response.data;
    }

    async getState(sessionId: string): Promise<any> {
        const response = await axios.get(`${API_BASE}/game/session/${sessionId}/state`);
        return response.data;
    }
}

export const gameApi = new GameAPI();