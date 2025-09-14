import { useState } from 'react';
import { useGameStore } from '../stores/gameStore';
import { MessageSquare, Hand, Send, ChevronDown, MapPin, Users } from 'lucide-react';

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
    const [inputMode, setInputMode] = useState<'say' | 'do'>('say');
    const [inputText, setInputText] = useState('');
    const [targetChar, setTargetChar] = useState<string | null>(null);
    const [showTargetMenu, setShowTargetMenu] = useState(false);

    // Parse characters from dialogue choices
    const characters = choices
        .filter(c => c.type === 'dialogue')
        .map(c => ({
            id: c.id.replace('talk_', ''),
            name: c.text.replace('💬 Talk to ', '')
        }));

    // Group choices by type
    const dialogueChoices = choices.filter(c => c.type === 'dialogue' && !c.disabled);
    const movementChoices = choices.filter(c => c.type === 'movement' && !c.disabled);
    const nodeChoices = choices.filter(c => c.type === 'node_choice' && !c.disabled);
    const otherChoices = choices.filter(c =>
        !['custom_say', 'custom_do', 'dialogue', 'movement', 'node_choice', 'divider'].includes(c.type) &&
        !c.disabled
    );

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (inputText.trim()) {
            sendAction(inputMode, inputText, inputMode === 'say' ? targetChar : null);
            setInputText('');
        }
    };

    const handleQuickAction = (choice: any) => {
        sendAction('choice', choice.text, null, choice.id);
    };

    const getTargetDisplay = () => {
        if (inputMode !== 'say') return null;
        const target = targetChar
            ? characters.find(c => c.id === targetChar)?.name
            : 'Everyone';
        return target;
    };

    return (
        <div className="bg-gray-800/50 backdrop-blur border border-gray-700 rounded-lg p-4 space-y-4">
            {/* Main Input Area */}
            <form onSubmit={handleSubmit} className="space-y-3">
                <div className="flex gap-2">
                    {/* Mode Selector */}
                    <div className="flex bg-gray-900 rounded-lg p-1">
                        <button
                            type="button"
                            onClick={() => setInputMode('say')}
                            className={`px-3 py-2 rounded-md flex items-center gap-2 transition-all ${
                                inputMode === 'say'
                                    ? 'bg-blue-600 text-white'
                                    : 'text-gray-400 hover:text-white'
                            }`}
                        >
                            <MessageSquare className="w-4 h-4" />
                            <span className="text-sm font-medium">Say</span>
                        </button>
                        <button
                            type="button"
                            onClick={() => setInputMode('do')}
                            className={`px-3 py-2 rounded-md flex items-center gap-2 transition-all ${
                                inputMode === 'do'
                                    ? 'bg-green-600 text-white'
                                    : 'text-gray-400 hover:text-white'
                            }`}
                        >
                            <Hand className="w-4 h-4" />
                            <span className="text-sm font-medium">Do</span>
                        </button>
                    </div>

                    {/* Target Selector (for Say mode) */}
                    {inputMode === 'say' && characters.length > 0 && (
                        <div className="relative">
                            <button
                                type="button"
                                onClick={() => setShowTargetMenu(!showTargetMenu)}
                                className="px-3 py-2 bg-gray-900 rounded-lg flex items-center gap-2 hover:bg-gray-800 transition-colors"
                            >
                                <Users className="w-4 h-4 text-gray-400" />
                                <span className="text-sm">{getTargetDisplay()}</span>
                                <ChevronDown className="w-3 h-3 text-gray-400" />
                            </button>

                            {showTargetMenu && (
                                <div className="absolute top-full mt-1 left-0 z-10 bg-gray-900 border border-gray-700 rounded-lg shadow-lg min-w-[150px]">
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setTargetChar(null);
                                            setShowTargetMenu(false);
                                        }}
                                        className={`w-full px-3 py-2 text-left text-sm hover:bg-gray-800 ${
                                            !targetChar ? 'bg-gray-800' : ''
                                        }`}
                                    >
                                        Everyone
                                    </button>
                                    {characters.map(char => (
                                        <button
                                            key={char.id}
                                            type="button"
                                            onClick={() => {
                                                setTargetChar(char.id);
                                                setShowTargetMenu(false);
                                            }}
                                            className={`w-full px-3 py-2 text-left text-sm hover:bg-gray-800 ${
                                                targetChar === char.id ? 'bg-gray-800' : ''
                                            }`}
                                        >
                                            {char.name}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Input Field */}
                    <input
                        type="text"
                        value={inputText}
                        onChange={(e) => setInputText(e.target.value)}
                        placeholder={
                            inputMode === 'say'
                                ? `Say to ${getTargetDisplay() || 'everyone'}...`
                                : "What do you want to do?"
                        }
                        className="flex-1 px-4 py-2 bg-gray-900 border border-gray-600 rounded-lg
                                 focus:outline-none focus:border-blue-500 placeholder-gray-500"
                        disabled={loading}
                    />

                    {/* Send Button */}
                    <button
                        type="submit"
                        disabled={loading || !inputText.trim()}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600
                                 disabled:cursor-not-allowed rounded-lg flex items-center gap-2 transition-colors"
                    >
                        <Send className="w-4 h-4" />
                    </button>
                </div>

                {/* Input hints */}
                <div className="text-xs text-gray-500 italic">
                    {inputMode === 'say' ? (
                        <span>💡 Chat with characters, ask questions, or express yourself</span>
                    ) : (
                        <span>💡 Examine, interact, move, or perform any action you can imagine</span>
                    )}
                </div>
            </form>

            {/* Quick Actions Section */}
            {(dialogueChoices.length > 0 || movementChoices.length > 0 || nodeChoices.length > 0 || otherChoices.length > 0) && (
                <div className="space-y-3 pt-3 border-t border-gray-700">
                    <h4 className="text-sm font-medium text-gray-400">Quick Actions</h4>

                    {/* Dialogue Actions */}
                    {dialogueChoices.length > 0 && (
                        <div className="space-y-2">
                            <h5 className="text-xs text-gray-500 uppercase tracking-wide flex items-center gap-1">
                                <MessageSquare className="w-3 h-3" />
                                Conversations
                            </h5>
                            <div className="flex flex-wrap gap-2">
                                {dialogueChoices.map((choice) => (
                                    <button
                                        key={choice.id}
                                        onClick={() => handleQuickAction(choice)}
                                        disabled={loading}
                                        className="px-3 py-1.5 text-sm bg-blue-600/20 hover:bg-blue-600/30
                                                 border border-blue-600/50 rounded-md transition-all
                                                 disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        {choice.text}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Movement Actions */}
                    {movementChoices.length > 0 && (
                        <div className="space-y-2">
                            <h5 className="text-xs text-gray-500 uppercase tracking-wide flex items-center gap-1">
                                <MapPin className="w-3 h-3" />
                                Movement
                            </h5>
                            <div className="flex flex-wrap gap-2">
                                {movementChoices.map((choice) => (
                                    <button
                                        key={choice.id}
                                        onClick={() => handleQuickAction(choice)}
                                        disabled={loading}
                                        className="px-3 py-1.5 text-sm bg-purple-600/20 hover:bg-purple-600/30
                                                 border border-purple-600/50 rounded-md transition-all
                                                 disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        {choice.text}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Context Actions */}
                    {nodeChoices.length > 0 && (
                        <div className="space-y-2">
                            <h5 className="text-xs text-gray-500 uppercase tracking-wide flex items-center gap-1">
                                <Hand className="w-3 h-3" />
                                Actions
                            </h5>
                            <div className="flex flex-wrap gap-2">
                                {nodeChoices.map((choice) => (
                                    <button
                                        key={choice.id}
                                        onClick={() => handleQuickAction(choice)}
                                        disabled={loading}
                                        className="px-3 py-1.5 text-sm bg-green-600/20 hover:bg-green-600/30
                                                 border border-green-600/50 rounded-md transition-all
                                                 disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        {choice.text}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Other Actions */}
                    {otherChoices.length > 0 && (
                        <div className="flex flex-wrap gap-2">
                            {otherChoices.map((choice) => (
                                <button
                                    key={choice.id}
                                    onClick={() => handleQuickAction(choice)}
                                    disabled={loading}
                                    className="px-3 py-1.5 text-sm bg-gray-600/20 hover:bg-gray-600/30
                                             border border-gray-600/50 rounded-md transition-all
                                             disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {choice.text}
                                </button>
                            ))}
                        </div>
                    )}
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