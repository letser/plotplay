// frontend/src/components/LogEntry.tsx
import { useState } from 'react'; // Corrected import
import { ChevronRight, ChevronDown } from 'lucide-react';

interface Props {
    log: string;
}

export const LogEntry = ({ log }: Props) => {
    const [isExpanded, setIsExpanded] = useState(true);

    const getLogLevelColor = (level: string) => {
        switch (level) {
            case 'INFO':
                return 'text-blue-400';
            case 'DEBUG':
                return 'text-gray-500';
            case 'WARNING':
                return 'text-yellow-400';
            case 'ERROR':
                return 'text-red-400';
            default:
                return 'text-gray-400';
        }
    };

    const formatLog = (logText: string) => {
        const match = logText.match(/(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - ([\w.-]+) - (\w+) - (.*)/s);
        if (!match) return <span>{logText}</span>;

        const [, timestamp, , level, message] = match;
        const levelColor = getLogLevelColor(level);

        // Keywords for special styling
        let messageElement;
        if (message.includes('🎨 WRITER:') || message.includes('Writer Prompt:')) {
            messageElement = <span className="text-cyan-400 font-semibold">{message}</span>;
        } else if (message.includes('🔍 CHECKER:') || message.includes('Checker Prompt:')) {
            messageElement = <span className="text-purple-400 font-semibold">{message}</span>;
        } else if (message.includes('⏱️  AI Call')) {
            // Highlight timing information in green
            messageElement = <span className="text-green-400 font-semibold">{message}</span>;
        } else if (message.includes('Writer Response:')) {
            messageElement = <span className="text-cyan-300">{message}</span>;
        } else if (message.includes('Checker Response:')) {
            messageElement = <span className="text-purple-300">{message}</span>;
        } else if (message.includes('Player Action:')) {
            messageElement = <span className="text-green-400 font-semibold">{message}</span>;
        } else if (message.includes('TIMEOUT') || message.includes('ERROR')) {
            messageElement = <span className="text-red-400 font-semibold">{message}</span>;
        } else {
            messageElement = <span>{message}</span>;
        }

        const isCollapsible = message.split('\n').length > 3;

        return (
            <div className="flex items-start">
                {isCollapsible && (
                    <button onClick={() => setIsExpanded(!isExpanded)} className="pr-2 pt-0.5">
                        {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    </button>
                )}
                <div className={!isCollapsible ? "ml-5" : ""}>
                    <span className="text-gray-500">{timestamp}</span>{' '}
                    <span className={`${levelColor} font-bold`}>{level}</span>{' '}
                    <div className={`whitespace-pre-wrap ${!isExpanded ? 'hidden' : ''}`}>
                        {messageElement}
                    </div>
                    {!isExpanded && <span className="text-gray-500 italic">...</span>}
                </div>
            </div>
        );
    };

    return formatLog(log);
};