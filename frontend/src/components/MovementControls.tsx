import { Fragment, ReactNode, useState } from 'react';
import { useGameStore } from '../stores/gameStore';
import { useLocation } from '../hooks';
import { toTitleCase } from '../utils';
import { ArrowUp, ArrowDown, ArrowLeft, ArrowRight, Navigation, MapPin } from 'lucide-react';
import { ZoneConnection } from '../services/gameApi';

const directionIconMap: Record<string, ReactNode> = {
    n: <ArrowUp className="w-4 h-4" />,
    s: <ArrowDown className="w-4 h-4" />,
    e: <ArrowRight className="w-4 h-4" />,
    w: <ArrowLeft className="w-4 h-4" />,
};

interface ZoneTravelWidgetProps {
    connection: ZoneConnection;
    onTravel: (zoneId: string, method: string | null, entryLocationId: string | null) => void;
}

const ZoneTravelWidget = ({ connection, onTravel }: ZoneTravelWidgetProps) => {
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
                disabled={!connection.available}
                className="bg-gray-900 rounded-md px-3 py-2 text-left text-sm border border-gray-700 hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
                <div className="flex items-center gap-2">
                    <MapPin className="w-4 h-4" />
                    <span>Travel to {connection.zone_name}</span>
                </div>
            </button>
        );
    }

    // Complex widget with selectors
    return (
        <div className="bg-gray-900 rounded-md px-3 py-2 border border-gray-700">
            <div className="flex items-center gap-2 mb-2">
                <MapPin className="w-4 h-4 text-gray-400" />
                <span className="text-sm font-medium text-gray-200">Travel to {connection.zone_name}</span>
            </div>

            <div className="flex items-center gap-2 flex-wrap">
                {hasMultipleEntries && (
                    <select
                        value={selectedEntry || ''}
                        onChange={(e) => setSelectedEntry(e.target.value)}
                        className="flex-1 min-w-[120px] bg-gray-800 text-gray-200 text-xs rounded px-2 py-1 border border-gray-600 focus:border-blue-500 focus:outline-none"
                        disabled={!connection.available}
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
                        <span className="text-xs text-gray-400">via</span>
                        <select
                            value={selectedMethod || ''}
                            onChange={(e) => setSelectedMethod(e.target.value)}
                            className="flex-1 min-w-[100px] bg-gray-800 text-gray-200 text-xs rounded px-2 py-1 border border-gray-600 focus:border-blue-500 focus:outline-none"
                            disabled={!connection.available}
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
                    disabled={!connection.available}
                    className="ml-auto bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white text-xs px-3 py-1 rounded transition-colors"
                >
                    Go
                </button>
            </div>
        </div>
    );
};

export const MovementControls = () => {
    const { performMovement, performZoneTravel } = useGameStore();
    const location = useLocation();

    if (!location) {
        return null;
    }

    const exits = location.exits || [];
    const zoneConnections = location.zone_connections || [];

    const hasExits = exits.length > 0;
    const hasZoneConnections = zoneConnections.length > 0;

    if (!hasExits && !hasZoneConnections) {
        return null;
    }

    const handleLocalMove = (exitId: string | null, direction: string | null) => {
        if (exitId) {
            void performMovement(`move_${exitId}`);
        } else if (direction) {
            void performMovement(`direction_${direction}`);
        }
    };

    const handleZoneTravel = (zoneId: string, method: string | null, entryLocationId: string | null) => {
        void performZoneTravel(zoneId, method, entryLocationId);
    };

    return (
        <div className="bg-gray-800/50 backdrop-blur border border-gray-700 rounded-lg p-4">
            <h3 className="text-lg font-semibold mb-3 text-gray-100 flex items-center gap-2">
                <Navigation className="w-4 h-4" />
                Movement
            </h3>

            {hasExits && (
                <div className="grid grid-cols-2 gap-2 mb-3">
                    {exits.map((exit, index) => {
                        const icon = exit.direction ? directionIconMap[exit.direction.toLowerCase()] : null;
                        const label =
                            exit.direction && icon
                                ? `${exit.direction.toUpperCase()} – ${toTitleCase(exit.name)}`
                                : toTitleCase(exit.name);

                        return (
                            <button
                                key={`${exit.to ?? exit.direction ?? index}`}
                                onClick={() => handleLocalMove(exit.to, exit.direction)}
                                disabled={!exit.available}
                                className="bg-gray-900 rounded-md px-3 py-2 text-left text-sm border border-gray-700 hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                            >
                                <Fragment>
                                    {icon}
                                    <span>{label}</span>
                                </Fragment>
                            </button>
                        );
                    })}
                </div>
            )}

            {hasZoneConnections && (
                <div className="space-y-2">
                    {hasExits && (
                        <div className="border-t border-gray-600 pt-2 mb-2">
                            <span className="text-xs text-gray-400 uppercase tracking-wide">Zone Travel</span>
                        </div>
                    )}
                    {zoneConnections.map((connection) => (
                        <ZoneTravelWidget
                            key={connection.zone_id}
                            connection={connection}
                            onTravel={handleZoneTravel}
                        />
                    ))}
                </div>
            )}
        </div>
    );
};
