import Link from "next/link";
import ImageWithFallback from "@/components/ui/ImageWithFallback";
import { cn } from "@/lib/utils";
import { BridgeResult } from "@/types";
import { scoreColorByValue } from "@/styles/theme";
import BridgeConnector from "./BridgeConnector";
import ConnectionBadge from "./ConnectionBadge";
import AttributePill from "./AttributePill";

interface BridgeCardCompactProps {
    bridge: BridgeResult;
    className?: string;
}

function parseSharedAttributes(attrs: Record<string, unknown>): { label: string; value: string }[] {
    return Object.entries(attrs)
        .filter(([, v]) => v != null && v !== "")
        .map(([key, value]) => ({
            label: key.replace(/_/g, " "),
            value: String(value),
        }));
}

export default function BridgeCardCompact({ bridge, className }: BridgeCardCompactProps) {
    const { source, target } = bridge;
    const attributes = parseSharedAttributes(bridge.shared_attributes).slice(0, 3);
    const score = Math.round(bridge.bridge_score * 100);

    return (
        <Link
            href={`/product/${source.id}`}
            className={cn(
                "snap-start block w-[240px] md:w-[280px] flex-shrink-0 overflow-hidden rounded-xl border border-border bg-warm-white shadow-card",
                className
            )}
        >
            {/* Image Pair */}
            <div className="relative flex h-[140px]">
                <div className="relative flex-1 overflow-hidden">
                    {source.primary_image ? (
                        <ImageWithFallback
                            src={source.primary_image ?? ""}
                            alt={source.title}
                            fill
                            className="object-cover"
                        />
                    ) : (
                        <div className="size-full bg-gradient-to-br from-border to-border-light" />
                    )}
                </div>
                <div className="relative flex-1 overflow-hidden">
                    {target.primary_image ? (
                        <ImageWithFallback
                            src={target.primary_image ?? ""}
                            alt={target.title}
                            fill
                            className="object-cover"
                        />
                    ) : (
                        <div className="size-full bg-gradient-to-br from-border to-border-light" />
                    )}
                </div>
                <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10">
                    <BridgeConnector variant="compact" />
                </div>
            </div>

            {/* Content */}
            <div className="px-3.5 py-3">

                {/* Era row + score */}
                <div className="flex items-center justify-between">
                    <span className="font-serif text-[11px] font-semibold text-charcoal-soft">
                        {source.era ?? "Unknown"} → {target.era ?? "Unknown"}
                    </span>
                    <span
                        className="font-serif text-sm font-bold"
                        style={{ color: scoreColorByValue(bridge.bridge_score) }}
                    >
                        {score}%
                    </span>
                </div>

                {/* Connection badges */}
                {(bridge.connection_mode || bridge.temporal_type) && (
                    <div className="mt-1.5">
                        <ConnectionBadge
                            connectionMode={bridge.connection_mode}
                            primaryAxis={bridge.primary_axis}
                            temporalType={bridge.temporal_type}
                        />
                    </div>
                )}

                {/* Narrative */}
                {bridge.bridge_narrative && (
                    <p className="mt-1.5 font-serif text-[11.5px] italic leading-[17.25px] text-charcoal-soft line-clamp-2">
                        {bridge.bridge_narrative}
                    </p>
                )}

                {/* Attribute pills */}
                {attributes.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                        {attributes.map((attr) => (
                            <AttributePill
                                key={attr.label}
                                label={attr.label}
                                value={attr.value}
                                size="sm"
                            />
                        ))}
                    </div>
                )}
            </div>
        </Link>
    );
}
