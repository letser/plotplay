import { useState, useRef, ReactNode } from 'react';
import { useGameStore } from '../stores/gameStore';
import { useLocation } from '../hooks';
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts';
import { toTitleCase } from '../utils';
import { LoadingSpinner } from './LoadingSpinner';
import { ZoneConnection } from '../services/gameApi';
import { MessageSquare, Hand, Send, MapPin, ArrowUp, ArrowDown, ArrowLeft, ArrowRight, Lock } from 'lucide-react';

const directionIconMap: Record<string, ReactNode> = {
    n: <ArrowUp className="w-4 h-4" />,
    s: <ArrowDown className="w-4 h-4" />,
    e: <ArrowRight className="w-4 h-4" />,
    w: <ArrowLeft className="w-4 h-4" />,
};

interface Choice {
    id: string;
    text: string;
    type: string;
    disabled?: boolean;
    skip_ai?: boolean;
}

interface Props {
    choices: Choice[];
}

// Zone Travel Widget Component
const ZoneTravelWidget = ({ connection, onTravel, loading }: { connection: ZoneConnection, onTravel: (zoneId: string, method: string | null, entryLocationId: string | null) => void, loading: boolean }) => {
    const [selectedMethod, setSelectedMethod] = useState<string | null>(
        connection.available_methods.length > 0 ? connection.available_methods[0] : null
    );
    const [selectedEntry, setSelectedEntry] = useState<string | null>(
        connection.entry_locations.length > 0 ? connection.entry_locations[0].id : null
    );

    const handleTravel = () => {
        onTravel(connection.zone_id, selectedMethod, selectedEntry);
    };

    const hasMultipleMethods = connection.available_methods.length > 1;
    const hasMultipleEntries = connection.entry_locations.length > 1;
    const needsSelectors = hasMultipleMethods || hasMultipleEntries;

    if (!needsSelectors) {
        // Simple button for single method/entry
        return (
            <button
                onClick={handleTravel}
                disabled={!connection.available || loading}
                className="w-full bg-orange-600/20 hover:bg-orange-600/30 border border-orange-600/50 rounded-md px-3 py-2 text-left text-sm disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
                Travel to {connection.zone_name}
            </button>
        );
    }

    // Complex widget with selectors
    return (
        <div className="bg-orange-600/10 rounded-md px-3 py-2 border border-orange-600/50">
            <div className="text-sm font-medium text-gray-200 mb-2">Travel to {connection.zone_name}</div>

            <div className="flex items-center gap-2 flex-wrap text-xs">
                {hasMultipleEntries && (
                    <select
                        value={selectedEntry || ''}
                        onChange={(e) => setSelectedEntry(e.target.value)}
                        className="flex-1 min-w-[100px] bg-gray-800 text-gray-200 rounded px-2 py-1 border border-gray-600 focus:border-orange-500 focus:outline-none"
                        disabled={!connection.available || loading}
                    >
                        {connection.entry_locations.map((entry) => (
                            <option key={entry.id} value={entry.id}>
                                {entry.name}
                            </option>
                        ))}
                    </select>
                )}

                {hasMultipleMethods && (
                    <>
                        <span className="text-gray-400">via</span>
                        <select
                            value={selectedMethod || ''}
                            onChange={(e) => setSelectedMethod(e.target.value)}
                            className="flex-1 min-w-[80px] bg-gray-800 text-gray-200 rounded px-2 py-1 border border-gray-600 focus:border-orange-500 focus:outline-none"
                            disabled={!connection.available || loading}
                        >
                            {connection.available_methods.map((method) => (
                                <option key={method} value={method}>
                                    {toTitleCase(method)}
                                </option>
                            ))}
                        </select>
                    </>
                )}

                <button
                    onClick={handleTravel}
                    disabled={!connection.available || loading}
                    className="ml-auto bg-orange-600 hover:bg-orange-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white text-xs px-3 py-1 rounded transition-colors"
                >
                    Go
                </button>
            </div>
        </div>
    );
};

export const ChoicePanel = ({ choices }: Props) => {
    const { sendAction, performMovement, performZoneTravel, loading } = useGameStore();
    const location = useLocation();
    const [inputMode, setInputMode] = useState<'say' | 'do'>('do');
    const [inputText, setInputText] = useState('');
    const inputRef = useRef<HTMLInputElement>(null);

    // Get exits and zone connections from location
    const exits = location?.exits ?? [];
    const zoneConnections = location?.zone_connections ?? [];

    // Group choices by type
    const nodeChoices = choices.filter(c => c.type === 'node_choice' && !c.disabled);

    // Keyboard shortcuts
    useKeyboardShortcuts([
        {
            key: 'Escape',
            handler: () => {
                setInputText('');
            },
            description: 'Clear input',
        },
        {
            key: 'k',
            ctrl: true,
            handler: () => {
                inputRef.current?.focus();
            },
            description: 'Focus input field',
        },
        ...nodeChoices.slice(0, 9).map((choice, index) => ({
            key: String(index + 1),
            handler: () => {
                if (!loading) {
                    handleQuickAction(choice);
                }
            },
            description: `Activate choice ${index + 1}: ${choice.text}`,
        })),
    ]);

    const handleInputChange = (text: string) => {
        setInputText(text);

        // Auto-switch mode based on mnemonic prefix
        if (text.startsWith('@')) {
            setInputMode('say');
        } else if (text.startsWith('>')) {
            setInputMode('do');
        }
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (inputText.trim()) {
            // Determine final mode (check for mnemonic override)
            let finalMode = inputMode;
            let finalText = inputText.trim();

            if (finalText.startsWith('@')) {
                finalMode = 'say';
                finalText = finalText.slice(1).trim(); // Remove @ prefix
            } else if (finalText.startsWith('>')) {
                finalMode = 'do';
                finalText = finalText.slice(1).trim(); // Remove > prefix
            }

            // Send action without target (AI will handle it)
            sendAction('choice', finalText, null, `custom_${finalMode}`);
            setInputText('');
        }
    };

    const handleQuickAction = (choice: Choice) => {
        if (choice.type === 'movement') {
            void performMovement(choice.id);
        } else {
            const shouldSkip = choice.skip_ai ?? false;
            sendAction('choice', choice.text, null, choice.id, undefined, { skipAi: shouldSkip });
        }
    };

    const handleMove = (exitId: string | null, direction: string | null) => {
        if (exitId) {
            void performMovement(`move_${exitId}`);
        } else if (direction) {
            void performMovement(`direction_${direction}`);
        }
    };

    return (
        <div className="bg-gray-800/50 backdrop-blur border border-gray-700 rounded-lg p-4 space-y-4">
            {/* Main Input Area */}
            <form onSubmit={handleSubmit} className="space-y-3">
                <div className="flex gap-2">
                    {/* Mode Indicator - shows current mode based on input */}
                    <div className="flex bg-gray-900 rounded-lg p-1">
                        <button
                            type="button"
                            onClick={() => {
                                setInputMode('say');
                                inputRef.current?.focus();
                            }}
                            className={`px-3 py-2 rounded-md flex items-center gap-2 transition-all ${
                                inputMode === 'say'
                                    ? 'bg-blue-600 text-white'
                                    : 'text-gray-400 hover:text-white'
                            }`}
                            title="Say mode (use @ prefix)"
                        >
                            <MessageSquare className="w-4 h-4" />
                            <span className="text-sm font-medium">@</span>
                        </button>
                        <button
                            type="button"
                            onClick={() => {
                                setInputMode('do');
                                inputRef.current?.focus();
                            }}
                            className={`px-3 py-2 rounded-md flex items-center gap-2 transition-all ${
                                inputMode === 'do'
                                    ? 'bg-green-600 text-white'
                                    : 'text-gray-400 hover:text-white'
                            }`}
                            title="Do mode (use > prefix)"
                        >
                            <Hand className="w-4 h-4" />
                            <span className="text-sm font-medium">&gt;</span>
                        </button>
                    </div>

                    {/* Input Field */}
                    <input
                        ref={inputRef}
                        type="text"
                        value={inputText}
                        onChange={(e) => handleInputChange(e.target.value)}
                        placeholder={
                            inputMode === 'say'
                                ? "Say something... (or start with > to do)"
                                : "What do you want to do? (or start with @ to say)"
                        }
                        className="flex-1 px-4 py-2 bg-gray-900 border border-gray-600 rounded-lg
                                 focus:outline-none focus:border-blue-500 placeholder-gray-500"
                        disabled={loading}
                    />

                    {/* Send Button */}
                    <button
                        type="submit"
                        disabled={loading || !inputText.trim()}
                        aria-label="Submit"
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600
                                 disabled:cursor-not-allowed rounded-lg flex items-center gap-2 transition-colors"
                    >
                        {loading ? <LoadingSpinner size="sm" /> : <Send className="w-4 h-4" />}
                    </button>
                </div>
            </form>

            {/* Quick Actions Section - Side by Side Layout */}
            {(exits.length > 0 || nodeChoices.length > 0) && (
                <div className="pt-3 border-t border-gray-700">
                    <div className="grid grid-cols-2 gap-4">
                        {/* Movement Column */}
                        <div className="space-y-2">
                            <h5 className="text-xs text-gray-500 uppercase tracking-wide flex items-center gap-1">
                                <MapPin className="w-3 h-3" />
                                Movement
                            </h5>

                            {/* Compass Layout for Directional Exits */}
                            {(() => {
                                // Create a map of directions to exits
                                const exitMap = new Map<string, typeof exits[0]>();
                                exits.forEach(exit => {
                                    if (exit.direction) {
                                        exitMap.set(exit.direction.toLowerCase(), exit);
                                    }
                                });

                                const getExit = (dir: string) => exitMap.get(dir);

                                const renderDirectionButton = (dir: string) => {
                                    const exit = getExit(dir);
                                    const icon = directionIconMap[dir];

                                    // Determine state and label based on discovered/locked status
                                    let label: string;
                                    let showLock = false;
                                    let isEnabled = false;

                                    if (!exit) {
                                        // No exit in this direction
                                        label = dir.toUpperCase();
                                        isEnabled = false;
                                    } else if (!exit.discovered) {
                                        // Not discovered - show direction only
                                        label = dir.toUpperCase();
                                        isEnabled = false;
                                    } else if (exit.locked) {
                                        // Discovered but locked - show name + lock icon
                                        label = toTitleCase(exit.name);
                                        showLock = true;
                                        isEnabled = false;
                                    } else {
                                        // Discovered and unlocked - show name
                                        label = toTitleCase(exit.name);
                                        isEnabled = true;
                                    }

                                    return (
                                        <button
                                            key={dir}
                                            onClick={() => exit && exit.discovered && handleMove(exit.to, exit.direction)}
                                            disabled={!isEnabled || loading}
                                            className="bg-purple-600/20 hover:bg-purple-600/30 border border-purple-600/50 rounded-md px-3 py-2 text-sm disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-1"
                                        >
                                            {icon}
                                            <span className="text-xs">{label}</span>
                                            {showLock && <Lock className="w-3 h-3 text-yellow-500" />}
                                        </button>
                                    );
                                };

                                return (
                                    <div className="space-y-2">
                                        {/* Compass Rose Layout */}
                                        <div className="flex flex-col gap-1">
                                            {/* North */}
                                            <div className="flex justify-center">
                                                {renderDirectionButton('n')}
                                            </div>
                                            {/* West and East */}
                                            <div className="grid grid-cols-2 gap-1">
                                                {renderDirectionButton('w')}
                                                {renderDirectionButton('e')}
                                            </div>
                                            {/* South */}
                                            <div className="flex justify-center">
                                                {renderDirectionButton('s')}
                                            </div>
                                        </div>

                                        {/* Zone Travel - New Widget System */}
                                        {zoneConnections.length > 0 && (
                                            <div className="space-y-2 pt-2 border-t border-gray-700/50">
                                                {zoneConnections.map((connection) => (
                                                    <ZoneTravelWidget
                                                        key={connection.zone_id}
                                                        connection={connection}
                                                        onTravel={(zoneId, method, entryLocationId) => {
                                                            void performZoneTravel(zoneId, method, entryLocationId);
                                                        }}
                                                        loading={loading}
                                                    />
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                );
                            })()}
                        </div>

                        {/* Actions Column */}
                        <div className="space-y-2">
                            <h5 className="text-xs text-gray-500 uppercase tracking-wide flex items-center gap-1">
                                <Hand className="w-3 h-3" />
                                Actions
                            </h5>
                            {nodeChoices.length > 0 ? (
                                <div className="flex flex-col gap-2">
                                    {nodeChoices.map((choice, index) => (
                                        <button
                                            key={choice.id}
                                            onClick={() => handleQuickAction(choice)}
                                            disabled={loading}
                                            className="w-full px-3 py-2 text-sm text-left bg-green-600/20 hover:bg-green-600/30
                                                     border border-green-600/50 rounded-md transition-all
                                                     hover:scale-105 active:scale-95
                                                     disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            {index < 9 && <span className="text-xs opacity-60 mr-1">{index + 1}</span>}
                                            {choice.text}
                                        </button>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-xs text-gray-500 italic">No actions available</p>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Loading indicator */}
            {loading && (
                <div className="flex justify-center py-2">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500"></div>
                </div>
            )}
        </div>
    );
};
