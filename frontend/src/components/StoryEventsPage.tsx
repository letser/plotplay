import { useQuery } from '@tanstack/react-query';
import { gameApi, CharacterMemory } from '../services/gameApi';
import { useGameStore } from '../stores/gameStore';
import { Book } from 'lucide-react';

export function StoryEventsPage() {
    const sessionId = useGameStore(state => state.sessionId);

    const { data: storyEvents, isLoading } = useQuery({
        queryKey: ['story-events', sessionId],
        queryFn: () => sessionId ? gameApi.getStoryEvents(sessionId) : Promise.reject(),
        enabled: !!sessionId,
    });

    if (isLoading) {
        return (
            <div className="flex-1 p-6">
                <div className="animate-pulse">Loading story events...</div>
            </div>
        );
    }

    if (!storyEvents || storyEvents.memories.length === 0) {
        return (
            <div className="flex-1 p-6">
                <div className="flex items-center gap-3 mb-6">
                    <Book className="w-8 h-8 text-gray-400" />
                    <h2 className="text-2xl font-bold">Story Events</h2>
                </div>
                <p className="text-gray-500 italic">No story events recorded yet.</p>
            </div>
        );
    }

    // Group memories by day
    const memoriesByDay = storyEvents.memories.reduce((acc, memory) => {
        const day = memory.day;
        if (!acc[day]) acc[day] = [];
        acc[day].push(memory);
        return acc;
    }, {} as Record<number, CharacterMemory[]>);

    const days = Object.keys(memoriesByDay).map(Number).sort((a, b) => a - b);

    return (
        <div className="flex-1 p-6 overflow-y-auto">
            <div className="flex items-center gap-3 mb-6">
                <Book className="w-8 h-8 text-gray-400" />
                <h2 className="text-2xl font-bold">Story Events</h2>
            </div>

            <p className="text-gray-400 mb-6">
                General events and atmosphere that shaped your journey
            </p>

            <div className="space-y-6">
                {days.map(day => (
                    <div key={day} className="border-l-2 border-blue-500 pl-4">
                        <h3 className="text-sm font-semibold text-blue-400 mb-3">
                            Day {day}
                        </h3>
                        <div className="space-y-2">
                            {memoriesByDay[day].map((memory, idx) => (
                                <div key={idx} className="flex items-start gap-2">
                                    <span className="text-gray-500 mt-1">•</span>
                                    <p className="text-gray-300">{memory.text}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
