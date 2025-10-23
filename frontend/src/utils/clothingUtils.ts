/**
 * Utility functions for formatting clothing/attire.
 */

/**
 * Formats attire for display.
 * Handles both string format (legacy) and object format (new clothing system).
 */
export const formatAttire = (attire?: string | Record<string, string | null> | null): string | null => {
    if (!attire) return null;

    // If it's a string, return as-is
    if (typeof attire === 'string') {
        return attire;
    }

    // If it's an object, format it as a comma-separated list
    const items = Object.entries(attire)
        .filter(([_, value]) => value !== null && value !== '')
        .map(([_slot, item]) => item);

    if (items.length === 0) return null;

    return items.join(', ');
};
