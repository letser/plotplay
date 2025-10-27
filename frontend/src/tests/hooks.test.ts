/**
 * Tests for custom hooks.
 */

import { renderHook } from '@testing-library/react';
import { useSnapshot, usePlayer, usePresentCharacters, useLocation, useTimeInfo } from '../hooks';
import { setupGameStore, resetGameStore, createMockGameState } from './testUtils';

describe('Custom Hooks', () => {
    beforeEach(() => {
        resetGameStore();
    });

    describe('useSnapshot', () => {
        it('returns null when no game state exists', () => {
            const { result } = renderHook(() => useSnapshot());
            expect(result.current).toBeNull();
        });

        it('returns snapshot when game state exists', () => {
            const mockState = createMockGameState();
            setupGameStore({ gameState: mockState });

            const { result } = renderHook(() => useSnapshot());
            expect(result.current).toBe(mockState.snapshot);
        });

        it('returns null when snapshot is undefined', () => {
            const mockState = createMockGameState({ snapshot: undefined });
            setupGameStore({ gameState: mockState });

            const { result } = renderHook(() => useSnapshot());
            expect(result.current).toBeNull();
        });
    });

    describe('usePlayer', () => {
        it('returns null when no snapshot exists', () => {
            const { result } = renderHook(() => usePlayer());
            expect(result.current).toBeNull();
        });

        it('returns player data from snapshot', () => {
            const mockState = createMockGameState();
            setupGameStore({ gameState: mockState });

            const { result } = renderHook(() => usePlayer());
            expect(result.current).toBeDefined();
            expect(result.current?.id).toBe('player');
            expect(result.current?.name).toBe('You');
        });

        it('includes player inventory', () => {
            const mockState = createMockGameState();
            setupGameStore({ gameState: mockState });

            const { result } = renderHook(() => usePlayer());
            expect(result.current?.inventory).toBeDefined();
            expect(result.current?.inventory.item1).toBe(2);
        });

        it('includes player meters', () => {
            const mockState = createMockGameState();
            setupGameStore({ gameState: mockState });

            const { result } = renderHook(() => usePlayer());
            expect(result.current?.meters).toBeDefined();
            expect(result.current?.meters.energy).toBeDefined();
            expect(result.current?.meters.energy.value).toBe(80);
        });
    });

    describe('usePresentCharacters', () => {
        it('returns empty array when no snapshot exists', () => {
            const { result } = renderHook(() => usePresentCharacters());
            expect(result.current).toEqual([]);
        });

        it('returns present characters from snapshot', () => {
            const mockState = createMockGameState();
            setupGameStore({ gameState: mockState });

            const { result } = renderHook(() => usePresentCharacters());
            expect(result.current).toHaveLength(1);
            expect(result.current[0].id).toBe('npc1');
            expect(result.current[0].name).toBe('Test NPC');
        });

        it('does not include player in the list', () => {
            const mockState = createMockGameState();
            setupGameStore({ gameState: mockState });

            const { result } = renderHook(() => usePresentCharacters());
            const playerInList = result.current.some(char => char.id === 'player');
            expect(playerInList).toBe(false);
        });
    });

    describe('useLocation', () => {
        it('returns null when no snapshot exists', () => {
            const { result } = renderHook(() => useLocation());
            expect(result.current).toBeNull();
        });

        it('returns location data from snapshot', () => {
            const mockState = createMockGameState();
            setupGameStore({ gameState: mockState });

            const { result } = renderHook(() => useLocation());
            expect(result.current).toBeDefined();
            expect(result.current?.id).toBe('test_location');
            expect(result.current?.name).toBe('Test Location');
        });

        it('includes exits information', () => {
            const mockState = createMockGameState();
            setupGameStore({ gameState: mockState });

            const { result } = renderHook(() => useLocation());
            expect(result.current?.exits).toBeDefined();
            expect(result.current?.exits).toHaveLength(1);
            expect(result.current?.exits[0].direction).toBe('n');
        });

        it('includes privacy level', () => {
            const mockState = createMockGameState();
            setupGameStore({ gameState: mockState });

            const { result } = renderHook(() => useLocation());
            expect(result.current?.privacy).toBe('public');
        });
    });

    describe('useTimeInfo', () => {
        it('returns null when no snapshot exists', () => {
            const { result } = renderHook(() => useTimeInfo());
            expect(result.current).toBeNull();
        });

        it('returns time data from snapshot', () => {
            const mockState = createMockGameState();
            setupGameStore({ gameState: mockState });

            const { result } = renderHook(() => useTimeInfo());
            expect(result.current).toBeDefined();
            expect(result.current?.day).toBe(1);
            expect(result.current?.slot).toBe('morning');
        });

        it('includes clock time when available', () => {
            const mockState = createMockGameState();
            setupGameStore({ gameState: mockState });

            const { result } = renderHook(() => useTimeInfo());
            expect(result.current?.time_hhmm).toBe('09:00');
        });

        it('includes weekday when available', () => {
            const mockState = createMockGameState();
            setupGameStore({ gameState: mockState });

            const { result } = renderHook(() => useTimeInfo());
            expect(result.current?.weekday).toBe('monday');
        });
    });
});
