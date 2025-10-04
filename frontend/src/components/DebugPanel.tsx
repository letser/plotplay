// frontend/src/components/DebugPanel.tsx
import { useState, useEffect, useRef } from 'react';
import { useGameStore } from '../stores/gameStore';
import { gameApi } from '../services/gameApi';
import { Terminal, ChevronUp, ChevronDown } from 'lucide-react';
import { LogEntry } from './LogEntry';

export const DebugPanel = () => {
    const { sessionId, turnCounter } = useGameStore();
    const [logs, setLogs] = useState('');
    const [lastSize, setLastSize] = useState(0);
    const [isOpen, setIsOpen] = useState(false);
    const logContainerRef = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        if (!sessionId || !isOpen) return;

        const fetchAndSetLogs = async () => {
            try {
                const response = await gameApi.getLogs(sessionId, lastSize);
                if (response.content) {
                    setLogs(prevLogs => prevLogs + response.content);
                }
                setLastSize(response.size);
            } catch (error) {
                console.error("Failed to fetch logs:", error);
            }
        };

        void fetchAndSetLogs();

    }, [sessionId, lastSize, isOpen, turnCounter]);

    useEffect(() => {
        if (isOpen && logContainerRef.current) {
            logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
        }
    }, [logs, isOpen]);

    const logEntries = logs.split(/(?=^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})/m).filter(Boolean);

    return (
        <div className="fixed bottom-0 left-0 right-0 z-50">
            <div className="max-w-7xl mx-auto px-4">
                <button
                    onClick={() => setIsOpen(!isOpen)}
                    className="w-full bg-gray-700 hover:bg-gray-600 text-gray-200 px-4 py-2 rounded-t-lg flex justify-between items-center"
                >
                    <div className="flex items-center gap-2">
                        <Terminal className="w-4 h-4" />
                        <span>Debug Log</span>
                    </div>
                    {isOpen ? <ChevronDown className="w-5 h-5" /> : <ChevronUp className="w-5 h-5" />}
                </button>
                {isOpen && (
                    <div
                        ref={logContainerRef}
                        className="bg-gray-950 text-gray-300 p-4 h-64 overflow-y-auto text-xs font-mono border-x border-gray-700 space-y-2"
                    >
                        {logEntries.length > 0
                            ? logEntries.map((log, index) => (
                                <LogEntry key={index} log={log} />
                            ))
                            : "Waiting for logs..."}
                    </div>
                )}
            </div>
        </div>
    );
};