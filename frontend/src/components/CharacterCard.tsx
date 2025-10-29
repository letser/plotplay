import React from 'react';
import { SnapshotCharacter } from '../services/gameApi';
import { useGameStore } from '../stores/gameStore';
import { Shirt } from 'lucide-react';

interface CharacterCardProps {
    character: SnapshotCharacter & {
        age?: number;
        gender?: string;
        pronouns?: string[] | null;
    };
    onClick?: () => void;
}

export function CharacterCard({ character, onClick }: CharacterCardProps) {
    const openNotebook = useGameStore(state => state.openNotebook);

    const handleClick = () => {
        if (onClick) {
            onClick();
        } else {
            openNotebook(character.id);
        }
    };

    // Summarize clothing
    const clothingSummary = summarizeClothing(character.attire);

    // Get top 2 modifiers
    const topModifiers = character.modifiers?.slice(0, 2) || [];

    return (
        <div
            onClick={handleClick}
            className="p-2 bg-gray-800 border border-gray-700 rounded-lg cursor-pointer transition-all hover:bg-gray-700 hover:border-gray-600 hover:scale-105 active:scale-95"
        >
            {/* Single line: Name, age/gender, clothing icon, modifiers, presence */}
            <div className="flex items-center gap-3">
                {/* Name */}
                <h3 className="font-semibold text-gray-100 flex-shrink-0">{character.name}</h3>

                {/* Age/Gender (compact) */}
                {(character.age || character.gender) && (
                    <span className="text-xs text-gray-400 flex-shrink-0">
                        {[character.age, character.gender].filter(Boolean).join(', ')}
                    </span>
                )}

                {/* Clothing icon with hover tooltip */}
                <div title={clothingSummary.text} className="flex-shrink-0">
                    {clothingSummary.icon}
                </div>

                {/* Active modifiers (max 2) */}
                {topModifiers.length > 0 && (
                    <div className="flex gap-1 flex-shrink-0">
                        {topModifiers.map(mod => (
                            <span
                                key={mod.id}
                                className="px-2 py-0.5 text-xs rounded-full bg-blue-900/30 text-blue-300"
                            >
                                {mod.id}
                            </span>
                        ))}
                    </div>
                )}

                {/* Presence indicator (right-aligned) */}
                <div className="ml-auto flex-shrink-0">
                    <div className="w-2 h-2 rounded-full bg-green-500" title="Present" />
                </div>
            </div>
        </div>
    );
}

function summarizeClothing(attire: string | Record<string, any> | null | undefined): {
    icon: React.ReactNode;
    text: string;
    color: string;
} {
    if (!attire) {
        return {
            icon: <Shirt className="w-4 h-4 text-gray-500" />,
            text: 'Unknown',
            color: 'text-gray-500'
        };
    }

    if (typeof attire === 'string') {
        const lower = attire.toLowerCase();

        if (lower.includes('naked') || lower.includes('nude')) {
            return {
                icon: <Shirt className="w-4 h-4 text-red-400 opacity-50" />,
                text: 'Unclothed',
                color: 'text-red-400'
            };
        }
        if (lower.includes('underwear only') || lower.includes('lingerie only')) {
            return {
                icon: <Shirt className="w-4 h-4 text-orange-400" />,
                text: 'Underwear only',
                color: 'text-orange-400'
            };
        }
        if (lower.includes('partially') || lower.includes('displaced')) {
            return {
                icon: <Shirt className="w-4 h-4 text-yellow-400" />,
                text: 'Partially dressed',
                color: 'text-yellow-400'
            };
        }

        // Fully dressed or specific description
        return {
            icon: <Shirt className="w-4 h-4 text-green-400" />,
            text: attire,
            color: 'text-green-400'
        };
    }

    // Handle wardrobe_state object
    const states = Object.values(attire).filter(s => typeof s === 'string');
    const removed = states.filter(s => s === 'removed').length;
    const displaced = states.filter(s => s === 'displaced').length;

    if (states.length === 0) {
        return {
            icon: <Shirt className="w-4 h-4 text-gray-500" />,
            text: 'Unknown',
            color: 'text-gray-500'
        };
    }

    if (removed === states.length) {
        return {
            icon: <Shirt className="w-4 h-4 text-red-400 opacity-50" />,
            text: 'Unclothed',
            color: 'text-red-400'
        };
    }
    if (removed > 0 || displaced > 0) {
        return {
            icon: <Shirt className="w-4 h-4 text-yellow-400" />,
            text: 'Partially dressed',
            color: 'text-yellow-400'
        };
    }
    return {
        icon: <Shirt className="w-4 h-4 text-green-400" />,
        text: 'Fully dressed',
        color: 'text-green-400'
    };
}
