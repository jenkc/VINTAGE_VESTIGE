import { CONNECTION_MODE_COLORS, CONNECTION_MODE_LABELS } from "@/styles/theme";

interface ConnectionBadgeProps {
    connectionMode: string | null;
    primaryAxis: string | null;
    temporalType: string | null;
}

export default function ConnectionBadge({
    connectionMode, primaryAxis, temporalType
}: ConnectionBadgeProps) {
    if (!connectionMode && !temporalType) return null;
    const modeColor = connectionMode ? CONNECTION_MODE_COLORS[connectionMode] ?? "#8A7E74" : "#8A7E74";
    const modeLabel = connectionMode ? CONNECTION_MODE_LABELS[connectionMode] ?? connectionMode : null;

    return (
        <div className="flex items-center gap-1.5">
            {modeLabel && (
                <span
                    className="inline-block rounded-full px-2.5 py-0.5 font-serif text-[10px] font-semibold uppercase tracking-[1.5px] text-warm-white"
                    style={{ backgroundColor: modeColor }}
                >
                    {modeLabel}
                </span>
            )}
            {primaryAxis && (
                <span className="inline-block rounded-full border border-border px-2 py-0.5 font-serif text-[10px] uppercase tracking-[1.5px] text-muted">
                    {primaryAxis}
                </span>
            )}
            {temporalType && (
                <span className="inline-block rounded-full border border-border px-2 py-0.5 font-serif text-[10px] uppercase tracking-[1.5px] text-charcoal-soft">
                    {temporalType}
                </span>
            )}
        </div>
    );
}
