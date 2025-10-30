import { useState } from 'react';
import { CharacterFull, ClothingStateValue } from '../services/gameApi';
import { User, Package, Hand, Trash2, ArrowRightLeft, ChevronDown, ChevronRight, Sparkles, Zap, Heart, AlertTriangle, Shirt, Undo2, Settings2 } from 'lucide-react';
import { getMeterColor, renderMeterIcon, formatMeterId } from '../utils';
import { useGameStore } from '../stores/gameStore';
import { usePresentCharacters } from '../hooks';

interface CharacterProfileProps {
    character: CharacterFull;
}

type InventoryCategory = 'item' | 'clothing' | 'outfit' | 'unknown';

const CLOTHING_STATE_COLORS: Record<ClothingStateValue, string> = {
    intact: 'text-emerald-300',
    opened: 'text-amber-300',
    displaced: 'text-purple-300',
    removed: 'text-gray-500',
};
const CLOTHING_STATES: ClothingStateValue[] = ['intact', 'opened', 'displaced', 'removed'];

export function CharacterProfile({ character }: CharacterProfileProps) {
    const isPlayer = character.id === 'player';
    const {
        gameState,
        sendAction,
        dropItem,
        giveItem,
        loading,
        putOnClothing,
        takeOffClothing,
        setClothingState,
        putOnOutfit,
        takeOffOutfit,
    } = useGameStore();
    const presentCharacters = usePresentCharacters();
    const [openGiveMenu, setOpenGiveMenu] = useState<string | null>(null);
    const [openStateMenu, setOpenStateMenu] = useState<string | null>(null);

    const inventoryDetails = gameState?.inventory_details || {};
    const hasInventory = Object.keys(character.inventory).length > 0;
    const hasWardrobe = Object.keys(character.wardrobe).length > 0 || character.outfits.length > 0;

    // State for collapsible outfits
    const [expandedOutfits, setExpandedOutfits] = useState<Set<string>>(new Set());

    const toggleOutfit = (outfitId: string) => {
        setExpandedOutfits(prev => {
            const next = new Set(prev);
            if (next.has(outfitId)) {
                next.delete(outfitId);
            } else {
                next.add(outfitId);
            }
            return next;
        });
    };

    // Helper to check if blocks should be shown
    const hasPersonality = character.personality && (
        character.personality.core_traits ||
        character.personality.quirks ||
        character.personality.values ||
        character.personality.fears
    );
    const hasMetersOrModifiers = Object.keys(character.meters).length > 0 || character.modifiers.length > 0;

    const handleUseItem = (itemId: string) => {
        if (isPlayer) {
            sendAction('use', null, null, null, itemId);
        }
    };

    const handleDropItem = (itemId: string, ownerId: string) => {
        setOpenGiveMenu(null);
        setOpenStateMenu(null);
        void dropItem(itemId, 1, ownerId);
    };

    const handleGiveItem = (itemId: string, targetId: string, sourceId: string) => {
        void giveItem(itemId, targetId, 1, sourceId);
        setOpenGiveMenu(null);
        setOpenStateMenu(null);
    };

    const getClothingState = (clothingId: string): ClothingStateValue | null => {
        const slotToItem = character.wardrobe_state?.slot_to_item ?? {};
        const layers = character.wardrobe_state?.layers ?? {};
        for (const [slot, item] of Object.entries(slotToItem)) {
            if (item === clothingId) {
                const rawState = layers?.[slot];
                if (rawState && (['intact', 'opened', 'displaced', 'removed'] as string[]).includes(rawState)) {
                    return rawState as ClothingStateValue;
                }
            }
        }
        return null;
    };

    const handleWearClothing = (clothingId: string, state?: ClothingStateValue) => {
        setOpenGiveMenu(null);
        setOpenStateMenu(null);
        void putOnClothing(clothingId, character.id, state);
    };

    const handleTakeOffClothingDirect = (clothingId: string) => {
        setOpenGiveMenu(null);
        setOpenStateMenu(null);
        void takeOffClothing(clothingId, character.id);
    };

    const handleClothingStateChange = (clothingId: string, state: ClothingStateValue) => {
        setOpenStateMenu(null);
        void setClothingState(clothingId, state, character.id);
    };

    const handleWearOutfit = (outfitId: string) => {
        setOpenGiveMenu(null);
        setOpenStateMenu(null);
        void putOnOutfit(outfitId, character.id);
    };

    const handleTakeOffOutfitDirect = (outfitId: string) => {
        setOpenGiveMenu(null);
        setOpenStateMenu(null);
        void takeOffOutfit(outfitId, character.id);
    };

    return (
        <div className="flex-1 p-6 overflow-y-auto">
            {/* Header: Name/Age/Gender on left, Money/Presence/Location on right */}
            <div className="flex items-start justify-between gap-4 mb-6">
                <div className="flex items-start gap-4">
                    <div className="w-16 h-16 rounded-full bg-gray-700 flex items-center justify-center flex-shrink-0">
                        <User className="w-8 h-8 text-gray-400" />
                    </div>
                    <div>
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
                    </div>
                </div>
                <div className="flex flex-col items-end gap-2">
                    {/* For player: always show location/zone. For NPCs: show presence + location */}
                    {isPlayer ? (
                        gameState?.snapshot?.location && (
                            <div className="text-right">
                                <div className="text-sm text-gray-400">
                                    {gameState.snapshot.location.name}
                                </div>
                                {gameState.snapshot.location.zone && (
                                    <div className="text-xs text-gray-500 mt-0.5">
                                        {gameState.snapshot.location.zone}
                                    </div>
                                )}
                            </div>
                        )
                    ) : (
                        character.present !== undefined && (
                            <div className="text-right">
                                <div className="flex items-center gap-2 justify-end text-sm text-gray-400">
                                    <span>{character.present ? 'Present' : 'Away'}</span>
                                    <div className={`w-2 h-2 rounded-full ${character.present ? 'bg-green-500' : 'bg-gray-600'}`} />
                                </div>
                                {character.present && gameState?.snapshot?.location && (
                                    <div className="text-xs text-gray-500 mt-0.5">
                                        {gameState.snapshot.location.name}
                                        {gameState.snapshot.location.zone && ` (${gameState.snapshot.location.zone})`}
                                    </div>
                                )}
                                {!character.present && character.location && (
                                    <div className="text-xs text-gray-500 mt-0.5">{character.location}</div>
                                )}
                            </div>
                        )
                    )}
                </div>
            </div>

            {/* General Information: Appearance, Personality, Attire */}
            {(character.appearance || hasPersonality || character.attire) && (
                <div className="mb-6 p-4 bg-gray-800 rounded-lg border border-gray-700">
                    <h3 className="text-lg font-semibold mb-3 text-gray-100">About</h3>
                    <div className="space-y-3 text-sm text-gray-300">
                        {/* Appearance (first, no title) */}
                        {character.appearance && (
                            <p>{character.appearance}</p>
                        )}

                        {/* Attire - what they're currently wearing (second, no title) */}
                        {character.attire && (
                            <p>{character.attire}</p>
                        )}

                        {/* Personality (with icons and labels) */}
                        {hasPersonality && (
                            <div className="space-y-1.5 pt-2">
                                {character.personality!.core_traits && (
                                    <div className="flex items-start gap-2">
                                        <Sparkles className="w-4 h-4 text-purple-400 flex-shrink-0 mt-0.5" />
                                        <div>
                                            <span className="text-gray-400 font-medium">Traits: </span>
                                            <span className="text-gray-300">{character.personality!.core_traits}</span>
                                        </div>
                                    </div>
                                )}
                                {character.personality!.quirks && (
                                    <div className="flex items-start gap-2">
                                        <Zap className="w-4 h-4 text-yellow-400 flex-shrink-0 mt-0.5" />
                                        <div>
                                            <span className="text-gray-400 font-medium">Quirks: </span>
                                            <span className="text-gray-300">{character.personality!.quirks}</span>
                                        </div>
                                    </div>
                                )}
                                {character.personality!.values && (
                                    <div className="flex items-start gap-2">
                                        <Heart className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                                        <div>
                                            <span className="text-gray-400 font-medium">Values: </span>
                                            <span className="text-gray-300">{character.personality!.values}</span>
                                        </div>
                                    </div>
                                )}
                                {character.personality!.fears && (
                                    <div className="flex items-start gap-2">
                                        <AlertTriangle className="w-4 h-4 text-orange-400 flex-shrink-0 mt-0.5" />
                                        <div>
                                            <span className="text-gray-400 font-medium">Fears: </span>
                                            <span className="text-gray-300">{character.personality!.fears}</span>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Current State: Meters & Modifiers */}
            {hasMetersOrModifiers && (
                <div className="mb-6 p-4 bg-gray-800 rounded-lg border border-gray-700">
                    <h3 className="text-lg font-semibold mb-3 text-gray-100">Stats</h3>

                    {/* Meters - compact cards in row (special styling for money) */}
                    {Object.keys(character.meters).length > 0 && (
                        <div className="mb-3">
                            <div className="flex flex-wrap gap-2">
                                {Object.entries(character.meters)
                                    .sort(([aId], [bId]) => {
                                        // For player, money comes first
                                        if (isPlayer) {
                                            if (aId === 'money') return -1;
                                            if (bId === 'money') return 1;
                                        }
                                        return 0;
                                    })
                                    .map(([meterId, meterData]) => {
                                        const isMoney = isPlayer && meterId === 'money';
                                        return (
                                            <div
                                                key={meterId}
                                                className={`flex-1 min-w-[120px] p-2 rounded ${
                                                    isMoney ? 'bg-yellow-900/20 border border-yellow-700/50' : 'bg-gray-900'
                                                }`}
                                            >
                                                <div className="flex items-center justify-between">
                                                    <div className="flex items-center gap-1.5">
                                                        {renderMeterIcon(meterData.icon)}
                                                        <span className={`text-xs ${isMoney ? 'text-yellow-300' : 'text-gray-400'}`}>
                                                            {formatMeterId(meterId)}
                                                        </span>
                                                    </div>
                                                    <span className={`text-sm font-mono ${isMoney ? 'text-yellow-300' : 'text-gray-200'}`}>
                                                        {isMoney ? `$${meterData.value}` : `${meterData.value}/${meterData.max}`}
                                                    </span>
                                                </div>
                                                {!isMoney && (
                                                    <div className="w-full bg-gray-700 rounded-full h-1.5 mt-1.5">
                                                        <div
                                                            className={`h-1.5 rounded-full transition-all ${getMeterColor(meterId)}`}
                                                            style={{ width: `${(meterData.value / meterData.max) * 100}%` }}
                                                        />
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })}
                            </div>
                        </div>
                    )}

                    {/* Modifiers */}
                    {character.modifiers.length > 0 && (
                        <div>
                            <h4 className="text-xs font-semibold text-gray-400 mb-2">Active Modifiers</h4>
                            <div className="flex flex-wrap gap-2">
                                {character.modifiers.map(mod => (
                                    <span
                                        key={mod.id}
                                        className="px-2 py-1 text-xs rounded-full bg-blue-900/30 text-blue-300"
                                    >
                                        {mod.id}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Inventory (Always show, even if empty) */}
            <div className="mb-6 p-4 bg-gray-800 rounded-lg border border-gray-700">
                <h3 className="text-lg font-semibold mb-3 text-gray-100 flex items-center gap-2">
                    <Package className="w-5 h-5" />
                    Inventory
                </h3>
                {hasInventory ? (
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
                            const type = (itemDetails.type as InventoryCategory | undefined) ?? 'item';
                            const isClothing = type === 'clothing';
                            const isOutfit = type === 'outfit';
                            const clothingState = isClothing ? getClothingState(itemId) : null;
                            const isEquippedClothing = Boolean(clothingState);
                            const clothingIconColor = clothingState ? (CLOTHING_STATE_COLORS[clothingState] ?? 'text-sky-300') : 'text-slate-500';
                            const clothingIconClass = isEquippedClothing ? clothingIconColor : 'text-slate-500';
                            const isCurrentOutfit = isOutfit && character.wardrobe_state?.current_outfit === itemId;
                            const outfitIconClass = isCurrentOutfit ? 'text-indigo-300' : 'text-slate-500';
                            const canDrop = canInteract && type !== 'outfit' && !isEquippedClothing;
                            const canGive = canInteract && type !== 'outfit' && !isEquippedClothing && presentCharacters.length > 0;

                            return (
                                <div key={itemId} className="flex items-center justify-between group">
                                    <div
                                        className="flex items-center gap-2"
                                        title={itemDetails.description ?? undefined}
                                    >
                                        {(isClothing || isOutfit) && (
                                            <span className="text-lg">
                                                {isClothing ? (
                                                    <Shirt className={`w-4 h-4 ${clothingIconClass}`} />
                                                ) : (
                                                    <Sparkles className={`w-4 h-4 ${outfitIconClass}`} />
                                                )}
                                            </span>
                                        )}
                                        <span className="capitalize text-gray-200">{itemDetails.name.replace('_', ' ')}</span>
                                        {isOutfit && isCurrentOutfit && (
                                            <span className="text-xs px-2 py-0.5 rounded bg-indigo-900/30 text-indigo-300">Equipped</span>
                                        )}
                                    </div>

                                    <div className="flex items-center gap-1">
                                        {itemDetails.stackable && count > 1 && <span className="text-gray-400">x{count}</span>}

                                        {canInteract && (
                                            <>
                                                {isPlayer && isClothing && (
                                                    isEquippedClothing ? (
                                                        <>
                                                            <button
                                                                onClick={() => handleTakeOffClothingDirect(itemId)}
                                                                disabled={loading}
                                                                className="p-1.5 rounded transition-colors disabled:opacity-50 hover:bg-gray-700 opacity-0 group-hover:opacity-100"
                                                                title="Take off"
                                                            >
                                                                <Undo2 className="w-4 h-4 text-amber-300" />
                                                            </button>
                                                            <div className="relative">
                                                                <button
                                                                    onClick={() => setOpenStateMenu(prev => (prev === itemId ? null : itemId))}
                                                                    disabled={loading}
                                                                    className="p-1.5 rounded transition-colors disabled:opacity-50 hover:bg-gray-700 opacity-0 group-hover:opacity-100"
                                                                    title="Adjust"
                                                                >
                                                                    <Settings2 className="w-4 h-4 text-slate-300" />
                                                                </button>
                                                                {openStateMenu === itemId && (
                                                                    <div className="absolute right-0 mt-2 bg-gray-900 border border-gray-700 rounded shadow-lg z-20 min-w-[120px]">
                                                                        <ul className="py-1 text-xs">
                                                                            {CLOTHING_STATES.map(stateOption => (
                                                                                <li key={`${itemId}-${stateOption}`}>
                                                                                    <button
                                                                                        onClick={() => handleClothingStateChange(itemId, stateOption)}
                                                                                        disabled={loading || clothingState === stateOption}
                                                                                        className={`px-3 py-2 w-full text-left capitalize hover:bg-gray-800 ${clothingState === stateOption ? 'text-emerald-300' : ''}`}
                                                                                    >
                                                                                        {stateOption}
                                                                                    </button>
                                                                                </li>
                                                                            ))}
                                                                        </ul>
                                                                    </div>
                                                                )}
                                                            </div>
                                                        </>
                                                    ) : (
                                                        <button
                                                            onClick={() => handleWearClothing(itemId)}
                                                            disabled={loading}
                                                            className="p-1.5 rounded transition-colors disabled:cursor-not-allowed disabled:opacity-0 hover:bg-gray-700 opacity-0 group-hover:opacity-100"
                                                            title="Wear"
                                                        >
                                                            <Shirt className="w-4 h-4 text-sky-300" />
                                                        </button>
                                                    )
                                                )}

                                                {isPlayer && isOutfit && (
                                                    isCurrentOutfit ? (
                                                        <button
                                                            onClick={() => handleTakeOffOutfitDirect(itemId)}
                                                            disabled={loading}
                                                            className="p-1.5 rounded transition-colors disabled:opacity-50 hover:bg-gray-700 opacity-0 group-hover:opacity-100"
                                                            title="Remove outfit"
                                                        >
                                                            <Undo2 className="w-4 h-4 text-amber-300" />
                                                        </button>
                                                    ) : (
                                                        <button
                                                            onClick={() => handleWearOutfit(itemId)}
                                                            disabled={loading}
                                                            className="p-1.5 rounded transition-colors disabled:opacity-50 hover:bg-gray-700 opacity-0 group-hover:opacity-100"
                                                            title="Wear outfit"
                                                        >
                                                            <Sparkles className="w-4 h-4 text-indigo-300" />
                                                        </button>
                                                    )
                                                )}

                                                {isUsable && (
                                                    <button
                                                        onClick={() => handleUseItem(itemId)}
                                                        disabled={loading}
                                                        className="p-1.5 rounded transition-colors disabled:opacity-50 hover:bg-gray-700 opacity-0 group-hover:opacity-100"
                                                        title="Use"
                                                    >
                                                        <Hand className="w-4 h-4 text-green-400" />
                                                    </button>
                                                )}
                                                <button
                                                    onClick={() => handleDropItem(itemId, character.id)}
                                                    disabled={loading || !canDrop}
                                                    className="p-1.5 rounded transition-colors disabled:cursor-not-allowed disabled:opacity-0 hover:bg-gray-700 opacity-0 group-hover:opacity-100"
                                                    title={canDrop ? 'Drop' : 'Cannot drop while equipped'}
                                                >
                                                    <Trash2 className={`w-4 h-4 ${canDrop ? 'text-red-400' : 'text-gray-600'}`} />
                                                </button>
                                                {canGive && (
                                                    <div className="relative">
                                                        <button
                                                            onClick={() => {
                                                                setOpenStateMenu(null);
                                                                setOpenGiveMenu(openGiveMenu === itemId ? null : itemId);
                                                            }}
                                                            disabled={loading}
                                                            className="p-1.5 rounded transition-colors disabled:opacity-50 hover:bg-gray-700 opacity-0 group-hover:opacity-100"
                                                            title="Give"
                                                        >
                                                            <ArrowRightLeft className="w-4 h-4 text-purple-300" />
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
                ) : (
                    <p className="text-sm text-gray-400 italic">Empty</p>
                )}
            </div>

            {/* Wardrobe (Outfits & Clothing) */}
            {hasWardrobe && (
                <div className="mb-6 p-4 bg-gray-800 rounded-lg border border-gray-700">
                    <h3 className="text-lg font-semibold mb-3 text-gray-100">Wardrobe</h3>

                    {/* Currently Wearing */}
                    <div className="mb-3 p-2 bg-gray-900 rounded border border-gray-700">
                        {/* Attire description */}
                        <div className="text-sm text-gray-300 mb-2">
                            {typeof character.attire === 'string' ? character.attire : 'Mixed items'}
                        </div>

                        {/* Wearing details - Single Row */}
                        <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-xs font-semibold text-gray-400">WEARING:</span>
                            {character.wardrobe_state?.current_outfit && (
                                <span className="text-xs px-2 py-0.5 rounded bg-blue-900/30 text-blue-300 font-medium">
                                    {character.outfits.find(o => o.id === character.wardrobe_state?.current_outfit)?.name || character.wardrobe_state.current_outfit}
                                </span>
                            )}
                            {!character.wardrobe_state?.current_outfit && (
                                <span className="text-xs text-gray-500">Mixed items</span>
                            )}
                            <span className="text-gray-600">•</span>
                            {/* Garment States - show item names with state always visible */}
                            {character.wardrobe_state?.layers && Object.keys(character.wardrobe_state.layers).length > 0 && (
                                <>
                                    {Object.entries(character.wardrobe_state.layers)
                                        .filter(([, state]) => typeof state === 'string')
                                        .map(([slot, state], index, arr) => {
                                            // Get the item_id for this slot
                                            const itemId = character.wardrobe_state?.slot_to_item?.[slot];

                                            // Look up the item name from item_details
                                            const item = itemId ? character.item_details[itemId] : null;
                                            const itemName = item?.name || formatGarmentName(slot);

                                            // State icon/emoji
                                            const stateIcon =
                                                state === 'intact' ? '✓' :
                                                state === 'displaced' ? '↓' :
                                                state === 'removed' ? '✗' :
                                                state === 'opened' ? '◯' : '?';

                                            return (
                                                <span key={slot} className="flex items-center gap-1">
                                                    <span className={`text-xs px-2 py-0.5 rounded ${
                                                        state === 'intact' ? 'bg-green-900/30 text-green-400' :
                                                        state === 'displaced' ? 'bg-yellow-900/30 text-yellow-400' :
                                                        state === 'removed' ? 'bg-red-900/30 text-red-400' :
                                                        state === 'opened' ? 'bg-purple-900/30 text-purple-400' :
                                                        'bg-gray-700 text-gray-400'
                                                    }`}>
                                                        {stateIcon} {itemName}
                                                    </span>
                                                    {index < arr.length - 1 && <span className="text-gray-600 text-xs">•</span>}
                                                </span>
                                            );
                                        })}
                                </>
                            )}
                        </div>
                    </div>

                    {/* Unlocked Outfits - Collapsible Cards in Row */}
                    {character.outfits && character.outfits.length > 0 && (
                        <div className="mb-3">
                            <h4 className="text-xs font-semibold text-gray-500 mb-2">OUTFITS</h4>
                            <div className="flex flex-wrap gap-2">
                                {character.outfits.map(outfit => {
                                    const isComplete = outfit.missing_items.length === 0;
                                    const isWearing = character.wardrobe_state?.current_outfit === outfit.id;
                                    const isExpanded = expandedOutfits.has(outfit.id);
                                    const canControlOutfit = isPlayer;

                                    return (
                                        <div key={outfit.id} className={`bg-gray-900 rounded border min-w-[200px] flex-1 ${
                                            isWearing ? 'border-blue-500' : 'border-gray-700'
                                        }`}>
                                            <div className="flex items-center justify-between px-3 py-2 hover:bg-gray-800/50 transition-colors">
                                                <button
                                                    onClick={() => toggleOutfit(outfit.id)}
                                                    className="flex items-center gap-2"
                                                >
                                                    {isExpanded ? (
                                                        <ChevronDown className="w-3 h-3 text-gray-400" />
                                                    ) : (
                                                        <ChevronRight className="w-3 h-3 text-gray-400" />
                                                    )}
                                                    <span className="text-sm font-medium text-gray-200">{outfit.name}</span>
                                                    {isWearing && (
                                                        <span className="text-xs px-2 py-0.5 rounded bg-blue-900/30 text-blue-300">
                                                            Wearing
                                                        </span>
                                                    )}
                                                    {!isComplete && (
                                                        <span className="text-xs px-2 py-0.5 rounded bg-yellow-900/30 text-yellow-400">
                                                            {outfit.missing_items.length} missing
                                                        </span>
                                                    )}
                                                </button>
                                                {canControlOutfit && (
                                                    <div className="flex items-center gap-1">
                                                        {isWearing ? (
                                                            <button
                                                                onClick={() => handleTakeOffOutfitDirect(outfit.id)}
                                                                disabled={loading}
                                                                className="p-1.5 rounded transition-colors disabled:opacity-50 hover:bg-gray-700"
                                                                title="Remove outfit"
                                                            >
                                                                <Undo2 className="w-4 h-4 text-amber-300" />
                                                            </button>
                                                        ) : (
                                                            <button
                                                                onClick={() => handleWearOutfit(outfit.id)}
                                                                disabled={loading}
                                                                className="p-1.5 rounded transition-colors disabled:opacity-50 hover:bg-gray-700"
                                                                title="Wear outfit"
                                                            >
                                                                <Sparkles className="w-4 h-4 text-indigo-300" />
                                                            </button>
                                                        )}
                                                    </div>
                                                )}
                                            </div>

                                            {/* Outfit items - collapsible */}
                                            {isExpanded && (
                                                <div className="px-3 pb-2 flex flex-wrap gap-1">
                                                    {outfit.items.map(itemId => {
                                                        const itemDetails = character.item_details[itemId];
                                                        const isOwned = outfit.owned_items.includes(itemId);

                                                        return (
                                                            <span
                                                                key={itemId}
                                                                className={`text-xs px-2 py-1 rounded flex items-center gap-1 ${
                                                                    isOwned
                                                                        ? 'bg-gray-800 text-gray-300'
                                                                        : 'bg-gray-800/50 text-gray-500'
                                                                }`}
                                                            >
                                                                {isOwned ? '✓' : '✗'}
                                                                {itemDetails?.name || itemId}
                                                            </span>
                                                        );
                                                    })}
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    {/* Individual clothing items - compact tags */}
                    {Object.keys(character.wardrobe).length > 0 && (
                        <div>
                            <h4 className="text-xs font-semibold text-gray-500 mb-2">CLOTHING ITEMS</h4>
                            <div className="space-y-2 text-sm">
                                {Object.entries(character.wardrobe).map(([itemId, count]) => {
                                    const itemDetails = character.item_details[itemId];
                                    if (!itemDetails || count <= 0) return null;

                                    const clothingState = getClothingState(itemId);
                                    const isEquipped = Boolean(clothingState);
                                    const clothingIconClass = clothingState ? (CLOTHING_STATE_COLORS[clothingState] ?? 'text-sky-300') : 'text-slate-500';
                                    const canControl = isPlayer;

                                    return (
                                        <div key={itemId} className="flex items-center justify-between group">
                                            <div className="flex items-center gap-2">
                                                <Shirt className={`w-4 h-4 ${isEquipped ? clothingIconClass : 'text-slate-500'}`} />
                                                <span className="text-gray-200">{itemDetails.name}</span>
                                            </div>
                                            <div className="flex items-center gap-1">
                                                {count > 1 && <span className="text-gray-500">×{count}</span>}
                                                {canControl && (
                                                    <>
                                                        {isEquipped ? (
                                                            <>
                                                                <button
                                                                    onClick={() => handleTakeOffClothingDirect(itemId)}
                                                                    disabled={loading}
                                                                    className="p-1.5 rounded transition-colors disabled:opacity-50 hover:bg-gray-700 opacity-0 group-hover:opacity-100"
                                                                    title="Take off"
                                                                >
                                                                    <Undo2 className="w-4 h-4 text-amber-300" />
                                                                </button>
                                                                <div className="relative">
                                                                    <button
                                                                        onClick={() => setOpenStateMenu(prev => (prev === itemId ? null : itemId))}
                                                                        disabled={loading}
                                                                        className="p-1.5 rounded transition-colors disabled:opacity-50 hover:bg-gray-700 opacity-0 group-hover:opacity-100"
                                                                        title="Adjust"
                                                                    >
                                                                        <Settings2 className="w-4 h-4 text-slate-300" />
                                                                    </button>
                                                                    {openStateMenu === itemId && (
                                                                        <div className="absolute right-0 mt-2 bg-gray-900 border border-gray-700 rounded shadow-lg z-20 min-w-[120px]">
                                                                            <ul className="py-1 text-xs">
                                                                                {CLOTHING_STATES.map(stateOption => (
                                                                                    <li key={`${itemId}-${stateOption}`}>
                                                                                        <button
                                                                                            onClick={() => handleClothingStateChange(itemId, stateOption)}
                                                                                            disabled={loading || clothingState === stateOption}
                                                                                            className={`px-3 py-2 w-full text-left capitalize hover:bg-gray-800 ${clothingState === stateOption ? 'text-emerald-300' : ''}`}
                                                                                        >
                                                                                            {stateOption}
                                                                                        </button>
                                                                                    </li>
                                                                                ))}
                                                                            </ul>
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            </>
                                                        ) : (
                                                            <button
                                                                onClick={() => handleWearClothing(itemId)}
                                                                disabled={loading}
                                                                className="p-1.5 rounded transition-colors disabled:opacity-50 hover:bg-gray-700 opacity-0 group-hover:opacity-100"
                                                                title="Wear"
                                                            >
                                                                <Shirt className="w-4 h-4 text-sky-300" />
                                                            </button>
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

function formatGarmentName(garment: string): string {
    // Convert snake_case to Title Case
    return garment
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}
