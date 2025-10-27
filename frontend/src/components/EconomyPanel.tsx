import { useGameStore } from '../stores/gameStore';
import { usePlayer } from '../hooks';
import { Coins } from 'lucide-react';

const formatCurrency = (symbol: string | null | undefined, amount: number | null | undefined) => {
    if (amount === null || amount === undefined) return '—';
    const prefix = symbol ?? '';
    return `${prefix}${amount}`;
};

export const EconomyPanel = () => {
    const { gameState } = useGameStore();
    const player = usePlayer();

    if (!player) return null;

    const economy = gameState?.economy;
    const playerMoneyMeter = player.meters.money;

    if (!economy) {
        return null;
    }

    return (
        <div className="bg-gray-800/50 backdrop-blur border border-gray-700 rounded-lg p-4">
            <h3 className="text-lg font-semibold mb-3 flex items-center gap-2 text-gray-100">
                <Coins className="w-4 h-4" />
                Economy
            </h3>
            <div className="space-y-1 text-sm">
                <div className="flex justify-between text-gray-300">
                    <span>Currency</span>
                    <span className="font-semibold">{economy.currency ?? 'Credits'}</span>
                </div>
                <div className="flex justify-between text-gray-300">
                    <span>Balance</span>
                    <span className="font-semibold">
                        {formatCurrency(economy?.symbol, playerMoneyMeter?.value)}
                    </span>
                </div>
                {economy?.max_money !== null && economy?.max_money !== undefined && (
                    <div className="flex justify-between text-gray-300">
                        <span>Max</span>
                        <span>{formatCurrency(economy?.symbol, economy?.max_money)}</span>
                    </div>
                )}
            </div>
        </div>
    );
};
