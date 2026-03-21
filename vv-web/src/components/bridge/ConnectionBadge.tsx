import { CONNECTION_MODE_COLORS, CONNECTION_MODE_LABELS } from "@/styles/theme";

interface ConnectionBadgeProps {
    connectionMode: string | null;
}

export default function ConnectionBadge({
    connectionMode,
}: ConnectionBadgeProps) {
    if (!connectionMode) return null;
    const modeColor = CONNECTION_MODE_COLORS[connectionMode] ?? "#9B9B9B";
    const modeLabel = CONNECTION_MODE_LABELS[connectionMode] ?? connectionMode;

    return (
        <span
            className="font-mono text-[10px] uppercase tracking-wider"
            style={{ color: modeColor }}
        >
            {modeLabel}
        </span>
    );
}
