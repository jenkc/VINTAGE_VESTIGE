import Link from "next/link";
import ImageWithFallback from "@/components/ui/ImageWithFallback";
import { cn } from "@/lib/utils";
import { BridgeResult } from "@/types";
import { ENTITY_TYPE_LABELS } from "@/styles/theme";
import ConnectionBadge from "./ConnectionBadge";
import AttributePill from "./AttributePill";

interface BridgeCardCompactProps {
    bridge: BridgeResult;
    className?: string;
}

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

export default function BridgeCardCompact({ bridge, className }: BridgeCardCompactProps) {
    const { source, target } = bridge;
    const tags = entityTags((bridge.shared_entities ?? {}) as Record<string, unknown>).slice(0, 3);
    const score = bridge.bridge_score != null ? Math.round(bridge.bridge_score * 100) : null;

    return (
        <div
            className={cn(
                "snap-start block w-[240px] md:w-[280px] flex-shrink-0 overflow-hidden border-b border-grey-200",
                className
            )}
        >
            {/* Image Pair — links to each product; thread pill is a sibling (no nested <a>) */}
            <div className="relative flex h-[140px]">
                <Link href={`/product/${source.id}`} className="relative flex-1 overflow-hidden">
                    {source.primary_image ? (
                        <ImageWithFallback
                            src={source.primary_image}
                            alt={source.display_title || source.title}
                            fill
                            className="object-cover"
                        />
                    ) : (
                        <div className="size-full bg-gradient-to-br from-grey-100 to-grey-200" />
                    )}
                </Link>
                <Link href={`/product/${target.id}`} className="relative flex-1 overflow-hidden">
                    {target.primary_image ? (
                        <ImageWithFallback
                            src={target.primary_image}
                            alt={target.display_title || target.title}
                            fill
                            className="object-cover"
                        />
                    ) : (
                        <div className="size-full bg-gradient-to-br from-grey-100 to-grey-200" />
                    )}
                </Link>

                {/* Pull the thread from THIS bridge — seeds source → target */}
                <Link
                    href={`/thread/${source.id}?path=${source.id}.${target.id}`}
                    aria-label="Pull the thread from this connection"
                    className="absolute bottom-1.5 left-1/2 -translate-x-1/2 inline-flex items-center gap-1 rounded-full border border-grey-200 bg-white/90 px-2.5 py-0.5 font-mono text-[8px] uppercase tracking-[0.1em] text-grey-600 backdrop-blur-sm transition-colors hover:border-accent hover:bg-white hover:text-accent"
                >
                    <span aria-hidden>↦</span>
                    Thread
                </Link>
            </div>

            {/* Content — links to the source product */}
            <Link href={`/product/${source.id}`} className="block px-3.5 py-3">
                {/* Era + distance + score */}
                <div className="flex items-center justify-between">
                    <span className="font-mono text-[10px] text-grey-600">
                        {source.era ?? "?"} → {target.era ?? "?"}
                        {bridge.year_gap != null && bridge.year_gap > 0 && (
                            <> · {bridge.year_gap}yr</>
                        )}
                    </span>
                    {score != null && (
                        <span className="font-mono text-xs text-grey-600">
                            {score}%
                        </span>
                    )}
                </div>

                {/* Connection mode */}
                {bridge.connection_mode && (
                    <div className="mt-1.5">
                        <ConnectionBadge connectionMode={bridge.connection_mode} />
                    </div>
                )}

                {/* Narrative */}
                {bridge.bridge_narrative && (
                    <p className="mt-1.5 font-editorial text-[11.5px] italic leading-[17.25px] text-dark line-clamp-2">
                        {bridge.bridge_narrative}
                    </p>
                )}

                {/* Entity tags */}
                {tags.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                        {tags.map((tag, i) => (
                            <AttributePill
                                key={`${tag.label}-${tag.value}-${i}`}
                                label={tag.label}
                                value={tag.value}
                                size="sm"
                            />
                        ))}
                    </div>
                )}
            </Link>
        </div>
    );
}
