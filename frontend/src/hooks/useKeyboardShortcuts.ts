/**
 * Custom hook for keyboard shortcuts.
 */

import { useEffect } from 'react';

type KeyHandler = (event: KeyboardEvent) => void;

interface ShortcutConfig {
    key: string;
    ctrl?: boolean;
    shift?: boolean;
    alt?: boolean;
    meta?: boolean;
    handler: KeyHandler;
    description?: string;
}

export const useKeyboardShortcut = (config: ShortcutConfig) => {
    useEffect(() => {
        const handleKeyDown = (event: KeyboardEvent) => {
            const { key, ctrl = false, shift = false, alt = false, meta = false, handler } = config;

            // Check if all modifier keys match
            if (
                event.key === key &&
                event.ctrlKey === ctrl &&
                event.shiftKey === shift &&
                event.altKey === alt &&
                event.metaKey === meta
            ) {
                event.preventDefault();
                handler(event);
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [config]);
};

/**
 * Hook for multiple keyboard shortcuts.
 */
export const useKeyboardShortcuts = (configs: ShortcutConfig[]) => {
    useEffect(() => {
        const handleKeyDown = (event: KeyboardEvent) => {
            for (const config of configs) {
                const { key, ctrl = false, shift = false, alt = false, meta = false, handler } = config;

                if (
                    event.key === key &&
                    event.ctrlKey === ctrl &&
                    event.shiftKey === shift &&
                    event.altKey === alt &&
                    event.metaKey === meta
                ) {
                    event.preventDefault();
                    handler(event);
                    return;
                }
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [configs]);
};
