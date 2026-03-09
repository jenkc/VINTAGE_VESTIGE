import Link from "next/link";
import ImageWithFallback from "@/components/ui/ImageWithFallback";
import { cn } from "@/lib/utils";
import { BridgeResult } from "@/types";
import PlatformBadge from "./PlatformBadge";
import EraBadge from "./EraBadge";
import ScoreCircle from "./ScoreCircle";
import BridgeConnector from "./BridgeConnector";
import ConnectionBadge from "./ConnectionBadge";
import AttributePill from "./AttributePill";
import NarrativeBlock from "./NarrativeBlock";
import ScoreBreakdown from "./ScoreBreakdown";

interface BridgeCardFullProps {
  bridge: BridgeResult;
  className?: string;
}

// Helper function to parse shared attributes into label-value pairs
function parseSharedAttributes(attrs: Record<string, unknown>): { label: string, value: string }[] {
    return Object.entries(attrs)
        .filter(([, v]) => v != null && v !== "")
        .map(([key, value]) => ({
            label: key.replace(/_/g, " "),
            value: String(value),
        }));
}

export default function BridgeCardFull({ bridge, className }: BridgeCardFullProps) {
    const { source, target } = bridge;
    const attributes = parseSharedAttributes(bridge.shared_attributes);

    return (
        <div className={cn(
            "overflow-hidden rounded-2xl border border-border bg-warm-white shadow-card",
            className
        )}>
            {/* Image Pair */}
            <div className="relative flex h-[300px]">
                {/* Source Image */}
                <div className="relative flex-1 overflow-hidden">
                    {source.primary_image ? (
                        <ImageWithFallback
                            src={source.primary_image ?? ""}
                            alt={source.title}
                            fill
                            className="object-cover"
                            sizes="(max-width: 768px) 100vw, 340px"
                        />
                    ) : (
                        <div className="size-full bg-gradient-to-br from-border to-border-light" />
                    )}
                    <div className="absolute left-2 top-2">
                        <PlatformBadge platform={source.platform} />
                    </div>
                    <div className="absolute bottom-2 left-2">
                        <EraBadge era={source.era ?? "Unknown"} date={source.decade} />
                    </div>
                </div>

                {/* Target Image */}
                <div className="relative flex-1 overflow-hidden">
                    {target.primary_image ? (
                        <ImageWithFallback
                            src={target.primary_image ?? ""}
                            alt={target.title}
                            fill
                            className="object-cover"
                            sizes="(max-width: 768px) 100vw, 340px"
                        />
                    ) : (
                        <div className="size-full bg-gradient-to-br from-border to-border-light" />
                    )}
                    <div className="absolute right-2 top-2">
                        <PlatformBadge platform={target.platform} />
                    </div>
                    <div className="absolute bottom-2 right-2">
                        <EraBadge era={target.era ?? "Unknown"} date={target.decade} />
                    </div>
                </div>

                {/* Connector */}
                <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10">
                    <BridgeConnector variant="full" />
                </div>
            </div>

            {/* Content */}
            <div className="flex flex-col gap-3.5 px-5 pt-[18px] pb-5">    
                {/* Title row */}
                <div className="flex items-center gap-3">
                    <div className="flex-1">
                        <p className="font-serif text-[10px] font-semibold uppercase tracking-[2.5px] text-gold">
                            Historical
                        </p>
                        <Link href={`/product/${source.id}`} className="font-serif text-sm font-bold text-charcoal hover:underline">
                            {source.title}
                        </Link>
                    </div>
                    <ScoreCircle score={bridge.bridge_score} />
                    <div className="flex-1 text-right">
                        <p className="font-serif text-[10px] font-semibold uppercase tracking-[2.5px] text-gold">
                            Modern
                        </p>
                        <Link href={`/product/${target.id}`} className="font-serif text-sm font-bold text-charcoal hover:underline">
                            {target.title}
                        </Link>
                    </div>
                </div>

                {/* Badge row with contrast pair callout */}
                {(bridge.connection_mode || bridge.temporal_type) && (
                    <div className="flex flex-col gap-1.5">
                        <ConnectionBadge
                            connectionMode={bridge.connection_mode}
                            primaryAxis={bridge.primary_axis}
                            temporalType={bridge.temporal_type}
                        />
                        {bridge.connection_mode === "contrast" && bridge.contrast_pair && (
                            <p className="font-serif text-[11px] italic text-charcoal-soft">
                                {bridge.contrast_pair}
                            </p>
                        )}
                    </div>
                )}

                {/* Narrative */}
                {bridge.bridge_narrative && (
                    <NarrativeBlock narrative={bridge.bridge_narrative} />
                )}

                {/* Shared Design DNA */}
                {attributes.length > 0 && (
                    <div className="flex flex-col gap-2">
                        <p className="font-serif text-[9px] font-semibold uppercase tracking-[2.5px] text-muted">
                            Shared Design DNA
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                            {attributes.map(attr => (
                                <AttributePill key={attr.label} label={attr.label} value={attr.value} />
                            ))}
                        </div>
                    </div>        
                )}

                {/* Score Breakdown */}
                <div className="border-t border-border pt-[13px]">
                    <ScoreBreakdown
                        text={bridge.text_similarity}
                        image={bridge.image_similarity}
                        structural={bridge.structural_score}
                        variant="horizontal"
                    />
                </div>

            </div>

        </div>
    )
}