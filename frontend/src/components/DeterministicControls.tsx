import { useState, useMemo } from 'react';
import { useGameStore } from '../stores/gameStore';
import { usePresentCharacters } from '../hooks';
import { Store, PackagePlus, PackageMinus, ShoppingCart, ArrowRightLeft, ToggleRight, ToggleLeft } from 'lucide-react';

export const DeterministicControls = () => {
    const {
        takeItem,
        dropItem,
        purchaseItem,
        sellItem,
        giveItem,
        loading,
        deterministicActionsEnabled,
        setDeterministicActionsEnabled,
    } = useGameStore();

    const characters = usePresentCharacters();

    const [takeItemId, setTakeItemId] = useState('');
    const [dropItemId, setDropItemId] = useState('');
    const [giveItemId, setGiveItemId] = useState('');
    const [giveTarget, setGiveTarget] = useState('');
    const [buyItemId, setBuyItemId] = useState('');
    const [buyPrice, setBuyPrice] = useState('');
    const [sellItemId, setSellItemId] = useState('');
    const [sellPrice, setSellPrice] = useState('');

    const presentCharacters = useMemo(() => {
        return characters.map(char => ({
            id: char.id,
            name: char.name ?? char.id
        }));
    }, [characters]);

    if (characters.length === 0 && !presentCharacters.length) {
        // Still show panel for take/drop/buy/sell even if no characters present
    }

    return (
        <div className="bg-gray-800/50 backdrop-blur border border-gray-700 rounded-lg p-4 space-y-4">
            <h3 className="text-lg font-semibold text-gray-100 flex items-center gap-2">
                <Store className="w-4 h-4" />
                Quick Utilities
            </h3>

            <div className="flex items-center justify-between text-sm bg-gray-900 border border-gray-700 rounded p-2">
                <div className="flex flex-col">
                    <span className="text-gray-200 font-medium">Skip AI narration</span>
                    <span className="text-xs text-gray-400">Apply deterministic endpoints when available.</span>
                </div>
                <button
                    onClick={() => setDeterministicActionsEnabled(!deterministicActionsEnabled)}
                    className={`px-3 py-1 rounded flex items-center gap-2 transition-colors ${
                        deterministicActionsEnabled ? 'bg-green-600/40 text-green-200' : 'bg-gray-700 text-gray-300'
                    }`}
                >
                    {deterministicActionsEnabled ? <ToggleRight className="w-5 h-5" /> : <ToggleLeft className="w-5 h-5" />}
                    <span>{deterministicActionsEnabled ? 'On' : 'Off'}</span>
                </button>
            </div>

            <div className="space-y-3 text-sm">
                <form
                    onSubmit={(e) => {
                        e.preventDefault();
                        if (takeItemId.trim()) {
                            void takeItem(takeItemId.trim());
                            setTakeItemId('');
                        }
                    }}
                    className="flex gap-2"
                >
                    <input
                        value={takeItemId}
                        onChange={(e) => setTakeItemId(e.target.value)}
                        placeholder="Item ID to take"
                        className="flex-1 px-3 py-2 bg-gray-900 border border-gray-700 rounded"
                    />
                    <button
                        type="submit"
                        disabled={loading || !takeItemId.trim()}
                        className="px-3 py-2 bg-blue-600/30 text-blue-200 rounded hover:bg-blue-600/50 disabled:opacity-50"
                    >
                        <PackagePlus className="w-4 h-4" />
                    </button>
                </form>

                <form
                    onSubmit={(e) => {
                        e.preventDefault();
                        if (dropItemId.trim()) {
                            void dropItem(dropItemId.trim());
                            setDropItemId('');
                        }
                    }}
                    className="flex gap-2"
                >
                    <input
                        value={dropItemId}
                        onChange={(e) => setDropItemId(e.target.value)}
                        placeholder="Item ID to drop"
                        className="flex-1 px-3 py-2 bg-gray-900 border border-gray-700 rounded"
                    />
                    <button
                        type="submit"
                        disabled={loading || !dropItemId.trim()}
                        className="px-3 py-2 bg-red-600/30 text-red-200 rounded hover:bg-red-600/50 disabled:opacity-50"
                    >
                        <PackageMinus className="w-4 h-4" />
                    </button>
                </form>

                <form
                    onSubmit={(e) => {
                        e.preventDefault();
                        if (giveItemId.trim() && giveTarget.trim()) {
                            void giveItem(giveItemId.trim(), giveTarget.trim());
                            setGiveItemId('');
                        }
                    }}
                    className="flex gap-2"
                >
                    <input
                        value={giveItemId}
                        onChange={(e) => setGiveItemId(e.target.value)}
                        placeholder="Item ID to give"
                        className="flex-1 px-3 py-2 bg-gray-900 border border-gray-700 rounded"
                    />
                    <select
                        value={giveTarget}
                        onChange={(e) => setGiveTarget(e.target.value)}
                        className="px-3 py-2 bg-gray-900 border border-gray-700 rounded text-gray-200"
                    >
                        <option value="">Choose target...</option>
                        {presentCharacters.map(char => (
                            <option key={char.id} value={char.id} className="capitalize">
                                {char.name}
                            </option>
                        ))}
                    </select>
                    <button
                        type="submit"
                        disabled={loading || !giveItemId.trim() || !giveTarget.trim()}
                        className="px-3 py-2 bg-purple-600/30 text-purple-200 rounded hover:bg-purple-600/50 disabled:opacity-50"
                    >
                        <ArrowRightLeft className="w-4 h-4" />
                    </button>
                </form>

                <form
                    onSubmit={(e) => {
                        e.preventDefault();
                        if (buyItemId.trim()) {
                            const price = buyPrice ? Number(buyPrice) : undefined;
                            void purchaseItem(buyItemId.trim(), 1, price);
                            setBuyItemId('');
                            setBuyPrice('');
                        }
                    }}
                    className="flex gap-2"
                >
                    <input
                        value={buyItemId}
                        onChange={(e) => setBuyItemId(e.target.value)}
                        placeholder="Item ID to buy"
                        className="flex-1 px-3 py-2 bg-gray-900 border border-gray-700 rounded"
                    />
                    <input
                        value={buyPrice}
                        onChange={(e) => setBuyPrice(e.target.value)}
                        placeholder="Price"
                        className="w-24 px-3 py-2 bg-gray-900 border border-gray-700 rounded"
                    />
                    <button
                        type="submit"
                        disabled={loading || !buyItemId.trim()}
                        className="px-3 py-2 bg-green-600/30 text-green-200 rounded hover:bg-green-600/50 disabled:opacity-50"
                    >
                        <ShoppingCart className="w-4 h-4" />
                    </button>
                </form>

                <form
                    onSubmit={(e) => {
                        e.preventDefault();
                        if (sellItemId.trim()) {
                            const price = sellPrice ? Number(sellPrice) : undefined;
                            void sellItem(sellItemId.trim(), 1, price);
                            setSellItemId('');
                            setSellPrice('');
                        }
                    }}
                    className="flex gap-2"
                >
                    <input
                        value={sellItemId}
                        onChange={(e) => setSellItemId(e.target.value)}
                        placeholder="Item ID to sell"
                        className="flex-1 px-3 py-2 bg-gray-900 border border-gray-700 rounded"
                    />
                    <input
                        value={sellPrice}
                        onChange={(e) => setSellPrice(e.target.value)}
                        placeholder="Price"
                        className="w-24 px-3 py-2 bg-gray-900 border border-gray-700 rounded"
                    />
                    <button
                        type="submit"
                        disabled={loading || !sellItemId.trim()}
                        className="px-3 py-2 bg-yellow-600/30 text-yellow-200 rounded hover:bg-yellow-600/50 disabled:opacity-50"
                    >
                        <ShoppingCart className="w-4 h-4 transform scale-x-[-1]" />
                    </button>
                </form>
            </div>
        </div>
    );
};
