/**
 * Skeleton loader components for displaying loading states.
 * Provides visual feedback while content is being fetched.
 */

interface SkeletonProps {
    className?: string;
}

/**
 * Basic skeleton element (animated gray box).
 */
export const Skeleton = ({ className = '' }: SkeletonProps) => (
    <div className={`animate-pulse bg-gray-700 rounded ${className}`} />
);

/**
 * Skeleton for a text line.
 */
export const SkeletonText = ({ width = 'full' }: { width?: 'full' | '3/4' | '1/2' | '1/4' }) => {
    const widthClasses = {
        full: 'w-full',
        '3/4': 'w-3/4',
        '1/2': 'w-1/2',
        '1/4': 'w-1/4',
    };

    return <Skeleton className={`h-4 ${widthClasses[width]}`} />;
};

/**
 * Skeleton for a panel/card.
 */
export const SkeletonPanel = () => (
    <div className="bg-gray-800/50 backdrop-blur border border-gray-700 rounded-lg p-4 space-y-3">
        <Skeleton className="h-6 w-1/3" />
        <SkeletonText width="full" />
        <SkeletonText width="3/4" />
        <SkeletonText width="1/2" />
    </div>
);

/**
 * Skeleton for a meter display.
 */
export const SkeletonMeter = () => (
    <div className="space-y-2">
        <div className="flex items-center justify-between">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-8" />
        </div>
        <Skeleton className="h-2 w-full" />
    </div>
);

/**
 * Skeleton for character card.
 */
export const SkeletonCharacter = () => (
    <div className="bg-gray-900/50 rounded border border-gray-700 p-3 space-y-3">
        <Skeleton className="h-5 w-32" />
        <SkeletonText width="full" />
        <div className="space-y-2">
            <SkeletonMeter />
            <SkeletonMeter />
        </div>
    </div>
);
