// frontend/src/components/InventoryPanel.tsx
import { useGameStore } from '../stores/gameStore';
import { Package, Hand } from 'lucide-react';

export const InventoryPanel = () => {
    const { gameState, sendAction, loading } = useGameStore();

    if (
        !gameState ||
        !gameState.inventory ||
        !gameState.inventory_details ||
        Object.keys(gameState.inventory).length === 0
    ) {
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

    return (
        <div className="bg-gray-800/50 backdrop-blur border border-gray-700 rounded-lg p-4">
            <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                <Package className="w-4 h-4" />
                Inventory
            </h3>
            <div className="space-y-2 text-sm">
                {Object.entries(gameState.inventory).map(([itemId, count]) => {
                    const itemDetails = gameState.inventory_details[itemId];
                    if (!itemDetails || count <= 0) return null;

                    const isUsable = itemDetails.effects_on_use && itemDetails.effects_on_use.length > 0;

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
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};