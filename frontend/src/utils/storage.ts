/**
 * LocalStorage utilities for persisting game state.
 * Enables session recovery on page refresh.
 */

const STORAGE_KEY = 'plotplay_session';
const STORAGE_VERSION = 1;

interface StoredSession {
    version: number;
    timestamp: number;
    sessionId: string;
    gameId: string;
    gameTitle: string;
}

/**
 * Save current session to localStorage.
 */
export const saveSession = (
    sessionId: string,
    gameId: string,
    gameTitle: string
): void => {
    try {
        const data: StoredSession = {
            version: STORAGE_VERSION,
            timestamp: Date.now(),
            sessionId,
            gameId,
            gameTitle,
        };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    } catch (error) {
        console.error('Failed to save session to localStorage:', error);
    }
};

/**
 * Load saved session from localStorage.
 * Returns null if no session exists or if it's invalid.
 */
export const loadSession = (): StoredSession | null => {
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (!stored) return null;

        const data: StoredSession = JSON.parse(stored);

        // Validate version
        if (data.version !== STORAGE_VERSION) {
            console.warn('Stored session has incompatible version, ignoring');
            clearSession();
            return null;
        }

        // Check if session is too old (older than 7 days)
        const MAX_AGE = 7 * 24 * 60 * 60 * 1000; // 7 days in milliseconds
        if (Date.now() - data.timestamp > MAX_AGE) {
            console.warn('Stored session is too old, clearing');
            clearSession();
            return null;
        }

        return data;
    } catch (error) {
        console.error('Failed to load session from localStorage:', error);
        return null;
    }
};

/**
 * Clear saved session from localStorage.
 */
export const clearSession = (): void => {
    try {
        localStorage.removeItem(STORAGE_KEY);
    } catch (error) {
        console.error('Failed to clear session from localStorage:', error);
    }
};

/**
 * Check if a saved session exists.
 */
export const hasStoredSession = (): boolean => {
    return loadSession() !== null;
};
