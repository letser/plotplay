import { useEffect, useRef, useState } from 'react';
import { TurnLogEntry, useGameStore } from '../stores/gameStore';
import { Sparkles, CheckCircle, RotateCcw } from 'lucide-react';
import clsx from 'clsx';

type Props = {
    entries: TurnLogEntry[];
};

export const NarrativePanel = ({ entries }: Props) => {
    const bottomRef = useRef<HTMLDivElement | null>(null);
    const { clearTurnLog, retryLastAction, checkerStatus } = useGameStore();
    const [copied, setCopied] = useState(false);
    const [retrying, setRetrying] = useState<number | null>(null);

    useEffect(() => {
        const element = bottomRef.current;
        if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }
    }, [entries, checkerStatus]); // Scroll when entries or checker status changes

    const handleCopyLog = async () => {
        try {
            await navigator.clipboard.writeText(JSON.stringify(entries, null, 2));
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
        } catch (err) {
            console.error('Failed to copy log:', err);
        }
    };

    const handleRetry = async (entryId: number) => {
        setRetrying(entryId);
        try {
            await retryLastAction();
        } finally {
            setRetrying(null);
        }
    };

    const disableClear = entries.length <= 1;

    return (
        <div className="bg-gray-800/50 backdrop-blur border border-gray-700 rounded-lg p-6 h-[500px] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-100">Turn Log</h2>
                <div className="flex items-center gap-2">
                    <button
                        onClick={handleCopyLog}
                        className="px-3 py-1.5 text-xs bg-gray-700 hover:bg-gray-600 rounded text-gray-200 transition-colors"
                    >
                        {copied ? 'Copied!' : 'Copy JSON'}
                    </button>
                    <button
                        onClick={() => clearTurnLog()}
                        disabled={disableClear}
                        className="px-3 py-1.5 text-xs rounded bg-red-600/20 text-red-200 hover:bg-red-600/40 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                        Clear history
                    </button>
                </div>
            </div>

            <div className="space-y-6">
                {entries.map((entry, index) => {
                    const showNarrative =
                        entry.narrative &&
                        entry.narrative.trim().toLowerCase() !== entry.summary.trim().toLowerCase();
                    const isDeterministic = entry.origin === 'deterministic';
                    const isLastEntry = index === entries.length - 1;
                    const formattedTime = new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

                    return (
                        <div key={entry.id} className="animate-fade-in-up">
                            {/* Action Summary with better visual separation */}
                            <div className="bg-gray-700/30 rounded-lg p-3 mb-3">
                                <div className="flex items-start justify-between gap-3">
                                    <p className="text-sm uppercase tracking-wide text-blue-300 font-semibold">
                                        {entry.summary}
                                    </p>
                                    <div className="flex items-center gap-2 text-xs flex-shrink-0">
                                        {isDeterministic ? (
                                            <span title="Deterministic action">
                                                <CheckCircle className="w-4 h-4 text-green-400" />
                                            </span>
                                        ) : (
                                            <>
                                                <span title="AI-generated">
                                                    <Sparkles className="w-4 h-4 text-blue-400" />
                                                </span>
                                                {isLastEntry && (
                                                    <button
                                                        onClick={() => handleRetry(entry.id)}
                                                        disabled={retrying === entry.id}
                                                        className="flex items-center text-blue-400 hover:text-blue-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                                        title={retrying === entry.id ? 'Regenerating...' : 'Retry this response'}
                                                    >
                                                        <RotateCcw className={clsx('w-4 h-4', retrying === entry.id && 'animate-spin')} />
                                                    </button>
                                                )}
                                            </>
                                        )}
                                        <span className="text-gray-400 font-mono">{formattedTime}</span>
                                    </div>
                                </div>
                            </div>

                            {/* Narrative */}
                            {showNarrative && (
                                <div className="mb-3">
                                    <div className="space-y-3 text-gray-100 leading-relaxed">
                                        {entry.narrative.split('\n').map((paragraph, pIndex) => (
                                            <p key={pIndex} className="text-base">
                                                {paragraph}
                                            </p>
                                        ))}
                                    </div>
                                </div>
                            )}
                            {!showNarrative && (
                                <p className="text-xs text-gray-500 italic mb-3">
                                    No additional AI prose for this entry.
                                </p>
                            )}
                            <div className="border-b border-gray-700" />
                        </div>
                    );
                })}

                {/* Checker Status Indicator */}
                {checkerStatus && (
                    <div className="animate-fade-in-up">
                        <div className="flex items-center gap-2 text-sm text-blue-300 italic py-2">
                            <div className="flex gap-1">
                                <span className="animate-pulse">●</span>
                                <span className="animate-pulse" style={{ animationDelay: '150ms' }}>●</span>
                                <span className="animate-pulse" style={{ animationDelay: '300ms' }}>●</span>
                            </div>
                            <span>{checkerStatus}</span>
                        </div>
                    </div>
                )}

                {/* Scroll anchor - ensures we scroll past the status message */}
                <div ref={bottomRef} className="h-4" />
            </div>
        </div>
    );
};
