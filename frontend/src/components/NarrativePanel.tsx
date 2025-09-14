import { useEffect, useRef } from 'react';

type Props = {
    narrative: string[];
};

export const NarrativePanel = ({ narrative }: Props) => {
    const bottomRef = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        const element = bottomRef.current;
        if (element) {
            element.scrollIntoView({ behavior: 'smooth' });
        }
    }, [narrative]);

    return (
        <div className="bg-gray-800/50 backdrop-blur border border-gray-700 rounded-lg p-6 h-[500px] overflow-y-auto">
            <div className="space-y-4">
                {narrative.map((text, index) => (
                    <div key={index} className="text-gray-100 leading-relaxed animate-fadeIn">
                        {text.split('\n').map((paragraph, pIndex) => (
                            <p key={pIndex} className="mb-3 text-lg">
                                {paragraph}
                            </p>
                        ))}
                        {index < narrative.length - 1 && (
                            <div className="border-b border-gray-700 my-4" />
                        )}
                    </div>
                ))}
                <div ref={bottomRef} />
            </div>
        </div>
    );
};