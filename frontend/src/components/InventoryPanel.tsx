import { useMemo, useState } from 'react';
import { useGameStore } from '../stores/gameStore';
import { usePlayer, usePresentCharacters } from '../hooks';
import { Package, Hand, Trash2, ArrowRightLeft } from 'lucide-react';

export const InventoryPanel = () => {
    const { gameState, sendAction, dropItem, giveItem, loading } = useGameStore();
    const player = usePlayer();
    const characters = usePresentCharacters();

    const presentCharacters = useMemo(() => {
        return characters.map(char => ({
            id: char.id,
            name: char.name ?? char.id
        }));
    }, [characters]);

    const [openGiveMenu, setOpenGiveMenu] = useState<string | null>(null);

    if (!player) {
        return null;
    }

    const playerInventory = player.inventory;
    const inventoryDetails = gameState?.inventory_details;

    if (!inventoryDetails || Object.keys(playerInventory).length === 0) {
        return (
            <div className="bg-gray-800/50 backdrop-blur border border-gray-700 rounded-lg p-4">
                <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                    <Package className="w-4 h-4" />
                    Inventory
                </h3>
                <p className="text-gray-500 text-sm">Empty</p>
            </div>
        );
    }

    const handleUseItem = (itemId: string) => {
        sendAction('use', null, null, null, itemId);
    };

    const handleDropItem = (itemId: string) => {
        void dropItem(itemId);
    };

    return (
        <div className="bg-gray-800/50 backdrop-blur border border-gray-700 rounded-lg p-4">
            <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                <Package className="w-4 h-4" />
                Inventory
            </h3>
            <div className="space-y-2 text-sm">
                {Object.entries(playerInventory).map(([itemId, count]) => {
                    const itemDetails = inventoryDetails[itemId];
                    if (!itemDetails || count <= 0) return null;

                    const usableEffects = Array.isArray(itemDetails.effects_on_use)
                        ? itemDetails.effects_on_use
                        : Array.isArray(itemDetails.on_use)
                        ? itemDetails.on_use
                        : [];
                    const isUsable = usableEffects.length > 0;

                    return (
                        <div key={itemId} className="flex justify-between items-center group">
                            <div className="flex items-center gap-2">
                                <span className="text-lg">{itemDetails.icon || '📦'}</span>
                                <div>
                                    <span className="capitalize text-gray-200">{itemDetails.name.replace('_', ' ')}</span>
                                    <p className="text-xs text-gray-400">{itemDetails.description}</p>
                                </div>
                            </div>

                            <div className="flex items-center gap-2">
                                {itemDetails.stackable && <span className="text-gray-400">x{count}</span>}
                                {isUsable && (
                                    <button
                                        onClick={() => handleUseItem(itemId)}
                                        disabled={loading}
                                        className="px-2 py-1 bg-green-600/20 text-green-300 text-xs rounded
                                                   hover:bg-green-600/40 disabled:opacity-50 disabled:cursor-not-allowed
                                                   transition-opacity opacity-0 group-hover:opacity-100"
                                    >
                                        <Hand className="w-3 h-3 inline mr-1"/>
                                        Use
                                    </button>
                                )}
                                <button
                                    onClick={() => handleDropItem(itemId)}
                                    disabled={loading}
                                    className="px-2 py-1 bg-red-600/20 text-red-300 text-xs rounded
                                               hover:bg-red-600/40 disabled:opacity-50 disabled:cursor-not-allowed
                                               transition-opacity opacity-0 group-hover:opacity-100"
                                >
                                    <Trash2 className="w-3 h-3 inline mr-1"/>
                                    Drop
                                </button>
                                {presentCharacters.length > 0 && (
                                    <div className="relative">
                                        <button
                                            onClick={() => setOpenGiveMenu(prev => (prev === itemId ? null : itemId))}
                                            disabled={loading}
                                            className="px-2 py-1 bg-purple-600/20 text-purple-200 text-xs rounded
                                                       hover:bg-purple-600/40 disabled:opacity-50 disabled:cursor-not-allowed
                                                       transition-opacity opacity-0 group-hover:opacity-100 flex items-center gap-1"
                                        >
                                            <ArrowRightLeft className="w-3 h-3" /> Give
                                        </button>
                                        {openGiveMenu === itemId && (
                                            <div className="absolute right-0 mt-2 bg-gray-900 border border-gray-700 rounded shadow-lg z-10">
                                                <ul className="py-1 text-xs">
                                                    {presentCharacters.map(char => (
                                                        <li key={`${itemId}-${char}`}> 
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
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};
