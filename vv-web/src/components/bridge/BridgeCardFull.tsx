import Link from "next/link";
import ImageWithFallback from "@/components/ui/ImageWithFallback";
import { cn } from "@/lib/utils";
import { BridgeResult } from "@/types";
import { ENTITY_TYPE_LABELS } from "@/styles/theme";
import PlatformBadge from "./PlatformBadge";
import EraBadge from "./EraBadge";
import ConnectionBadge from "./ConnectionBadge";
import AttributePill from "./AttributePill";
import NarrativeBlock from "./NarrativeBlock";
import ScoreBreakdown from "./ScoreBreakdown";

interface BridgeCardFullProps {
  bridge: BridgeResult;
  className?: string;
}

/** Format shared entities into displayable entity tags */
function entityTags(shared: Record<string, unknown>): { label: string; value: string }[] {
    const tags: { label: string; value: string }[] = [];
    for (const [key, val] of Object.entries(shared)) {
        if (!Array.isArray(val)) continue;
        const label = ENTITY_TYPE_LABELS[key] || key.replace(/_/g, " ");
        for (const v of val) {
            tags.push({ label, value: String(v) });
        }
    }
    return tags;
}

/** Format distance between two items */
function distanceLabel(bridge: BridgeResult): string {
    const parts: string[] = [];
    if (bridge.year_gap != null && bridge.year_gap > 0) {
        parts.push(`${bridge.year_gap} years`);
    } else if (bridge.year_gap === 0) {
        parts.push("same era");
    }
    if (bridge.crossing_type?.includes("culture") && bridge.crossing_type?.includes("category")) {
        parts.push("cross-culture · cross-category");
    } else if (bridge.crossing_type?.includes("culture")) {
        parts.push("cross-culture");
    } else if (bridge.crossing_type === "cross_category") {
        parts.push("cross-category");
    }
    return parts.join(" · ") || "";
}

export default function BridgeCardFull({ bridge, className }: BridgeCardFullProps) {
    const { source, target } = bridge;
    const tags = entityTags((bridge.shared_entities ?? {}) as Record<string, unknown>);
    const distance = distanceLabel(bridge);
    const lineageRef = bridge.shared_entities?.lineage_reference as string | undefined;

    return (
        <div className={cn(
            "max-w-[600px] overflow-hidden border-b border-grey-200",
            className
        )}>
            {/* Image Pair */}
            <div className="relative flex aspect-[2/1]">
                <Link href={`/product/${source.id}`} className="relative flex-1 overflow-hidden bg-off-white transition-opacity hover:opacity-90">
                    {source.primary_image ? (
                        <ImageWithFallback
                            src={source.primary_image}
                            alt={source.display_title || source.title}
                            fill
                            className="object-contain"
                            sizes="(max-width: 768px) 50vw, 300px"
                        />
                    ) : (
                        <div className="size-full bg-gradient-to-br from-grey-100 to-grey-200" />
                    )}
                </Link>

                <Link href={`/product/${target.id}`} className="relative flex-1 overflow-hidden bg-off-white transition-opacity hover:opacity-90">
                    {target.primary_image ? (
                        <ImageWithFallback
                            src={target.primary_image}
                            alt={target.display_title || target.title}
                            fill
                            className="object-contain"
                            sizes="(max-width: 768px) 50vw, 300px"
                        />
                    ) : (
                        <div className="size-full bg-gradient-to-br from-grey-100 to-grey-200" />
                    )}
                </Link>

                {/* Pull the thread from THIS bridge — seeds the thread with source → target */}
                <Link
                    href={`/thread/${source.id}?path=${source.id}.${target.id}`}
                    aria-label="Pull the thread from this connection"
                    className="absolute bottom-2 left-1/2 -translate-x-1/2 inline-flex items-center gap-1.5 rounded-full border border-grey-200 bg-white/90 px-3 py-1 font-mono text-[9px] uppercase tracking-[0.1em] text-grey-600 backdrop-blur-sm transition-colors hover:border-accent hover:bg-white hover:text-accent"
                >
                    <span aria-hidden>↦</span>
                    Pull the thread
                </Link>
            </div>

            {/* Metadata row — platform + era under each image, aligned in two columns */}
            <div className="grid grid-cols-2 gap-px border-t border-grey-200 bg-grey-200">
                <div className="flex flex-col gap-1 bg-white px-5 py-3">
                    <PlatformBadge platform={source.platform} />
                    <EraBadge era={source.era ?? "Unknown"} date={source.decade} />
                </div>
                <div className="flex flex-col gap-1 bg-white px-5 py-3">
                    <PlatformBadge platform={target.platform} />
                    <EraBadge era={target.era ?? "Unknown"} date={target.decade} />
                </div>
            </div>

            {/* Content */}
            <div className="flex flex-col gap-3.5 px-5 pt-[18px] pb-5">
                {/* Title row */}
                <div className="flex items-center gap-3">
                    <div className="flex-1">
                        <Link href={`/product/${source.id}`} className="font-display text-sm font-bold text-black hover:underline">
                            {source.display_title || source.title}
                        </Link>
                    </div>
                    {bridge.bridge_score != null && (
                        <span className="font-mono text-sm text-grey-600">
                            {Math.round(bridge.bridge_score * 100)}%
                        </span>
                    )}
                    <div className="flex-1 text-right">
                        <Link href={`/product/${target.id}`} className="font-display text-sm font-bold text-black hover:underline">
                            {target.display_title || target.title}
                        </Link>
                    </div>
                </div>

                {/* Entity tags — the "why" */}
                {tags.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                        {tags.map((tag, i) => (
                            <AttributePill key={`${tag.label}-${tag.value}-${i}`} label={tag.label} value={tag.value} />
                        ))}
                    </div>
                )}

                {/* Distance + connection mode */}
                <div className="flex items-center gap-3">
                    <ConnectionBadge connectionMode={bridge.connection_mode} />
                    {distance && (
                        <span className="font-mono text-[10px] text-grey-400">
                            {distance}
                        </span>
                    )}
                    {bridge.directed && (
                        <span className="font-mono text-[10px] text-accent">→ directed</span>
                    )}
                </div>

                {/* Lineage reference */}
                {lineageRef && (
                    <p className="font-mono text-[10px] uppercase tracking-wider text-accent">
                        Lineage: &ldquo;{lineageRef}&rdquo;
                    </p>
                )}

                {/* Narrative */}
                {bridge.bridge_narrative && (
                    <NarrativeBlock narrative={bridge.bridge_narrative} />
                )}

                {/* Score Breakdown */}
                <div className="border-t border-grey-200 pt-[13px]">
                    <ScoreBreakdown
                        text={bridge.text_similarity}
                        image={bridge.image_similarity}
                        entity={bridge.entity_score}
                        variant="horizontal"
                    />
                </div>
            </div>
        </div>
    );
}
