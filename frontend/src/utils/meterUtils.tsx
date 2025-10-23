/**
 * Utility functions for working with meters.
 */

import type { ReactNode } from 'react';

/**
 * Returns the appropriate Tailwind color class for a meter based on its ID.
 */
export const getMeterColor = (meterId: string): string => {
    const colors: Record<string, string> = {
        attraction: 'bg-pink-500',
        trust: 'bg-blue-500',
        arousal: 'bg-red-500',
        corruption: 'bg-purple-500',
        energy: 'bg-yellow-500',
        confidence: 'bg-orange-500',
        money: 'bg-green-500',
        comfort: 'bg-teal-500',
        interest: 'bg-rose-500',
    };
    return colors[meterId.toLowerCase()] || 'bg-gray-500';
};

/**
 * Renders a meter icon or placeholder.
 * Returns a span with the icon character, or an empty div if no icon.
 */
export const renderMeterIcon = (icon: string | null): ReactNode => {
    if (icon) {
        return <span>{icon}</span>;
    }
    return <div className="w-4 h-4" />;
};

/**
 * Formats a meter ID for display (e.g., "trust_level" → "Trust Level").
 */
export const formatMeterId = (meterId: string): string => {
    return meterId
        .replace(/_/g, ' ')
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
};
