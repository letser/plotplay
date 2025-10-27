/**
 * Test utilities for React Testing Library with Zustand.
 */

import { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { useGameStore } from '../stores/gameStore';
import type { GameInfo, GameState, GameChoice } from '../services/gameApi';

/**
 * Creates a mock game state for testing.
 */
export const createMockGameState = (overrides?: Partial<GameState>): GameState => {
    return {
        day: 1,
        time: 'morning',
        location: 'test_location',
        location_id: 'test_location',
        zone: 'test_zone',
        present_characters: ['npc1'],
        character_details: {
            npc1: {
                name: 'Test NPC',
                pronouns: ['they', 'them'],
                wearing: 'casual clothes',
            },
        },
        player_details: {
            name: 'You',
            pronouns: ['you'],
            wearing: 'jeans and t-shirt',
        },
        meters: {
            player: {
                energy: { value: 80, min: 0, max: 100, icon: '⚡', visible: true },
                money: { value: 50, min: 0, max: 1000, icon: '💰', visible: true },
            },
            npc1: {
                trust: { value: 50, min: 0, max: 100, icon: '❤️', visible: true },
            },
        },
        inventory: {
            item1: 2,
        },
        inventory_details: {
            item1: {
                id: 'item1',
                name: 'Test Item',
                description: 'A test item',
                icon: '📦',
                stackable: true,
                droppable: true,
            },
        },
        flags: {
            test_flag: {
                value: true,
                label: 'Test Flag',
            },
        },
        modifiers: {},
        turn_count: 5,
        snapshot: {
            time: {
                day: 1,
                slot: 'morning',
                time_hhmm: '09:00',
                weekday: 'monday',
            },
            location: {
                id: 'test_location',
                name: 'Test Location',
                zone: 'test_zone',
                privacy: 'public',
                summary: 'A test location',
                has_shop: false,
                exits: [
                    {
                        direction: 'n',
                        to: 'north_location',
                        name: 'North Exit',
                        available: true,
                        locked: false,
                        description: null,
                    },
                ],
            },
            player: {
                id: 'player',
                name: 'You',
                pronouns: ['you'],
                attire: 'jeans and t-shirt',
                meters: {
                    energy: { value: 80, min: 0, max: 100, icon: '⚡', visible: true },
                    money: { value: 50, min: 0, max: 1000, icon: '💰', visible: true },
                },
                modifiers: [],
                inventory: {
                    item1: 2,
                },
            },
            characters: [
                {
                    id: 'npc1',
                    name: 'Test NPC',
                    pronouns: ['they', 'them'],
                    attire: 'casual clothes',
                    meters: {
                        trust: { value: 50, min: 0, max: 100, icon: '❤️', visible: true },
                    },
                    modifiers: [],
                },
            ],
        },
        ...overrides,
    };
};

/**
 * Creates a mock game info for testing.
 */
export const createMockGameInfo = (overrides?: Partial<GameInfo>): GameInfo => {
    return {
        id: 'test_game',
        title: 'Test Game',
        author: 'Test Author',
        content_rating: 'general',
        version: '1.0.0',
        ...overrides,
    };
};

/**
 * Creates mock choices for testing.
 */
export const createMockChoices = (): GameChoice[] => {
    return [
        {
            id: 'choice1',
            text: 'Say hello',
            type: 'node_choice',
        },
        {
            id: 'choice2',
            text: 'Move north',
            type: 'movement',
        },
    ];
};

/**
 * Resets the game store to initial state.
 * Useful for cleaning up between tests.
 */
export const resetGameStore = () => {
    useGameStore.setState({
        games: [],
        currentGame: null,
        sessionId: null,
        turnLog: [],
        choices: [],
        gameState: null,
        loading: false,
        error: null,
        turnCounter: 0,
        deterministicActionsEnabled: true,
    });
};

/**
 * Sets up the game store with test data.
 */
export const setupGameStore = (options?: {
    sessionId?: string;
    currentGame?: GameInfo;
    gameState?: GameState;
    choices?: GameChoice[];
}) => {
    const {
        sessionId = 'test-session-id',
        currentGame = createMockGameInfo(),
        gameState = createMockGameState(),
        choices = createMockChoices(),
    } = options || {};

    useGameStore.setState({
        currentGame,
        sessionId,
        gameState,
        choices,
        loading: false,
        error: null,
        turnCounter: 1,
    });
};

/**
 * Custom render function that wraps components with necessary providers.
 */
export const renderWithProviders = (
    ui: ReactElement,
    options?: RenderOptions
) => {
    return render(ui, { ...options });
};

// Re-export everything from React Testing Library
export * from '@testing-library/react';
