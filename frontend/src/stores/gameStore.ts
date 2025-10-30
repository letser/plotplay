import { create } from 'zustand';
import {
    gameApi,
    GameChoice,
    GameInfo,
    GameState,
    DeterministicActionResponse,
    MovementRequest,
    ClothingStateValue,
} from '../services/gameApi';
import { saveSession, clearSession, loadSession, hasStoredSession } from '../utils/storage';
import { useToast } from '../hooks/useToast';
import { queryClient } from '../lib/queryClient';

const DEFAULT_SUMMARY = 'Action resolved.';

export type TurnOrigin = 'ai' | 'deterministic';

export interface TurnLogEntry {
    id: number;
    summary: string;
    narrative: string;
    origin: TurnOrigin;
    timestamp: string;
}

interface GameStore {
    games: GameInfo[];
    currentGame: GameInfo | null;
    sessionId: string | null;
    turnLog: TurnLogEntry[];
    choices: GameChoice[];
    gameState: GameState | null;
    loading: boolean;
    error: string | null;
    turnCounter: number;
    checkerStatus: string | null;
    lastAction: {
        actionType: string;
        actionText: string | null;
        target?: string | null;
        choiceId?: string | null;
        itemId?: string | null;
        options?: { skipAi?: boolean };
    } | null;

    // Character notebook state
    notebookOpen: boolean;
    selectedNotebookView: 'character' | 'story-events';
    selectedCharacterId: string | null;

    loadGames: () => Promise<void>;
    startGame: (gameId: string) => Promise<void>;
    sendAction: (
        actionType: string,
        actionText: string | null,
        target?: string | null,
        choiceId?: string | null,
        itemId?: string | null,
        options?: { skipAi?: boolean }
    ) => Promise<void>;
    retryLastAction: () => Promise<void>;
    performMovement: (choiceId: string) => Promise<void>;
    performZoneTravel: (zoneId: string, method: string | null, entryLocationId: string | null) => Promise<void>;
    purchaseItem: (itemId: string, count?: number, price?: number, sellerId?: string) => Promise<void>;
    sellItem: (itemId: string, count?: number, price?: number, buyerId?: string) => Promise<void>;
    takeItem: (itemId: string, count?: number, ownerId?: string) => Promise<void>;
    dropItem: (itemId: string, count?: number, ownerId?: string) => Promise<void>;
    giveItem: (itemId: string, targetId: string, count?: number, sourceId?: string) => Promise<void>;
    putOnClothing: (clothingId: string, characterId?: string, state?: ClothingStateValue) => Promise<void>;
    takeOffClothing: (clothingId: string, characterId?: string) => Promise<void>;
    setClothingState: (clothingId: string, state: ClothingStateValue, characterId?: string) => Promise<void>;
    putOnOutfit: (outfitId: string, characterId?: string) => Promise<void>;
    takeOffOutfit: (outfitId: string, characterId?: string) => Promise<void>;
    clearTurnLog: () => void;
    resetGame: () => void;
    hasStoredSession: () => boolean;
    restoreSession: () => Promise<void>;

    // Character notebook actions
    openNotebook: (characterId?: string) => void;
    closeNotebook: () => void;
    selectCharacter: (characterId: string) => void;
    selectStoryEvents: () => void;
}

const buildTurnEntry = (
    turnId: number,
    origin: TurnOrigin,
    summary?: string | null,
    narrative?: string | null
): TurnLogEntry => {
    const safeSummary = summary && summary.trim().length > 0 ? summary.trim() : DEFAULT_SUMMARY;
    const safeNarrative =
        narrative && narrative.trim().length > 0 ? narrative : safeSummary;
    return {
        id: turnId,
        summary: safeSummary,
        narrative: safeNarrative,
        origin,
        timestamp: new Date().toISOString(),
    };
};

const extractChoicesFromDetails = (details?: Record<string, unknown>): GameChoice[] | undefined => {
    if (!details) return undefined;
    if (Array.isArray(details.choices)) {
        return details.choices as GameChoice[];
    }
    return undefined;
};

export const useGameStore = create<GameStore>((set, get) => ({
    games: [],
    currentGame: null,
    sessionId: null,
    turnLog: [],
    choices: [],
    gameState: null,
    loading: false,
    error: null,
    turnCounter: 0,
    lastAction: null,
    checkerStatus: null,
    notebookOpen: false,
    selectedNotebookView: 'character',
    selectedCharacterId: null,

    loadGames: async () => {
        set({ loading: true, error: null });
        try {
            const games = await gameApi.listGames();
            set({ games, loading: false });
        } catch (error) {
            console.error(error);
            const errorMsg = 'Failed to load games';
            useToast.getState().error(errorMsg);
            set({ error: errorMsg, loading: false });
        }
    },

    startGame: async (gameId: string) => {
        set({ loading: true, error: null });

        try {
            const game = get().games.find(g => g.id === gameId) ?? null;
            let sessionId = '';
            let actionSummary = '';
            let accumulatedNarrative = '';

            // Process streaming chunks
            const stream = gameApi.startGameStream(gameId);

            for await (const chunk of stream) {
                if (chunk.type === 'session_created') {
                    sessionId = chunk.session_id;
                    // Immediately show game interface with placeholder entry
                    const placeholderEntry = buildTurnEntry(1, 'ai', 'Starting game...', 'Loading...');

                    // Create minimal placeholder state so UI can render
                    const placeholderState: any = {
                        snapshot: {
                            player: {
                                meters: {},
                                clothing: {},
                                modifiers: []
                            },
                            characters: [],
                            location: {
                                id: 'loading',
                                name: 'Loading...',
                                zone: '',
                                privacy: 'public',
                                exits: []
                            },
                            time: {
                                day: 1,
                                slot: 'morning',
                                time_hhmm: '09:00',
                                weekday: null,
                                mode: 'slots'
                            },
                            flags: {},
                            inventory: {},
                            arcs: {}
                        }
                    };

                    set({
                        sessionId,
                        currentGame: game,
                        turnLog: [placeholderEntry],
                        turnCounter: 1,
                        loading: false,  // Show UI immediately, streaming will update it
                        choices: [],     // Initialize as empty, will be populated when complete
                        gameState: placeholderState  // Minimal state to allow UI render
                    });
                    // Persist session early
                    if (game) {
                        saveSession(sessionId, gameId, game.title);
                    }
                } else if (chunk.type === 'initial_state') {
                    // Real state arrives - populate all panels immediately
                    set({
                        gameState: chunk.state_summary,
                        choices: chunk.choices
                    });
                } else if (chunk.type === 'action_summary') {
                    actionSummary = chunk.content;
                    set(state => {
                        const updatedLog = [...state.turnLog];
                        updatedLog[0] = {
                            ...updatedLog[0],
                            summary: actionSummary,
                            narrative: accumulatedNarrative || actionSummary
                        };
                        return { turnLog: updatedLog };
                    });
                } else if (chunk.type === 'narrative_chunk') {
                    accumulatedNarrative += chunk.content;
                    set(state => {
                        const updatedLog = [...state.turnLog];
                        updatedLog[0] = {
                            ...updatedLog[0],
                            narrative: accumulatedNarrative
                        };
                        return { turnLog: updatedLog };
                    });
                } else if (chunk.type === 'checker_status') {
                    set({ checkerStatus: chunk.message });
                } else if (chunk.type === 'complete') {
                    set(state => {
                        const updatedLog = [...state.turnLog];
                        updatedLog[0] = {
                            ...updatedLog[0],
                            summary: chunk.action_summary || actionSummary,
                            narrative: chunk.narrative
                        };
                        return {
                            turnLog: updatedLog,
                            choices: chunk.choices,
                            gameState: chunk.state_summary,
                            loading: false,
                            turnCounter: 1,
                            checkerStatus: null
                        };
                    });
                } else if (chunk.type === 'error') {
                    throw new Error(chunk.message);
                }
            }

            // Invalidate character queries for fresh data
            queryClient.invalidateQueries({ queryKey: ['characters-list'] });
            queryClient.invalidateQueries({ queryKey: ['character'] });
            queryClient.invalidateQueries({ queryKey: ['story-events'] });

            useToast.getState().success('Game started successfully!');
        } catch (error) {
            console.error(error);
            const errorMsg = 'Failed to start game';
            useToast.getState().error(errorMsg);
            set({ error: errorMsg, loading: false });
        }
    },

    sendAction: async (
        actionType,
        actionText,
        target,
        choiceId,
        itemId,
        options
    ) => {
        const sessionId = get().sessionId;
        if (!sessionId) return;

        set({ loading: true, error: null });

        // Store action for potential retry
        set({ lastAction: { actionType, actionText, target, choiceId, itemId, options } });

        try {
            const nextTurn = get().turnCounter + 1;
            const origin: TurnOrigin = options?.skipAi ? 'deterministic' : 'ai';

            // Create a placeholder entry that will be updated with streaming chunks
            let actionSummary = '';
            let accumulatedNarrative = '';
            let finalResponse: any = null;

            // Add placeholder entry immediately
            const placeholderEntry = buildTurnEntry(nextTurn, origin, 'Processing...', 'Processing...');
            set(state => ({
                turnLog: [...state.turnLog, placeholderEntry]
            }));

            // Process streaming chunks
            const stream = gameApi.sendActionStream(
                sessionId,
                actionType,
                actionText,
                target,
                choiceId,
                itemId,
                options
            );

            for await (const chunk of stream) {
                if (chunk.type === 'action_summary') {
                    actionSummary = chunk.content;
                    // Update with action summary
                    set(state => {
                        const updatedLog = [...state.turnLog];
                        updatedLog[updatedLog.length - 1] = {
                            ...updatedLog[updatedLog.length - 1],
                            summary: actionSummary,
                            narrative: accumulatedNarrative || actionSummary
                        };
                        return { turnLog: updatedLog };
                    });
                } else if (chunk.type === 'narrative_chunk') {
                    accumulatedNarrative += chunk.content;
                    // Update with streaming narrative
                    set(state => {
                        const updatedLog = [...state.turnLog];
                        updatedLog[updatedLog.length - 1] = {
                            ...updatedLog[updatedLog.length - 1],
                            narrative: accumulatedNarrative
                        };
                        return { turnLog: updatedLog };
                    });
                } else if (chunk.type === 'checker_status') {
                    // Update checker status message
                    set({ checkerStatus: chunk.message });
                } else if (chunk.type === 'complete') {
                    finalResponse = chunk;
                    // Clear checker status and final update
                    set(state => {
                        const updatedLog = [...state.turnLog];
                        updatedLog[updatedLog.length - 1] = {
                            ...updatedLog[updatedLog.length - 1],
                            summary: chunk.action_summary || actionSummary,
                            narrative: chunk.narrative
                        };
                        return {
                            turnLog: updatedLog,
                            choices: chunk.choices,
                            gameState: chunk.state_summary,
                            loading: false,
                            turnCounter: nextTurn,
                            checkerStatus: null
                        };
                    });
                } else if (chunk.type === 'error') {
                    throw new Error(chunk.message);
                }
            }

            // If we never got a complete response, update with what we have
            if (!finalResponse) {
                set(state => {
                    const updatedLog = [...state.turnLog];
                    updatedLog[updatedLog.length - 1] = {
                        ...updatedLog[updatedLog.length - 1],
                        summary: actionSummary || 'Action completed',
                        narrative: accumulatedNarrative || actionSummary
                    };
                    return {
                        turnLog: updatedLog,
                        loading: false,
                        turnCounter: nextTurn
                    };
                });
            }

            // Invalidate character queries (memories may have changed)
            queryClient.invalidateQueries({ queryKey: ['characters-list'] });
            queryClient.invalidateQueries({ queryKey: ['character'] });
            queryClient.invalidateQueries({ queryKey: ['story-events'] });

        } catch (error) {
            console.error(error);
            const errorMsg = 'Failed to send action';
            useToast.getState().error(errorMsg);
            set({ error: errorMsg, loading: false });
        }
    },

    performMovement: async (choiceId: string) => {
        const sessionId = get().sessionId;
        if (!sessionId) return;

        const payload: MovementRequest = {};
        if (choiceId.startsWith('move_')) {
            payload.destination_id = choiceId.substring(5);
        } else if (choiceId.startsWith('travel_')) {
            payload.zone_id = choiceId.substring(7);
        } else if (choiceId.startsWith('direction_')) {
            payload.direction = choiceId.substring(10);
        }

        // If we couldn't derive a deterministic payload, fall back to generic action
        if (!payload.destination_id && !payload.zone_id && !payload.direction) {
            const choice = get().choices.find(c => c.id === choiceId);
            const text = choice?.text ?? '';
            await get().sendAction('choice', text, null, choiceId, undefined, { skipAi: true });
            return;
        }

        // Optimistic update: Add loading turn entry immediately
        const nextTurn = get().turnCounter + 1;
        const destination = payload.destination_id || payload.zone_id || payload.direction || 'new location';
        const optimisticEntry = buildTurnEntry(nextTurn, 'deterministic', 'Moving...', `Moving to ${destination}...`);

        set(state => ({
            turnLog: [...state.turnLog, optimisticEntry],
            loading: true,
            error: null,
        }));

        try {
            const response = await gameApi.move(sessionId, payload);

            set(state => {
                const turnEntry = buildTurnEntry(nextTurn, 'deterministic', response.action_summary, response.message);
                const updatedChoices = extractChoicesFromDetails(response.details) ?? state.choices;

                return {
                    turnLog: [...state.turnLog.slice(0, -1), turnEntry], // Replace optimistic entry
                    choices: updatedChoices,
                    gameState: response.state_summary,
                    loading: false,
                    turnCounter: nextTurn,
                };
            });

            useToast.getState().success('Movement successful!');
        } catch (error) {
            console.error(error);
            const errorMsg = 'Failed to move';
            useToast.getState().error(errorMsg);
            // Revert optimistic update on error
            set(state => ({
                turnLog: state.turnLog.slice(0, -1),
                error: errorMsg,
                loading: false,
            }));
        }
    },

    performZoneTravel: async (zoneId: string, method: string | null, entryLocationId: string | null) => {
        const sessionId = get().sessionId;
        if (!sessionId) return;

        const payload: MovementRequest = {
            zone_id: zoneId,
            method: method,
            entry_location_id: entryLocationId,
        };

        // Optimistic update: Add loading turn entry immediately
        const nextTurn = get().turnCounter + 1;
        const optimisticEntry = buildTurnEntry(nextTurn, 'deterministic', 'Traveling...', `Traveling to ${zoneId}...`);

        set(state => ({
            turnLog: [...state.turnLog, optimisticEntry],
            loading: true,
            error: null,
        }));

        try {
            const response = await gameApi.move(sessionId, payload);

            set(state => {
                const turnEntry = buildTurnEntry(nextTurn, 'deterministic', response.action_summary, response.message);
                const updatedChoices = extractChoicesFromDetails(response.details) ?? state.choices;

                return {
                    turnLog: [...state.turnLog.slice(0, -1), turnEntry], // Replace optimistic entry
                    choices: updatedChoices,
                    gameState: response.state_summary,
                    loading: false,
                    turnCounter: nextTurn,
                };
            });

            useToast.getState().success('Travel successful!');
        } catch (error) {
            console.error(error);
            const errorMsg = 'Failed to travel';
            useToast.getState().error(errorMsg);
            // Revert optimistic update on error
            set(state => ({
                turnLog: state.turnLog.slice(0, -1),
                error: errorMsg,
                loading: false,
            }));
        }
    },

    purchaseItem: async (itemId, count = 1, price, sellerId) => {
        const sessionId = get().sessionId;
        if (!sessionId) return;

        set({ loading: true, error: null });
        try {
            const response = await gameApi.purchase(sessionId, itemId, count, price, sellerId);
            set(state => {
                const nextTurn = state.turnCounter + 1;
            const turnEntry = buildTurnEntry(nextTurn, 'deterministic', response.action_summary, response.message);

                return {
                    turnLog: [...state.turnLog, turnEntry],
                    gameState: response.state_summary,
                    choices: extractChoicesFromDetails(response.details) ?? state.choices,
                    loading: false,
                    turnCounter: nextTurn,
                };
            });
        } catch (error) {
            console.error(error);
            set({ error: 'Purchase failed', loading: false });
        }
    },

    sellItem: async (itemId, count = 1, price, buyerId) => {
        const sessionId = get().sessionId;
        if (!sessionId) return;

        set({ loading: true, error: null });
        try {
            const response = await gameApi.sell(sessionId, itemId, count, price, buyerId);
            set(state => {
                const nextTurn = state.turnCounter + 1;
            const turnEntry = buildTurnEntry(nextTurn, 'deterministic', response.action_summary, response.message);

                return {
                    turnLog: [...state.turnLog, turnEntry],
                    gameState: response.state_summary,
                    choices: extractChoicesFromDetails(response.details) ?? state.choices,
                    loading: false,
                    turnCounter: nextTurn,
                };
            });
        } catch (error) {
            console.error(error);
            set({ error: 'Sale failed', loading: false });
        }
    },

    takeItem: async (itemId, count = 1, ownerId = 'player') => {
        const sessionId = get().sessionId;
        if (!sessionId) return;

        set({ loading: true, error: null });
        try {
            const response = await gameApi.takeItem(sessionId, itemId, count, ownerId);
            set((state: GameStore) => createDeterministicUpdate(state, response));
        } catch (error) {
            console.error(error);
            set({ error: 'Failed to take item', loading: false });
        }
    },

    dropItem: async (itemId, count = 1, ownerId = 'player') => {
        const sessionId = get().sessionId;
        if (!sessionId) return;

        set({ loading: true, error: null });
        try {
            const response = await gameApi.dropItem(sessionId, itemId, count, ownerId);
            set((state: GameStore) => createDeterministicUpdate(state, response));
        } catch (error) {
            console.error(error);
            set({ error: 'Failed to drop item', loading: false });
        }
    },

    giveItem: async (itemId, targetId, count = 1, sourceId = 'player') => {
        const sessionId = get().sessionId;
        if (!sessionId) return;

        set({ loading: true, error: null });
        try {
            const response = await gameApi.giveItem(sessionId, itemId, targetId, count, sourceId);
            set((state: GameStore) => createDeterministicUpdate(state, response));
        } catch (error) {
            console.error(error);
            set({ error: 'Failed to give item', loading: false });
        }
    },

    putOnClothing: async (clothingId, characterId = 'player', state) => {
        const sessionId = get().sessionId;
        if (!sessionId) return;

        set({ loading: true, error: null });
        try {
            const response = await gameApi.putOnClothing(sessionId, clothingId, characterId, state);
            set((stateStore: GameStore) => createDeterministicUpdate(stateStore, response));
        } catch (error) {
            console.error(error);
            set({ error: 'Failed to put on clothing', loading: false });
        }
    },

    takeOffClothing: async (clothingId, characterId = 'player') => {
        const sessionId = get().sessionId;
        if (!sessionId) return;

        set({ loading: true, error: null });
        try {
            const response = await gameApi.takeOffClothing(sessionId, clothingId, characterId);
            set((stateStore: GameStore) => createDeterministicUpdate(stateStore, response));
        } catch (error) {
            console.error(error);
            set({ error: 'Failed to take off clothing', loading: false });
        }
    },

    setClothingState: async (clothingId, stateValue: ClothingStateValue, characterId = 'player') => {
        const sessionId = get().sessionId;
        if (!sessionId) return;

        set({ loading: true, error: null });
        try {
            const response = await gameApi.setClothingState(sessionId, clothingId, stateValue, characterId);
            set((stateStore: GameStore) => createDeterministicUpdate(stateStore, response));
        } catch (error) {
            console.error(error);
            set({ error: 'Failed to adjust clothing', loading: false });
        }
    },

    putOnOutfit: async (outfitId, characterId = 'player') => {
        const sessionId = get().sessionId;
        if (!sessionId) return;

        set({ loading: true, error: null });
        try {
            const response = await gameApi.putOnOutfit(sessionId, outfitId, characterId);
            set((stateStore: GameStore) => createDeterministicUpdate(stateStore, response));
        } catch (error) {
            console.error(error);
            set({ error: 'Failed to change outfit', loading: false });
        }
    },

    takeOffOutfit: async (outfitId, characterId = 'player') => {
        const sessionId = get().sessionId;
        if (!sessionId) return;

        set({ loading: true, error: null });
        try {
            const response = await gameApi.takeOffOutfit(sessionId, outfitId, characterId);
            set((stateStore: GameStore) => createDeterministicUpdate(stateStore, response));
        } catch (error) {
            console.error(error);
            set({ error: 'Failed to remove outfit', loading: false });
        }
    },


    retryLastAction: async () => {
        const { lastAction, sessionId } = get();
        if (!lastAction || !sessionId || lastAction.options?.skipAi) {
            useToast.getState().error('No AI action to retry');
            return;
        }

        set({ loading: true, error: null });
        try {
            const response = await gameApi.sendAction(
                sessionId,
                lastAction.actionType,
                lastAction.actionText,
                lastAction.target,
                lastAction.choiceId,
                lastAction.itemId,
                lastAction.options
            );

            // Replace the last entry with the new response
            set(state => {
                const updatedLog = [...state.turnLog];
                const lastEntry = updatedLog[updatedLog.length - 1];
                if (lastEntry) {
                    updatedLog[updatedLog.length - 1] = {
                        ...lastEntry,
                        narrative: response.narrative,
                        timestamp: new Date().toISOString(),
                    };
                }

                return {
                    turnLog: updatedLog,
                    choices: response.choices,
                    gameState: response.state_summary,
                    loading: false,
                };
            });

            useToast.getState().success('Response regenerated!');
        } catch (error) {
            console.error('Failed to retry action:', error);
            useToast.getState().error('Failed to regenerate response');
            set({ loading: false });
        }
    },

    clearTurnLog: () => {
        set(state => ({ turnLog: state.turnLog.slice(-10) }));
    },

    resetGame: () => {
        // Clear localStorage session
        clearSession();

        set({
            currentGame: null,
            sessionId: null,
            turnLog: [],
            choices: [],
            gameState: null,
            turnCounter: 0,
        });
    },

    hasStoredSession: () => {
        return hasStoredSession();
    },

    restoreSession: async () => {
        const stored = loadSession();
        if (!stored) {
            set({ error: 'No saved session found' });
            return;
        }

        set({ loading: true, error: null });
        try {
            // Fetch current state from backend
            const stateResponse = await gameApi.getState(stored.sessionId);

            // Find the game info
            const games = get().games;
            if (games.length === 0) {
                await get().loadGames();
            }
            const game = get().games.find(g => g.id === stored.gameId) ?? {
                id: stored.gameId,
                title: stored.gameTitle,
                author: 'Unknown',
                content_rating: 'Unknown',
                version: '1.0',
            };

            // Extract last few turns from history to build turn log
            const history = stateResponse.history || [];
            const turnLog: TurnLogEntry[] = history.map((narrative, index) => ({
                id: index + 1,
                summary: `Turn ${index + 1}`,
                narrative,
                origin: 'ai' as TurnOrigin,
                timestamp: new Date().toLocaleTimeString(),
            }));

            // For now, we'll need to make a dummy action call to get current choices
            // This is a limitation - we can't restore choices without the backend tracking them
            set({
                currentGame: game,
                sessionId: stored.sessionId,
                turnLog: turnLog.length > 0 ? turnLog : [],
                choices: [], // Will be populated on next action
                gameState: stateResponse.state as GameState,
                loading: false,
                turnCounter: turnLog.length,
            });
        } catch (error) {
            console.error('Failed to restore session:', error);
            clearSession();
            set({ error: 'Failed to restore session', loading: false });
        }
    },

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

const createDeterministicUpdate = (state: GameStore, response: DeterministicActionResponse) => {
    const nextTurn = state.turnCounter + 1;
    const turnEntry = buildTurnEntry(nextTurn, 'deterministic', response.action_summary, response.message);

    return {
        turnLog: [...state.turnLog, turnEntry],
        gameState: response.state_summary,
        choices: extractChoicesFromDetails(response.details) ?? state.choices,
        loading: false,
        turnCounter: nextTurn,
    };
};
