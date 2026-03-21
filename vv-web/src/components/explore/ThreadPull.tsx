"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import ImageWithFallback from "@/components/ui/ImageWithFallback";
import { AttributePill } from "@/components/bridge";
import { ConnectionBadge } from "@/components/bridge";
import { PLATFORM_COLORS, PLATFORM_NAMES, ENTITY_TYPE_LABELS } from "@/styles/theme";
import { getProductBridges } from "@/lib/api";
import type { BridgeResult, ProductSummary } from "@/types";

interface ThreadStep {
    product: ProductSummary;
    bridge?: BridgeResult;       // the bridge that led TO this product
}

interface ThreadPullProps {
    startProduct: ProductSummary;
    initialBridges?: BridgeResult[];
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

export default function ThreadPull({ startProduct, initialBridges }: ThreadPullProps) {
    const [steps, setSteps] = useState<ThreadStep[]>([
        { product: startProduct }
    ]);
    const [loading, setLoading] = useState(false);
    const [exhausted, setExhausted] = useState(false);
    const visitedIds = new Set([startProduct.id]);

    // Track visited across renders
    for (const step of steps) {
        visitedIds.add(step.product.id);
    }

    const pullNext = useCallback(async () => {
        const lastStep = steps[steps.length - 1];
        const currentId = lastStep.product.id;

        setLoading(true);
        try {
            const data = await getProductBridges(currentId, { limit: 10 });

            // Find best bridge to an unvisited product
            let nextBridge: BridgeResult | null = null;
            let nextProduct: ProductSummary | null = null;

            for (const bridge of data.bridges) {
                const otherId = bridge.source.id === currentId ? bridge.target.id : bridge.source.id;
                if (!visitedIds.has(otherId)) {
                    nextBridge = bridge;
                    nextProduct = bridge.source.id === currentId ? bridge.target : bridge.source;
                    break;
                }
            }

            if (nextBridge && nextProduct) {
                visitedIds.add(nextProduct.id);
                setSteps(prev => [...prev, {
                    product: nextProduct!,
                    bridge: nextBridge!,
                }]);
            } else {
                setExhausted(true);
            }
        } catch {
            setExhausted(true);
        } finally {
            setLoading(false);
        }
    }, [steps]);

    return (
        <div className="max-w-[720px] mx-auto">
            {steps.map((step, i) => (
                <div key={step.product.id}>
                    {/* Edge — the connection that led here */}
                    {step.bridge && (
                        <Edge bridge={step.bridge} />
                    )}

                    {/* Node — the garment */}
                    <Node product={step.product} index={i} />
                </div>
            ))}

            {/* Continue / End */}
            <div className="mt-8 ml-[110px] border-l border-grey-200 pl-8 pb-8">
                {loading ? (
                    <p className="font-mono text-[11px] uppercase tracking-wider text-grey-400 animate-pulse">
                        Following the thread...
                    </p>
                ) : exhausted ? (
                    <div className="py-4">
                        <p className="font-editorial text-lg italic text-grey-400">
                            {steps.length} steps. Keep exploring?
                        </p>
                        <p className="mt-2 font-mono text-[10px] text-grey-400">
                            {steps.length} garments · {steps.length - 1} connections
                        </p>
                    </div>
                ) : (
                    <button
                        onClick={pullNext}
                        className="group flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.12em] text-grey-400 hover:text-black transition-colors"
                    >
                        Pull next
                        <span className="transition-transform group-hover:translate-x-1">→</span>
                    </button>
                )}
            </div>
        </div>
    );
}


function Node({ product, index }: { product: ProductSummary; index: number }) {
    const platformColor = PLATFORM_COLORS[product.platform] ?? "#6B6B6B";
    const platformName = PLATFORM_NAMES[product.platform] ?? product.platform;

    return (
        <div className="pt-10">
            <div className="font-mono text-[9px] uppercase tracking-[0.15em] text-grey-400 mb-4">
                {String(index + 1).padStart(2, '0')}
            </div>
            <div className="grid grid-cols-[180px_1fr] gap-8 items-start">
                <Link href={`/product/${product.id}`} className="block">
                    <div className="w-[180px] aspect-[3/4] bg-off-white overflow-hidden hover:opacity-90 transition-opacity">
                        {product.primary_image ? (
                            <ImageWithFallback
                                src={product.primary_image}
                                alt={product.display_title || product.title}
                                width={180}
                                height={240}
                                className="w-full h-full object-contain"
                            />
                        ) : (
                            <div className="w-full h-full bg-gradient-to-br from-grey-100 to-grey-200" />
                        )}
                    </div>
                </Link>
                <div className="pt-1">
                    <span
                        className="font-mono text-[10px] uppercase tracking-[0.12em]"
                        style={{ color: platformColor }}
                    >
                        {platformName}
                    </span>
                    <Link href={`/product/${product.id}`}>
                        <h3 className="mt-2 font-display text-xl font-semibold leading-tight text-black hover:underline">
                            {product.display_title || product.title}
                        </h3>
                    </Link>
                    <p className="mt-1 font-mono text-[11px] text-grey-600">
                        {[product.era, product.culture].filter(Boolean).join(" · ")}
                    </p>
                </div>
            </div>
        </div>
    );
}


function Edge({ bridge }: { bridge: BridgeResult }) {
    const shared = (bridge.shared_entities ?? {}) as Record<string, unknown>;
    const tags = entityTags(shared).slice(0, 4);
    const lineageRef = shared.lineage_reference as string | undefined;

    const distanceParts: string[] = [];
    if (bridge.year_gap != null && bridge.year_gap > 0) {
        distanceParts.push(`${bridge.year_gap} years`);
    }
    if (bridge.crossing_type?.includes("culture")) {
        distanceParts.push("cross-culture");
    }

    return (
        <div className="relative py-8 pl-8 ml-[110px] border-l border-grey-200">
            {/* Dot on the line */}
            <div className="absolute left-[-4px] bottom-0 w-[7px] h-[7px] rounded-full bg-grey-200" />

            {/* Lineage reference */}
            {lineageRef ? (
                <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-accent mb-3">
                    Lineage: &ldquo;{lineageRef}&rdquo;
                </p>
            ) : (
                <ConnectionBadge connectionMode={bridge.connection_mode} />
            )}

            {/* Entity tags */}
            {tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-2 mb-2">
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

            {/* Distance */}
            {distanceParts.length > 0 && (
                <p className="font-mono text-[10px] text-grey-400 mt-1">
                    {distanceParts.join(" · ")}
                </p>
            )}

            {/* Narrative */}
            {bridge.bridge_narrative && (
                <p className="mt-3 font-editorial text-[15px] italic leading-[1.5] text-dark">
                    {bridge.bridge_narrative}
                </p>
            )}
        </div>
    );
}
