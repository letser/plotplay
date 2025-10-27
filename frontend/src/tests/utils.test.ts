/**
 * Tests for utility functions.
 */

import { getMeterColor, formatMeterId, capitalize, toTitleCase, formatLocationName } from '../utils';

describe('Utility Functions', () => {
    describe('getMeterColor', () => {
        it('returns correct color for known meters', () => {
            expect(getMeterColor('attraction')).toBe('bg-pink-500');
            expect(getMeterColor('trust')).toBe('bg-blue-500');
            expect(getMeterColor('arousal')).toBe('bg-red-500');
            expect(getMeterColor('corruption')).toBe('bg-purple-500');
            expect(getMeterColor('energy')).toBe('bg-yellow-500');
            expect(getMeterColor('confidence')).toBe('bg-orange-500');
            expect(getMeterColor('money')).toBe('bg-green-500');
        });

        it('is case insensitive', () => {
            expect(getMeterColor('TRUST')).toBe('bg-blue-500');
            expect(getMeterColor('TrUsT')).toBe('bg-blue-500');
        });

        it('returns default color for unknown meters', () => {
            expect(getMeterColor('unknown_meter')).toBe('bg-gray-500');
            expect(getMeterColor('custom_stat')).toBe('bg-gray-500');
        });
    });

    describe('formatMeterId', () => {
        it('formats meter IDs with underscores', () => {
            expect(formatMeterId('trust_level')).toBe('Trust Level');
            expect(formatMeterId('max_energy')).toBe('Max Energy');
        });

        it('capitalizes single words', () => {
            expect(formatMeterId('energy')).toBe('Energy');
            expect(formatMeterId('trust')).toBe('Trust');
        });

        it('handles multiple underscores', () => {
            expect(formatMeterId('max_trust_level')).toBe('Max Trust Level');
        });

        it('handles empty string', () => {
            expect(formatMeterId('')).toBe('');
        });
    });

    describe('capitalize', () => {
        it('capitalizes first letter', () => {
            expect(capitalize('hello')).toBe('Hello');
            expect(capitalize('world')).toBe('World');
        });

        it('does not change already capitalized text', () => {
            expect(capitalize('Hello')).toBe('Hello');
        });

        it('handles single character', () => {
            expect(capitalize('a')).toBe('A');
        });

        it('handles empty string', () => {
            expect(capitalize('')).toBe('');
        });

        it('only capitalizes first letter', () => {
            expect(capitalize('hello world')).toBe('Hello world');
        });
    });

    describe('toTitleCase', () => {
        it('converts underscored text to title case', () => {
            expect(toTitleCase('coffee_shop')).toBe('Coffee Shop');
            expect(toTitleCase('main_street')).toBe('Main Street');
        });

        it('handles single words', () => {
            expect(toTitleCase('library')).toBe('Library');
        });

        it('handles multiple underscores', () => {
            expect(toTitleCase('north_main_street')).toBe('North Main Street');
        });

        it('handles null and undefined', () => {
            expect(toTitleCase(null)).toBe('');
            expect(toTitleCase(undefined)).toBe('');
        });

        it('handles empty string', () => {
            expect(toTitleCase('')).toBe('');
        });
    });

    describe('formatLocationName', () => {
        it('formats location names with underscores', () => {
            expect(formatLocationName('coffee_shop')).toBe('Coffee Shop');
            expect(formatLocationName('main_street')).toBe('Main Street');
        });

        it('handles camelCase', () => {
            expect(formatLocationName('coffeeShop')).toBe('CoffeeShop');
        });

        it('capitalizes each word', () => {
            expect(formatLocationName('north_side_park')).toBe('North Side Park');
        });

        it('handles single words', () => {
            expect(formatLocationName('library')).toBe('Library');
        });
    });
});
