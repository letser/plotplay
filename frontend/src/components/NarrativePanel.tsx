import { useEffect, useRef, useState } from 'react';
import { TurnLogEntry, useGameStore } from '../stores/gameStore';
import clsx from 'clsx';

type Props = {
    entries: TurnLogEntry[];
};

export const NarrativePanel = ({ entries }: Props) => {
    const bottomRef = useRef<HTMLDivElement | null>(null);
    const { clearTurnLog } = useGameStore();
    const [copied, setCopied] = useState(false);

    useEffect(() => {
        const element = bottomRef.current;
        if (element) {
            element.scrollIntoView({ behavior: 'smooth' });
        }
    }, [entries]);

    const handleCopyLog = async () => {
        try {
            await navigator.clipboard.writeText(JSON.stringify(entries, null, 2));
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
        } catch (err) {
            console.error('Failed to copy log:', err);
        }
    };

    const disableClear = entries.length <= 1;

    return (
        <div className="bg-gray-800/50 backdrop-blur border border-gray-700 rounded-lg p-6 h-[500px] overflow-y-auto">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-4">
                <div>
                    <h2 className="text-lg font-semibold text-gray-100">Turn Log</h2>
                    <p className="text-xs text-gray-400">
                        Each entry shows the quick summary first, followed by AI narrative when available.
                    </p>
                </div>
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
                {entries.map((entry) => {
                    const showNarrative =
                        entry.narrative &&
                        entry.narrative.trim().toLowerCase() !== entry.summary.trim().toLowerCase();
                    const isDeterministic = entry.origin === 'deterministic';
                    const formattedTime = new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

                    return (
                        <div key={entry.id} className="animate-fade-in-up">
                            <div className="flex items-start justify-between gap-3 mb-2">
                                <p className="text-sm uppercase tracking-wide text-blue-200 font-semibold">
                                    {entry.summary}
                                </p>
                                <div className="flex items-center gap-2 text-xs">
                                    <span
                                        className={clsx(
                                            'px-2 py-0.5 rounded-full font-semibold',
                                            isDeterministic
                                                ? 'bg-green-500/20 text-green-200 border border-green-500/40'
                                                : 'bg-blue-500/20 text-blue-200 border border-blue-500/40'
                                        )}
                                    >
                                        {isDeterministic ? 'Deterministic' : 'AI-generated'}
                                    </span>
                                    <span className="text-gray-400 font-mono">{formattedTime}</span>
                                </div>
                            </div>
                            {showNarrative && (
                                <div className="space-y-3 text-gray-100 leading-relaxed">
                                    {entry.narrative.split('\n').map((paragraph, index) => (
                                        <p key={index} className="text-base">
                                            {paragraph}
                                        </p>
                                    ))}
                                </div>
                            )}
                            {!showNarrative && (
                                <p className="text-xs text-gray-500 italic">
                                    No additional AI prose for this entry.
                                </p>
                            )}
                            <div className="border-b border-gray-700 mt-4" />
                        </div>
                    );
                })}
                <div ref={bottomRef} />
            </div>
        </div>
    );
};
