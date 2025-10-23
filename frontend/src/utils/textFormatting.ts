/**
 * Text formatting utilities.
 */

/**
 * Capitalizes the first letter of a string.
 * Example: "hello" → "Hello"
 */
export const capitalize = (text: string): string => {
    if (!text) return '';
    return text.charAt(0).toUpperCase() + text.slice(1);
};

/**
 * Converts underscores to spaces and capitalizes each word.
 * Example: "coffee_shop" → "Coffee Shop"
 */
export const toTitleCase = (text: string | null | undefined): string => {
    if (!text) return '';
    return text
        .replace(/_/g, ' ')
        .split(' ')
        .map(word => capitalize(word))
        .join(' ');
};

/**
 * Formats a location/zone name for display.
 * Replaces underscores with spaces and capitalizes.
 */
export const formatLocationName = (name: string): string => {
    return name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
};
