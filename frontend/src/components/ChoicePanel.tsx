import { useState } from 'react';
import { useGameStore } from '../stores/gameStore';
import { MessageSquare, Hand, ChevronRight, Send } from 'lucide-react';

interface Props {
    choices: Array<{
        id: string;
        text: string;
        type: string;
        custom?: boolean;
        disabled?: boolean;
    }>;
}

export const ChoicePanel = ({ choices }: Props) => {
    const { sendAction, loading } = useGameStore();
    const [inputMode, setInputMode] = useState<'say' | 'do' | null>(null);
    const [inputText, setInputText] = useState('');
    const [targetChar, setTargetChar] = useState<string | null>(null);

    const handleChoice = (choice: any) => {
        if (choice.custom) {
            if (choice.type === 'custom_say') {
                setInputMode('say');
            } else if (choice.type === 'custom_do') {
                setInputMode('do');
            }
        } else if (!choice.disabled) {
            sendAction('choice', choice.text, null, choice.id);
        }
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (inputText.trim() && inputMode) {
            sendAction(inputMode, inputText, targetChar);
            setInputText('');
            setInputMode(null);
            setTargetChar(null);
        }
    };

    const getButtonStyle = (type: string) => {
        switch(type) {
            case 'custom_say':
                return 'bg-blue-600 hover:bg-blue-700 border-blue-500';
            case 'custom_do':
                return 'bg-green-600 hover:bg-green-700 border-green-500';
            case 'dialogue':
                return 'bg-blue-600/50 hover:bg-blue-700/50 border-blue-500/50';
            case 'movement':
                return 'bg-purple-600/50 hover:bg-purple-700/50 border-purple-500/50';
            case 'divider':
                return 'bg-transparent text-gray-500 cursor-default';
            default:
                return 'bg-gray-600/50 hover:bg-gray-700/50 border-gray-500/50';
        }
    };

    // Get available characters for targeting
    const characters = choices
        .filter(c => c.type === 'dialogue')
        .map(c => ({
            id: c.id.replace('talk_', ''),
            name: c.text.replace('💬 Talk to ', '')
        }));

    return (
        <div className="bg-gray-800/50 backdrop-blur border border-gray-700 rounded-lg p-4">
            {inputMode ? (
                <form onSubmit={handleSubmit} className="space-y-3">
                    <div className="flex items-center gap-2 mb-2">
                        {inputMode === 'say' ? (
                            <MessageSquare className="w-5 h-5 text-blue-400" />
                        ) : (
                            <Hand className="w-5 h-5 text-green-400" />
                        )}
                        <span className="text-lg font-semibold">
                            {inputMode === 'say' ? 'Say' : 'Do'} what?
                        </span>
                        <button
                            type="button"
                            onClick={() => setInputMode(null)}
                            className="ml-auto text-gray-400 hover:text-gray-200"
                        >
                            Cancel
                        </button>
                    </div>

                    {inputMode === 'say' && characters.length > 0 && (
                        <div className="flex gap-2 flex-wrap">
                            <span className="text-sm text-gray-400">To:</span>
                            <button
                                type="button"
                                onClick={() => setTargetChar(null)}
                                className={`px-2 py-1 text-xs rounded ${
                                    !targetChar ? 'bg-blue-600' : 'bg-gray-700'
                                }`}
                            >
                                Everyone
                            </button>
                            {characters.map(char => (
                                <button
                                    key={char.id}
                                    type="button"
                                    onClick={() => setTargetChar(char.id)}
                                    className={`px-2 py-1 text-xs rounded ${
                                        targetChar === char.id ? 'bg-blue-600' : 'bg-gray-700'
                                    }`}
                                >
                                    {char.name}
                                </button>
                            ))}
                        </div>
                    )}

                    <div className="flex gap-2">
                        <input
                            type="text"
                            value={inputText}
                            onChange={(e) => setInputText(e.target.value)}
                            placeholder={
                                inputMode === 'say'
                                    ? "What do you want to say?"
                                    : "What do you want to do?"
                            }
                            className="flex-1 px-3 py-2 bg-gray-900 border border-gray-600 rounded-lg
                                     focus:outline-none focus:border-blue-500"
                            autoFocus
                            disabled={loading}
                        />
                        <button
                            type="submit"
                            disabled={loading || !inputText.trim()}
                            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600
                                     disabled:cursor-not-allowed rounded-lg flex items-center gap-2"
                        >
                            <Send className="w-4 h-4" />
                            Send
                        </button>
                    </div>

                    <div className="text-xs text-gray-400">
                        {inputMode === 'say' ? (
                            <p>💡 Tip: Have conversations with NPCs. Long dialogues won't advance time immediately.</p>
                        ) : (
                            <p>💡 Tip: Describe actions like "examine the bar", "go to the street", "kiss Alex"</p>
                        )}
                    </div>
                </form>
            ) : (
                <>
                    <h3 className="text-lg font-semibold mb-3 text-gray-100">Actions</h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {choices.map((choice) => (
                            <button
                                key={choice.id}
                                onClick={() => handleChoice(choice)}
                                disabled={loading || choice.disabled}
                                className={`px-4 py-3 rounded-lg border transition-all flex items-center justify-between
                                    ${getButtonStyle(choice.type)}
                                    disabled:cursor-not-allowed disabled:opacity-50 text-left`}
                            >
                                <span>{choice.text}</span>
                                {!choice.disabled && <ChevronRight className="w-4 h-4 ml-2" />}
                            </button>
                        ))}
                    </div>

                    {loading && (
                        <div className="mt-4 text-center">
                            <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
                        </div>
                    )}
                </>
            )}
        </div>
    );
};