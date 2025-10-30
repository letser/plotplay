import { useMemo, useState } from 'react';
import { Package, Hand, Trash2, ArrowRightLeft, Inbox, Shirt, Undo2, Sparkles, Settings2 } from 'lucide-react';
import { useGameStore } from '../stores/gameStore';
import { useLocation, usePlayer, usePresentCharacters } from '../hooks';
import type { Item, ClothingStateValue } from '../services/gameApi';

type InventoryCategory = 'item' | 'clothing' | 'outfit' | 'unknown';

interface InventoryEntry {
    id: string;
    count: number;
    type: InventoryCategory;
    detail: Item;
}

const CATEGORY_ORDER: InventoryCategory[] = ['item', 'clothing', 'outfit', 'unknown'];

const TYPE_META: Record<InventoryCategory, { label: string; icon: string }> = {
    item: { label: 'Items', icon: '📦' },
    clothing: { label: 'Clothing', icon: '🧥' },
    outfit: { label: 'Outfits', icon: '👗' },
    unknown: { label: 'Other', icon: '❔' },
};

const CLOTHING_STATES: ClothingStateValue[] = ['intact', 'opened', 'displaced', 'removed'];
const CLOTHING_STATE_COLORS: Record<ClothingStateValue, string> = {
    intact: 'text-emerald-300',
    opened: 'text-amber-300',
    displaced: 'text-purple-300',
    removed: 'text-gray-500',
};

const formatName = (value: string) => value.replace(/_/g, ' ');

const compareEntries = (a: InventoryEntry, b: InventoryEntry) => {
    const typeRank = CATEGORY_ORDER.indexOf(a.type) - CATEGORY_ORDER.indexOf(b.type);
    if (typeRank !== 0) return typeRank;
    return a.detail.name.localeCompare(b.detail.name);
};

export const InventoryPanel = () => {
    const {
        gameState,
        sendAction,
        dropItem,
        giveItem,
        takeItem,
        putOnClothing,
        takeOffClothing,
        setClothingState,
        putOnOutfit,
        takeOffOutfit,
        loading
    } = useGameStore();
    const player = usePlayer();
    const characters = usePresentCharacters();
    const locationInfo = useLocation();

    const presentCharacters = useMemo(() => {
        return characters.filter(char => char.id !== 'player').map(char => ({
            id: char.id,
            name: char.name ?? char.id,
        }));
    }, [characters]);

    const [openGiveMenu, setOpenGiveMenu] = useState<string | null>(null);
    const [openStateMenu, setOpenStateMenu] = useState<string | null>(null);

    if (!player) {
        return null;
    }

    const playerInventory = player.inventory ?? {};
    const locationInventory = gameState?.location_inventory ?? {};
    const inventoryDetails = gameState?.inventory_details ?? {};
    const locationInventoryDetails = gameState?.location_inventory_details ?? {};
    const playerOutfits = gameState?.player_outfits ?? [];
    const playerCurrentOutfit = gameState?.player_current_outfit ?? null;
    const equippedClothingIds = useMemo(() => new Set(gameState?.player_equipped_clothing ?? []), [gameState?.player_equipped_clothing]);
    const wardrobeState = player.wardrobe_state as { layers?: Record<string, string>; slot_to_item?: Record<string, string> } | undefined;

    const mergedDetails = useMemo<Record<string, Item>>(() => ({
        ...locationInventoryDetails,
        ...inventoryDetails,
    }), [inventoryDetails, locationInventoryDetails]);

    const buildEntries = (inventory: Record<string, number>): InventoryEntry[] => {
        const entries: InventoryEntry[] = [];

        Object.entries(inventory).forEach(([itemId, count]) => {
            if (count <= 0) return;

            const detail = mergedDetails[itemId] ?? {
                id: itemId,
                name: formatName(itemId),
                description: null,
                icon: null,
                stackable: false,
                type: 'unknown',
            };

            const type = (detail.type as InventoryCategory | undefined) ?? 'item';
            const icon = detail.icon ?? TYPE_META[type].icon;

            entries.push({
                id: itemId,
                count,
                type,
                detail: {
                    ...detail,
                    id: detail.id ?? itemId,
                    name: detail.name ?? formatName(itemId),
                    description: detail.description ?? null,
                    icon,
                    stackable: detail.stackable ?? false,
                    type,
                },
            });
        });

        return entries.sort(compareEntries);
    };

    const playerEntries = useMemo(() => {
        const entries = buildEntries(playerInventory);
        playerOutfits.forEach(outfitId => {
            if (entries.some(entry => entry.id === outfitId)) {
                return;
            }
            const detail = mergedDetails[outfitId];
            if (!detail) {
                return;
            }
            entries.push({
                id: outfitId,
                count: 1,
                type: 'outfit',
                detail: {
                    ...detail,
                    id: detail.id ?? outfitId,
                    name: detail.name ?? formatName(outfitId),
                    icon: detail.icon ?? TYPE_META.outfit.icon,
                    stackable: false,
                    type: 'outfit',
                },
            });
        });
        return entries.sort(compareEntries);
    }, [playerInventory, playerOutfits, mergedDetails]);
    const locationEntries = useMemo(() => buildEntries(locationInventory), [locationInventory, mergedDetails]);

    const handleUseItem = (itemId: string) => {
        setOpenGiveMenu(null);
        sendAction('use', null, null, null, itemId);
    };

    const handleDropItem = (itemId: string) => {
        setOpenGiveMenu(null);
        void dropItem(itemId);
    };

    const handleTakeItem = (itemId: string) => {
        setOpenGiveMenu(null);
        void takeItem(itemId);
    };

    const getClothingState = (clothingId: string): ClothingStateValue | null => {
        if (!wardrobeState) return null;
        const slotToItem = wardrobeState.slot_to_item ?? {};
        const layers = wardrobeState.layers ?? {};
        for (const [slot, item] of Object.entries(slotToItem)) {
            if (item === clothingId) {
                const rawState = layers?.[slot];
                if (rawState && (CLOTHING_STATES as string[]).includes(rawState)) {
                    return rawState as ClothingStateValue;
                }
            }
        }
        return null;
    };

    const handleWearClothing = (clothingId: string, state?: ClothingStateValue) => {
        setOpenGiveMenu(null);
        setOpenStateMenu(null);
        void putOnClothing(clothingId, 'player', state);
    };

    const handleTakeOffClothing = (clothingId: string) => {
        setOpenGiveMenu(null);
        setOpenStateMenu(null);
        void takeOffClothing(clothingId);
    };

    const handleClothingStateChange = (clothingId: string, state: ClothingStateValue) => {
        setOpenStateMenu(null);
        void setClothingState(clothingId, state);
    };

    const handleWearOutfit = (outfitId: string) => {
        setOpenGiveMenu(null);
        setOpenStateMenu(null);
        void putOnOutfit(outfitId);
    };

    const handleTakeOffOutfit = (outfitId: string) => {
        setOpenGiveMenu(null);
        setOpenStateMenu(null);
        void takeOffOutfit(outfitId);
    };

    const renderRow = (entry: InventoryEntry, context: 'player' | 'location') => {
        const { id: itemId, count, detail, type } = entry;
        const itemDescription = detail.description ?? undefined;
        const isStackable = detail.stackable ?? false;
        const showCount = isStackable || count > 1;

        const usableEffects = Array.isArray(detail.effects_on_use)
            ? detail.effects_on_use
            : Array.isArray(detail.on_use)
            ? detail.on_use
            : [];
        const isUsable = context === 'player' && type === 'item' && usableEffects.length > 0;

        const isClothing = type === 'clothing';
        const isOutfit = type === 'outfit';
        const isEquippedClothing = isClothing && equippedClothingIds.has(itemId);
        const clothingState = isClothing ? getClothingState(itemId) : null;
        const isCurrentOutfit = isOutfit && playerCurrentOutfit === itemId;
        const canDrop = context === 'player' && type !== 'outfit' && !(isClothing && isEquippedClothing);

        const clothingIconColor = clothingState ? (CLOTHING_STATE_COLORS[clothingState] ?? 'text-sky-300') : 'text-slate-500';
        const clothingIconClass = isEquippedClothing ? clothingIconColor : 'text-slate-500';
        const outfitIconClass = isCurrentOutfit ? 'text-indigo-300' : 'text-slate-500';

        const canGive = context === 'player' && !isOutfit && !(isClothing && isEquippedClothing) && presentCharacters.length > 0;

        return (
            <div key={itemId} className="flex items-center justify-between group">
                <div
                    className="flex items-center gap-2"
                    title={itemDescription}
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
                    <span className="capitalize text-gray-200">{detail.name}</span>
                    {isOutfit && isCurrentOutfit && (
                        <span className="text-xs px-2 py-0.5 rounded bg-indigo-900/30 text-indigo-300">Equipped</span>
                    )}
                </div>

                <div className="flex items-center gap-1">
                    {showCount && <span className="text-gray-400">x{count}</span>}

                    {context === 'player' ? (
                        <>
                            {isClothing && (
                                <>
                                    {isEquippedClothing ? (
                                        <>
                                            <button
                                                onClick={() => handleTakeOffClothing(itemId)}
                                                disabled={loading}
                                                className="p-1.5 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                                                           hover:bg-gray-700 opacity-0 group-hover:opacity-100"
                                                title="Take off"
                                            >
                                                <Undo2 className="w-4 h-4 text-amber-300" />
                                            </button>
                                            <div className="relative">
                                                <button
                                                    onClick={() => {
                                                        setOpenGiveMenu(null);
                                                        setOpenStateMenu(prev => (prev === itemId ? null : itemId));
                                                    }}
                                                    disabled={loading}
                                                    className="p-1.5 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                                                               hover:bg-gray-700 opacity-0 group-hover:opacity-100"
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
                                            className="p-1.5 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                                                       hover:bg-gray-700 opacity-0 group-hover:opacity-100"
                                            title="Wear"
                                        >
                                            <Shirt className="w-4 h-4 text-sky-300" />
                                        </button>
                                    )}
                                </>
                            )}

                            {isOutfit && (
                                isCurrentOutfit ? (
                                    <button
                                        onClick={() => handleTakeOffOutfit(itemId)}
                                        disabled={loading}
                                        className="p-1.5 rounded transition-colors disabled:cursor-not-allowed disabled:opacity-0
                                                   hover:bg-gray-700 opacity-0 group-hover:opacity-100"
                                        title="Remove outfit"
                                    >
                                        <Undo2 className="w-4 h-4 text-amber-300" />
                                    </button>
                                ) : (
                                    <button
                                        onClick={() => handleWearOutfit(itemId)}
                                        disabled={loading}
                                        className="p-1.5 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                                                   hover:bg-gray-700 opacity-0 group-hover:opacity-100"
                                        title="Wear outfit"
                                    >
                                        <Sparkles className="w-4 h-4 text-indigo-300" />
                                    </button>
                                )
                            )}

                            {!isClothing && !isOutfit && isUsable && (
                                <button
                                    onClick={() => handleUseItem(itemId)}
                                    disabled={loading}
                                    className="p-1.5 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                                               hover:bg-gray-700 opacity-0 group-hover:opacity-100"
                                    title="Use"
                                >
                                    <Hand className="w-4 h-4 text-green-400" />
                                </button>
                            )}

                            {context === 'player' && type !== 'outfit' && (
                                <button
                                    onClick={() => handleDropItem(itemId)}
                                    disabled={loading || !canDrop}
                                    className="p-1.5 rounded transition-colors disabled:cursor-not-allowed disabled:opacity-0
                                               hover:bg-gray-700 opacity-0 group-hover:opacity-100"
                                    title={canDrop ? 'Drop' : 'Cannot drop while equipped'}
                                >
                                    <Trash2 className={`w-4 h-4 ${canDrop ? 'text-red-400' : 'text-gray-600'}`} />
                                </button>
                            )}

                            {canGive && (
                                <div className="relative">
                                    <button
                                        onClick={() => {
                                            setOpenStateMenu(null);
                                            setOpenGiveMenu(prev => (prev === itemId ? null : itemId));
                                        }}
                                        disabled={loading}
                                        className="p-1.5 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                                                   hover:bg-gray-700 opacity-0 group-hover:opacity-100"
                                        title="Give"
                                    >
                                        <ArrowRightLeft className="w-4 h-4 text-purple-300" />
                                    </button>
                                    {openGiveMenu === itemId && (
                                        <div className="absolute right-0 mt-2 bg-gray-900 border border-gray-700 rounded shadow-lg z-10">
                                            <ul className="py-1 text-xs">
                                                {presentCharacters.map(char => (
                                                    <li key={`${itemId}-${char.id}`}>
                                                        <button
                                                            onClick={() => {
                                                                setOpenGiveMenu(null);
                                                                void giveItem(itemId, char.id);
                                                            }}
                                                            className="px-3 py-2 w-full text-left capitalize hover:bg-gray-800"
                                                        >
                                                            {char.name}
                                                        </button>
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            )}
                        </>
                    ) : (
                        <button
                            onClick={() => handleTakeItem(itemId)}
                            disabled={loading}
                            className="p-1.5 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                                       hover:bg-gray-700 opacity-0 group-hover:opacity-100"
                            title="Take"
                        >
                            <Inbox className="w-4 h-4 text-blue-300" />
                        </button>
                    )}
                </div>
            </div>
        );
    };

    const renderSection = (
        title: string,
        entries: InventoryEntry[],
        emptyLabel: string,
        context: 'player' | 'location',
        subtitle?: string,
    ) => {
        const totalUnique = entries.length;
        const activeCategories = CATEGORY_ORDER.filter(category =>
            entries.some(entry => entry.type === category)
        );
        const showGroupHeaders = activeCategories.length > 1;

        return (
            <div>
                <div className="flex items-start justify-between mb-2">
                    <div>
                        <span className="text-sm font-semibold text-gray-200">{title}</span>
                        {subtitle && (
                            <div className="text-xs text-gray-500">{subtitle}</div>
                        )}
                    </div>
                    {totalUnique > 0 && (
                        <span className="text-xs text-gray-500">
                            {totalUnique} {totalUnique === 1 ? 'item' : 'items'}
                        </span>
                    )}
                </div>

                {totalUnique === 0 ? (
                    <p className="text-xs text-gray-500">{emptyLabel}</p>
                ) : (
                    <div className="space-y-3">
                        {activeCategories.map(category => {
                            const items = entries.filter(entry => entry.type === category);
                            if (items.length === 0) return null;

                            return (
                                <div key={category}>
                                    {showGroupHeaders && (
                                        <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-gray-500 mb-1">
                                            <span>{TYPE_META[category].icon}</span>
                                            <span>{TYPE_META[category].label}</span>
                                            <span className="text-gray-700">•</span>
                                            <span className="text-gray-500 lowercase">{items.length}</span>
                                        </div>
                                    )}
                                    <div className="space-y-2">
                                        {items.map(entry => renderRow(entry, context))}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="bg-gray-800/50 backdrop-blur border border-gray-700 rounded-lg p-4">
            <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                <Package className="w-4 h-4" />
                Inventory
            </h3>

            <div className="space-y-4 text-sm">
                {renderSection(
                    'Your Pack',
                    playerEntries,
                    'Empty',
                    'player'
                )}
                {renderSection(
                    'At Location',
                    locationEntries,
                    'Nothing here',
                    'location',
                    locationInfo?.name ?? undefined
                )}
            </div>
        </div>
    );
};
