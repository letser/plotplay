import { useGameStore } from '../stores/gameStore';
import { useSnapshot, useLocation, useTimeInfo } from '../hooks';
import { formatLocationName } from '../utils';
import { ErrorBoundary } from './ErrorBoundary';
import { NarrativePanel } from './NarrativePanel';
import { PlayerPanel } from './PlayerPanel';
import { CharacterPanel } from './CharacterPanel';
import { FlagsPanel } from './FlagsPanel';
import { ChoicePanel } from './ChoicePanel';
import { InventoryPanel } from './InventoryPanel';
import { DeterministicControls } from './DeterministicControls';
import { DebugPanel } from './DebugPanel';
import { MapPin, Clock, Calendar, Layers, Shield, Coins } from 'lucide-react';

export const GameInterface = () => {
    const {
        currentGame,
        gameState,
        turnLog,
        choices,
        resetGame
    } = useGameStore();

    const snapshot = useSnapshot();
    const location = useLocation();
    const timeInfo = useTimeInfo();

    // Early return if no snapshot available
    if (!snapshot || !location || !timeInfo) return null;

    const locationName = location.name;
    const timeClock = timeInfo.time_hhmm;
    const timeSlot = timeInfo.slot;
    const timeMode = timeInfo.mode ?? 'slots';
    const dayNumber = timeInfo.day;
    const zoneName = location.zone ?? 'unknown zone';
    const privacy = location.privacy;

    // Economy data
    const economy = gameState?.economy;
    const playerMoney = economy?.player_money;
    const currencySymbol = economy?.symbol ?? '$';

    return (
        <div className="max-w-7xl mx-auto p-4 pb-24">
            {/* Header */}
            <div className="bg-gray-800 rounded-lg p-4 mb-4 flex justify-between items-center">
                <h1 className="text-2xl font-bold">{currentGame?.title}</h1>

                <div className="flex items-center gap-6 text-sm">
                    {/* Zone */}
                    <div className="flex items-center gap-2">
                        <Layers className="w-4 h-4" />
                        <span>{formatLocationName(zoneName)}</span>
                    </div>

                    {/* Location */}
                    <div className="flex items-center gap-2">
                        <MapPin className="w-4 h-4" />
                        <span>{formatLocationName(locationName)}</span>
                    </div>

                    {/* Privacy */}
                    <div className="flex items-center gap-2">
                        <Shield className="w-4 h-4" />
                        <span className="capitalize">{privacy ? formatLocationName(privacy) : '—'}</span>
                    </div>

                    {/* Day */}
                    <div className="flex items-center gap-2">
                        <Calendar className="w-4 h-4" />
                        <span>Day {dayNumber}</span>
                    </div>

                    {/* Time Slot (show in slots/hybrid mode) */}
                    {timeSlot && (timeMode === 'slots' || timeMode === 'hybrid') && (
                        <div className="flex items-center gap-2">
                            <Clock className="w-4 h-4" />
                            <span className="capitalize">{timeSlot}</span>
                        </div>
                    )}

                    {/* Time Clock (only show in clock/hybrid mode) */}
                    {timeClock && (timeMode === 'clock' || timeMode === 'hybrid') && (
                        <div className="flex items-center gap-2">
                            <Clock className="w-4 h-4" />
                            <span className="font-mono">{timeClock}</span>
                        </div>
                    )}

                    {/* Money */}
                    {playerMoney !== null && playerMoney !== undefined && (
                        <div className="flex items-center gap-2">
                            <Coins className="w-4 h-4" />
                            <span className="font-mono">{currencySymbol}{playerMoney}</span>
                        </div>
                    )}
                </div>

                <button
                    onClick={resetGame}
                    className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded text-sm"
                >
                    End Game
                </button>
            </div>
            {/* Main Content */}
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
                {/* Left Sidebar */}
                <div className="lg:col-span-1 space-y-4">
                    <ErrorBoundary fallbackTitle="Error loading player stats">
                        <PlayerPanel />
                    </ErrorBoundary>

                    <ErrorBoundary fallbackTitle="Error loading characters">
                        <CharacterPanel />
                    </ErrorBoundary>

                    <ErrorBoundary fallbackTitle="Error loading flags">
                        <FlagsPanel />
                    </ErrorBoundary>

                    <ErrorBoundary fallbackTitle="Error loading inventory">
                        <InventoryPanel />
                    </ErrorBoundary>

                    <ErrorBoundary fallbackTitle="Error loading controls">
                        <DeterministicControls />
                    </ErrorBoundary>
                </div>

                {/* Main Panel */}
                <div className="lg:col-span-3 space-y-4">
                    <ErrorBoundary fallbackTitle="Error loading narrative">
                        <NarrativePanel entries={turnLog} />
                    </ErrorBoundary>

                    <ErrorBoundary fallbackTitle="Error loading actions">
                        <ChoicePanel choices={choices} />
                    </ErrorBoundary>
                </div>
            </div>

            {/* Debug Panel */}
            <ErrorBoundary fallbackTitle="Error loading debug panel">
                <DebugPanel />
            </ErrorBoundary>
        </div>
    );
};
