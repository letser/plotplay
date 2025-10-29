import { useState } from 'react';
import { CharacterFull } from '../services/gameApi';
import { User, Lock, Unlock, Shirt, Package, Hand, Trash2, ArrowRightLeft } from 'lucide-react';
import { getMeterColor, renderMeterIcon, formatMeterId } from '../utils';
import { useGameStore } from '../stores/gameStore';
import { usePresentCharacters } from '../hooks';

interface CharacterProfileProps {
    character: CharacterFull;
}

export function CharacterProfile({ character }: CharacterProfileProps) {
    const isPlayer = character.id === 'player';
    const { gameState, sendAction, dropItem, giveItem, loading } = useGameStore();
    const presentCharacters = usePresentCharacters();
    const [openGiveMenu, setOpenGiveMenu] = useState<string | null>(null);

    const inventoryDetails = gameState?.inventory_details || {};
    const hasInventory = Object.keys(character.inventory).length > 0;
    const hasWardrobe = Object.keys(character.wardrobe).length > 0;

    // Helper to check if blocks should be shown
    const hasPersonality = character.personality && (
        character.personality.core_traits ||
        character.personality.quirks ||
        character.personality.values ||
        character.personality.fears
    );
    const hasGates = character.gates && character.gates.length > 0;
    const hasMetersOrModifiers = Object.keys(character.meters).length > 0 || character.modifiers.length > 0;

    const handleUseItem = (itemId: string) => {
        if (isPlayer) {
            sendAction('use', null, null, null, itemId);
        }
    };

    const handleDropItem = (itemId: string, ownerId: string) => {
        void dropItem(itemId, 1, ownerId);
    };

    const handleGiveItem = (itemId: string, targetId: string, sourceId: string) => {
        void giveItem(itemId, targetId, 1, sourceId);
        setOpenGiveMenu(null);
    };

    return (
        <div className="flex-1 p-6 overflow-y-auto">
            {/* Header */}
            <div className="flex items-start gap-4 mb-6">
                <div className="w-16 h-16 rounded-full bg-gray-700 flex items-center justify-center">
                    <User className="w-8 h-8 text-gray-400" />
                </div>
                <div className="flex-1">
                    <h2 className="text-2xl font-bold mb-1">{character.name}</h2>
                    {(character.age || character.gender || character.pronouns) && (
                        <p className="text-gray-400">
                            {[
                                character.age,
                                character.gender,
                                character.pronouns?.join('/')
                            ].filter(Boolean).join(' • ')}
                        </p>
                    )}
                    {character.present !== undefined && (
                        <div className="flex items-center gap-2 mt-2">
                            <div className={`w-2 h-2 rounded-full ${character.present ? 'bg-green-500' : 'bg-gray-600'}`} />
                            <span className="text-sm text-gray-400">
                                {character.present ? 'Present' : 'Away'}
                                {character.location && ` (${character.location})`}
                            </span>
                        </div>
                    )}
                </div>
            </div>

            {/* Inventory (Top Priority) */}
            {hasInventory && (
                <div className="mb-6 p-4 bg-gray-800 rounded-lg border border-gray-700">
                    <h3 className="text-lg font-semibold mb-3 text-gray-100 flex items-center gap-2">
                        <Package className="w-5 h-5" />
                        Inventory
                    </h3>
                    <div className="space-y-2 text-sm">
                        {Object.entries(character.inventory).map(([itemId, count]) => {
                            const itemDetails = inventoryDetails[itemId];
                            if (!itemDetails || count <= 0) return null;

                            const usableEffects = Array.isArray(itemDetails.effects_on_use)
                                ? itemDetails.effects_on_use
                                : Array.isArray(itemDetails.on_use)
                                ? itemDetails.on_use
                                : [];
                            const isUsable = isPlayer && usableEffects.length > 0;
                            const canInteract = character.present || isPlayer;

                            return (
                                <div key={itemId} className="flex justify-between items-center group">
                                    <div className="flex items-center gap-2">
                                        <span className="text-lg">{itemDetails.icon || '📦'}</span>
                                        <div>
                                            <span className="capitalize text-gray-200">{itemDetails.name.replace('_', ' ')}</span>
                                            {itemDetails.description && (
                                                <p className="text-xs text-gray-400">{itemDetails.description}</p>
                                            )}
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-2">
                                        {itemDetails.stackable && count > 1 && <span className="text-gray-400">x{count}</span>}

                                        {canInteract && (
                                            <>
                                                {isUsable && (
                                                    <button
                                                        onClick={() => handleUseItem(itemId)}
                                                        disabled={loading}
                                                        className="p-1.5 hover:bg-gray-700 rounded transition-colors disabled:opacity-50"
                                                        title="Use"
                                                    >
                                                        <Hand className="w-4 h-4 text-green-400" />
                                                    </button>
                                                )}
                                                <button
                                                    onClick={() => handleDropItem(itemId, character.id)}
                                                    disabled={loading}
                                                    className="p-1.5 hover:bg-gray-700 rounded transition-colors disabled:opacity-50"
                                                    title="Drop"
                                                >
                                                    <Trash2 className="w-4 h-4 text-red-400" />
                                                </button>
                                                {presentCharacters.length > 0 && (
                                                    <div className="relative">
                                                        <button
                                                            onClick={() => setOpenGiveMenu(openGiveMenu === itemId ? null : itemId)}
                                                            disabled={loading}
                                                            className="p-1.5 hover:bg-gray-700 rounded transition-colors disabled:opacity-50"
                                                            title="Give"
                                                        >
                                                            <ArrowRightLeft className="w-4 h-4 text-blue-400" />
                                                        </button>
                                                        {openGiveMenu === itemId && (
                                                            <div className="absolute right-0 mt-1 bg-gray-900 border border-gray-700 rounded-lg shadow-lg z-10 min-w-[120px]">
                                                                {presentCharacters
                                                                    .filter(c => c.id !== character.id)
                                                                    .map(char => (
                                                                    <button
                                                                        key={char.id}
                                                                        onClick={() => handleGiveItem(itemId, char.id, character.id)}
                                                                        className="w-full px-3 py-2 text-left text-sm hover:bg-gray-800 first:rounded-t-lg last:rounded-b-lg"
                                                                    >
                                                                        {char.name}
                                                                    </button>
                                                                ))}
                                                            </div>
                                                        )}
                                                    </div>
                                                )}
                                            </>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* Wardrobe (Full clothing items owned) */}
            {hasWardrobe && (
                <div className="mb-6 p-4 bg-gray-800 rounded-lg border border-gray-700">
                    <h3 className="text-lg font-semibold mb-3 text-gray-100">Wardrobe</h3>

                    {/* Current outfit */}
                    <div className="mb-4 p-3 bg-gray-900 rounded border border-gray-700">
                        <h4 className="text-sm font-semibold text-gray-400 mb-2">Currently Wearing</h4>
                        <div className="flex items-start gap-2 mb-2 text-sm">
                            {getClothingIcon(character.attire, character.wardrobe_state)}
                            <span className="text-gray-300">
                                {typeof character.attire === 'string' ? character.attire : 'See garment states below'}
                            </span>
                        </div>

                        {/* Garment States */}
                        {character.wardrobe_state && (
                            <div className="mt-3">
                                <h5 className="text-xs font-semibold text-gray-500 mb-2">Garment States</h5>
                                <div className="grid grid-cols-2 gap-2 text-xs">
                                    {Object.entries(character.wardrobe_state)
                                        .filter(([, state]) => typeof state === 'string')
                                        .map(([garment, state]) => (
                                        <div key={garment} className="flex items-center justify-between p-2 bg-gray-800 rounded">
                                            <span className="text-gray-300 capitalize">{formatGarmentName(garment)}</span>
                                            <span className={`px-2 py-0.5 rounded ${
                                                state === 'intact' ? 'bg-green-900/30 text-green-400' :
                                                state === 'displaced' ? 'bg-yellow-900/30 text-yellow-400' :
                                                state === 'removed' ? 'bg-red-900/30 text-red-400' :
                                                'bg-gray-700 text-gray-400'
                                            }`}>
                                                {state}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Owned clothing items */}
                    <div>
                        <h4 className="text-sm font-semibold text-gray-400 mb-2">Owned Clothing</h4>
                        <div className="space-y-1 text-sm">
                            {Object.entries(character.wardrobe).map(([itemId, count]) => {
                                const itemDetails = inventoryDetails[itemId];
                                if (!itemDetails || count <= 0) return null;

                                return (
                                    <div key={itemId} className="flex justify-between items-center p-2 bg-gray-900 rounded">
                                        <div className="flex items-center gap-2">
                                            <span className="text-lg">{itemDetails.icon || '👕'}</span>
                                            <span className="capitalize text-gray-200">{itemDetails.name.replace('_', ' ')}</span>
                                        </div>
                                        {itemDetails.stackable && count > 1 && <span className="text-gray-400">x{count}</span>}
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            )}

            {/* Personality */}
            {hasPersonality && (
                <div className="mb-6 p-4 bg-gray-800 rounded-lg border border-gray-700">
                    <h3 className="text-lg font-semibold mb-3 text-gray-100">Personality</h3>
                    <div className="space-y-2 text-sm">
                        {character.personality!.core_traits && (
                            <div>
                                <span className="text-gray-400">Traits: </span>
                                <span className="text-gray-300">{character.personality!.core_traits}</span>
                            </div>
                        )}
                        {character.personality!.quirks && (
                            <div>
                                <span className="text-gray-400">Quirks: </span>
                                <span className="text-gray-300">{character.personality!.quirks}</span>
                            </div>
                        )}
                        {character.personality!.values && (
                            <div>
                                <span className="text-gray-400">Values: </span>
                                <span className="text-gray-300">{character.personality!.values}</span>
                            </div>
                        )}
                        {character.personality!.fears && (
                            <div>
                                <span className="text-gray-400">Fears: </span>
                                <span className="text-gray-300">{character.personality!.fears}</span>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Appearance */}
            {character.appearance && (
                <div className="mb-6 p-4 bg-gray-800 rounded-lg border border-gray-700">
                    <h3 className="text-lg font-semibold mb-3 text-gray-100">Appearance</h3>
                    <p className="text-sm text-gray-300">{character.appearance}</p>
                </div>
            )}

            {/* Dialogue Style */}
            {character.dialogue_style && (
                <div className="mb-6 p-4 bg-gray-800 rounded-lg border border-gray-700">
                    <h3 className="text-lg font-semibold mb-3 text-gray-100">Dialogue Style</h3>
                    <p className="text-sm text-gray-300">{character.dialogue_style}</p>
                </div>
            )}

            {/* Relationship Gates */}
            {hasGates && (
                <div className="mb-6 p-4 bg-gray-800 rounded-lg border border-gray-700">
                    <h3 className="text-lg font-semibold mb-3 text-gray-100">Relationship Gates</h3>
                    <div className="space-y-3">
                        {character.gates.map(gate => (
                            <div key={gate.id} className="p-3 bg-gray-900 rounded border border-gray-700">
                                <div className="flex items-center gap-2 mb-2">
                                    {gate.allow ? (
                                        <Unlock className="w-4 h-4 text-green-500" />
                                    ) : (
                                        <Lock className="w-4 h-4 text-red-500" />
                                    )}
                                    <span className="font-medium text-gray-200">
                                        {formatMeterId(gate.id)}
                                    </span>
                                    <span className={`text-xs px-2 py-1 rounded ${
                                        gate.allow ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'
                                    }`}>
                                        {gate.allow ? 'Unlocked' : 'Locked'}
                                    </span>
                                </div>
                                {gate.condition && (
                                    <p className="text-xs text-gray-500 mb-2">
                                        Requires: {gate.condition}
                                    </p>
                                )}
                                {gate.allow && gate.acceptance && (
                                    <p className="text-sm text-gray-400 italic">{gate.acceptance}</p>
                                )}
                                {!gate.allow && gate.refusal && (
                                    <p className="text-sm text-gray-400 italic">{gate.refusal}</p>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Current State: Meters & Modifiers */}
            {hasMetersOrModifiers && (
                <div className="mb-6 p-4 bg-gray-800 rounded-lg border border-gray-700">
                    <h3 className="text-lg font-semibold mb-3 text-gray-100">Current State</h3>

                    {/* Meters */}
                    {Object.keys(character.meters).length > 0 && (
                        <div className="mb-4">
                            <h4 className="text-sm font-semibold text-gray-400 mb-2">Meters</h4>
                            <div className="space-y-2 text-sm">
                                {Object.entries(character.meters).map(([meterId, meterData]) => (
                                    <div key={meterId}>
                                        <div className="flex items-center justify-between mb-1">
                                            <div className="flex items-center gap-2">
                                                {renderMeterIcon(meterData.icon)}
                                                <span className="text-gray-300">{formatMeterId(meterId)}</span>
                                            </div>
                                            <span className="font-mono text-gray-200">
                                                {meterData.value}
                                            </span>
                                        </div>
                                        <div className="w-full bg-gray-700 rounded-full h-2">
                                            <div
                                                className={`h-2 rounded-full transition-all ${getMeterColor(meterId)}`}
                                                style={{ width: `${(meterData.value / meterData.max) * 100}%` }}
                                            />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Modifiers */}
                    {character.modifiers.length > 0 && (
                        <div>
                            <h4 className="text-sm font-semibold text-gray-400 mb-2">Active Modifiers</h4>
                            <div className="flex flex-wrap gap-2">
                                {character.modifiers.map(mod => (
                                    <span
                                        key={mod.id}
                                        className="px-3 py-1 text-sm rounded-full bg-blue-900/30 text-blue-300"
                                    >
                                        {mod.id}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Shared Memories (Always show) */}
            <div className="mb-6 p-4 bg-gray-800 rounded-lg border border-gray-700">
                <h3 className="text-lg font-semibold mb-3 text-gray-100">
                    {isPlayer ? 'All Memories' : 'Shared Memories'}
                </h3>
                {character.memories.length > 0 ? (
                    <>
                        <p className="text-sm text-gray-400 mb-4">
                            {isPlayer
                                ? 'Your complete journey so far'
                                : `Memories involving ${character.name}`
                            }
                        </p>

                        {/* Group memories by day */}
                        {(() => {
                            const memoriesByDay = character.memories.reduce((acc, memory) => {
                                const day = memory.day;
                                if (!acc[day]) acc[day] = [];
                                acc[day].push(memory);
                                return acc;
                            }, {} as Record<number, typeof character.memories>);

                            const days = Object.keys(memoriesByDay).map(Number).sort((a, b) => a - b);

                            return (
                                <div className="space-y-4">
                                    {days.map(day => (
                                        <div key={day} className="border-l-2 border-blue-500 pl-4">
                                            <h4 className="text-sm font-semibold text-blue-400 mb-2">
                                                Day {day}
                                            </h4>
                                            <div className="space-y-2">
                                                {memoriesByDay[day].map((memory, idx) => (
                                                    <div key={idx} className="flex items-start gap-2">
                                                        <span className="text-gray-500 mt-1">•</span>
                                                        <p className="text-sm text-gray-300">{memory.text}</p>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            );
                        })()}
                    </>
                ) : (
                    <p className="text-gray-500 italic text-sm">
                        No memories recorded yet. Interact with this character to create shared experiences.
                    </p>
                )}
            </div>
        </div>
    );
}

function getClothingIcon(attire: string | null, wardrobeState?: Record<string, string | any> | null) {
    if (!attire) {
        return <Shirt className="w-4 h-4 text-gray-500 flex-shrink-0" />;
    }

    const lower = attire.toLowerCase();

    if (lower.includes('naked') || lower.includes('nude')) {
        return <Shirt className="w-4 h-4 text-red-400 flex-shrink-0 opacity-50" />;
    }

    if (wardrobeState) {
        const states = Object.values(wardrobeState).filter(s => typeof s === 'string');
        const allRemoved = states.length > 0 && states.every(s => s === 'removed');
        if (allRemoved) {
            return <Shirt className="w-4 h-4 text-red-400 flex-shrink-0 opacity-50" />;
        }
    }

    return <Shirt className="w-4 h-4 text-gray-400 flex-shrink-0" />;
}

function formatGarmentName(garment: string): string {
    // Convert snake_case to Title Case
    return garment
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}
