/**
 * Tests for localStorage utilities.
 */

import { saveSession, loadSession, clearSession, hasStoredSession } from '../utils/storage';

// Mock localStorage
const localStorageMock = (() => {
    let store: Record<string, string> = {};

    return {
        getItem: (key: string) => store[key] || null,
        setItem: (key: string, value: string) => {
            store[key] = value;
        },
        removeItem: (key: string) => {
            delete store[key];
        },
        clear: () => {
            store = {};
        },
    };
})();

Object.defineProperty(window, 'localStorage', {
    value: localStorageMock,
});

describe('Storage Utilities', () => {
    beforeEach(() => {
        localStorageMock.clear();
    });

    describe('saveSession', () => {
        it('saves session to localStorage', () => {
            saveSession('session-123', 'game-456', 'Test Game');

            const stored = localStorageMock.getItem('plotplay_session');
            expect(stored).toBeTruthy();

            const data = JSON.parse(stored!);
            expect(data.sessionId).toBe('session-123');
            expect(data.gameId).toBe('game-456');
            expect(data.gameTitle).toBe('Test Game');
        });

        it('includes version and timestamp', () => {
            saveSession('session-123', 'game-456', 'Test Game');

            const stored = localStorageMock.getItem('plotplay_session');
            const data = JSON.parse(stored!);

            expect(data.version).toBe(1);
            expect(data.timestamp).toBeGreaterThan(0);
        });

        it('overwrites previous session', () => {
            saveSession('session-1', 'game-1', 'Game 1');
            saveSession('session-2', 'game-2', 'Game 2');

            const stored = localStorageMock.getItem('plotplay_session');
            const data = JSON.parse(stored!);

            expect(data.sessionId).toBe('session-2');
            expect(data.gameTitle).toBe('Game 2');
        });
    });

    describe('loadSession', () => {
        it('loads saved session', () => {
            saveSession('session-123', 'game-456', 'Test Game');

            const loaded = loadSession();
            expect(loaded).toBeTruthy();
            expect(loaded?.sessionId).toBe('session-123');
            expect(loaded?.gameId).toBe('game-456');
            expect(loaded?.gameTitle).toBe('Test Game');
        });

        it('returns null when no session exists', () => {
            const loaded = loadSession();
            expect(loaded).toBeNull();
        });

        it('returns null and clears session if version mismatch', () => {
            const invalidData = {
                version: 99,
                timestamp: Date.now(),
                sessionId: 'session-123',
                gameId: 'game-456',
                gameTitle: 'Test Game',
            };
            localStorageMock.setItem('plotplay_session', JSON.stringify(invalidData));

            const loaded = loadSession();
            expect(loaded).toBeNull();

            // Should clear the invalid session
            const stored = localStorageMock.getItem('plotplay_session');
            expect(stored).toBeNull();
        });

        it('returns null and clears session if too old', () => {
            const oldTimestamp = Date.now() - (8 * 24 * 60 * 60 * 1000); // 8 days ago
            const oldData = {
                version: 1,
                timestamp: oldTimestamp,
                sessionId: 'session-123',
                gameId: 'game-456',
                gameTitle: 'Test Game',
            };
            localStorageMock.setItem('plotplay_session', JSON.stringify(oldData));

            const loaded = loadSession();
            expect(loaded).toBeNull();

            // Should clear the old session
            const stored = localStorageMock.getItem('plotplay_session');
            expect(stored).toBeNull();
        });

        it('loads session within age limit', () => {
            const recentTimestamp = Date.now() - (2 * 24 * 60 * 60 * 1000); // 2 days ago
            const recentData = {
                version: 1,
                timestamp: recentTimestamp,
                sessionId: 'session-123',
                gameId: 'game-456',
                gameTitle: 'Test Game',
            };
            localStorageMock.setItem('plotplay_session', JSON.stringify(recentData));

            const loaded = loadSession();
            expect(loaded).toBeTruthy();
            expect(loaded?.sessionId).toBe('session-123');
        });
    });

    describe('clearSession', () => {
        it('removes session from localStorage', () => {
            saveSession('session-123', 'game-456', 'Test Game');

            let stored = localStorageMock.getItem('plotplay_session');
            expect(stored).toBeTruthy();

            clearSession();

            stored = localStorageMock.getItem('plotplay_session');
            expect(stored).toBeNull();
        });

        it('does not throw error when no session exists', () => {
            expect(() => clearSession()).not.toThrow();
        });
    });

    describe('hasStoredSession', () => {
        it('returns true when valid session exists', () => {
            saveSession('session-123', 'game-456', 'Test Game');

            expect(hasStoredSession()).toBe(true);
        });

        it('returns false when no session exists', () => {
            expect(hasStoredSession()).toBe(false);
        });

        it('returns false when session is invalid', () => {
            const invalidData = {
                version: 99,
                timestamp: Date.now(),
                sessionId: 'session-123',
                gameId: 'game-456',
                gameTitle: 'Test Game',
            };
            localStorageMock.setItem('plotplay_session', JSON.stringify(invalidData));

            expect(hasStoredSession()).toBe(false);
        });
    });
});
