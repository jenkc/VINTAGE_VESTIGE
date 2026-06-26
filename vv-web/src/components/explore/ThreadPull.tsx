"use client";

import { useState, useCallback, useMemo, useEffect, useRef } from "react";
import Link from "next/link";
import ImageWithFallback from "@/components/ui/ImageWithFallback";
import { AttributePill } from "@/components/bridge";
import { ConnectionBadge } from "@/components/bridge";
import BranchTray from "@/components/explore/BranchTray";
import { PLATFORM_COLORS, PLATFORM_NAMES, ENTITY_TYPE_LABELS } from "@/styles/theme";
import { getProductBridges, getBridgeBetween } from "@/lib/api";
import { usePrefersReducedMotion } from "@/lib/useReducedMotion";
import { encodePath } from "@/lib/threadPath";
import type { BridgeResult, ProductSummary } from "@/types";

interface ThreadStep {
    product: ProductSummary;
    bridge?: BridgeResult;       // the bridge that led TO this product
}

interface ThreadPullProps {
    startProduct: ProductSummary;
    initialBridges?: BridgeResult[];
    /** Shared-link replay: full path of product ids, origin first. */
    initialPathIds?: number[];
}

// How many bridges to pull per node: #0 (first unvisited) is the auto-pick,
// the rest become the branch tray's runners-up. 14 gives a deep enough menu.
const BRIDGE_LIMIT = 14;

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

export default function ThreadPull({ startProduct, initialPathIds }: ThreadPullProps) {
    const prefersReducedMotion = usePrefersReducedMotion();

    const [steps, setSteps] = useState<ThreadStep[]>([
        { product: startProduct }
    ]);
    const [loading, setLoading] = useState(false);
    const [exhausted, setExhausted] = useState(false);

    // Branch tray: the full bridge list per node (cached so reopening / pulling
    // never re-hits the API), and the score-desc options for menus.
    const [optionsByNodeId, setOptionsByNodeId] = useState<Record<number, BridgeResult[]>>({});

    // Share affordance state
    const [copied, setCopied] = useState(false);

    // Shared-link replay state (so we don't replay twice, and can show progress)
    const [replaying, setReplaying] = useState(false);
    const replayDone = useRef(false);

    // The single source of truth for the cycle guard. Derived from the (one)
    // path, NEVER mutated — so a branch truncate automatically frees the
    // garments below it (they become revisitable) while everything currently
    // on the path stays blocked. This is the linchpin that makes branching
    // correct-by-construction (Decision #47).
    const visitedIds = useMemo(
        () => new Set(steps.map((s) => s.product.id)),
        [steps]
    );

    const lastStepRef = useRef<HTMLDivElement | null>(null);
    // Which step index just got appended (so only the newest animates).
    const [animIndex, setAnimIndex] = useState<number | null>(null);

    // ─── Shared-link replay ──────────────────────────────────────────
    // Walk consecutive id pairs, recover each connecting bridge via the
    // existing getBridgeBetween, and rebuild the full steps with edges so the
    // shared thread arrives with its "why" intact (Decision #49). Falls back
    // to a bare node if a pair's bridge can't be fetched, rather than failing.
    useEffect(() => {
        if (replayDone.current) return;
        if (!initialPathIds || initialPathIds.length < 2) return;
        // The first id must be the origin we already render.
        if (initialPathIds[0] !== startProduct.id) return;

        replayDone.current = true;
        let cancelled = false;

        (async () => {
            setReplaying(true);
            const rebuilt: ThreadStep[] = [{ product: startProduct }];
            for (let i = 1; i < initialPathIds.length; i++) {
                const prevId = initialPathIds[i - 1];
                const curId = initialPathIds[i];
                try {
                    const bridge = await getBridgeBetween(prevId, curId);
                    const target =
                        bridge.source.id === curId ? bridge.source : bridge.target;
                    rebuilt.push({ product: target, bridge });
                } catch {
                    // Bridge unavailable for this pair — keep the thread alive
                    // with a bare node rather than dropping the rest.
                    const prevStep = rebuilt[rebuilt.length - 1];
                    const guess =
                        prevStep.bridge &&
                        (prevStep.bridge.source.id === curId
                            ? prevStep.bridge.source
                            : prevStep.bridge.target.id === curId
                              ? prevStep.bridge.target
                              : null);
                    if (guess) rebuilt.push({ product: guess });
                    // if we can't even name the node, stop replaying gracefully
                    else break;
                }
                if (cancelled) return;
            }
            if (!cancelled) {
                setSteps(rebuilt);
                setReplaying(false);
            }
        })();

        return () => {
            cancelled = true;
        };
    }, [initialPathIds, startProduct]);

    // ─── Linear pull ─────────────────────────────────────────────────
    const pullNext = useCallback(async () => {
        const lastStep = steps[steps.length - 1];
        const currentId = lastStep.product.id;

        setLoading(true);
        try {
            // reuse cached bridges for this node if we already fetched them
            let bridges = optionsByNodeId[currentId];
            if (!bridges) {
                const data = await getProductBridges(currentId, { limit: BRIDGE_LIMIT });
                bridges = data.bridges;
                setOptionsByNodeId((prev) => ({ ...prev, [currentId]: bridges! }));
            }

            // Find best bridge to an unvisited product (highest-score-first).
            let nextBridge: BridgeResult | null = null;
            let nextProduct: ProductSummary | null = null;

            for (const bridge of bridges) {
                const otherId = bridge.source.id === currentId ? bridge.target.id : bridge.source.id;
                if (!visitedIds.has(otherId)) {
                    nextBridge = bridge;
                    nextProduct = bridge.source.id === currentId ? bridge.target : bridge.source;
                    break;
                }
            }

            if (nextBridge && nextProduct) {
                setAnimIndex(steps.length); // the index this new step will land at
                setSteps((prev) => [...prev, { product: nextProduct!, bridge: nextBridge! }]);
            } else {
                setExhausted(true);
            }
        } catch {
            setExhausted(true);
        } finally {
            setLoading(false);
        }
    }, [steps, optionsByNodeId, visitedIds]);

    // ─── Branch: replace the tail, then take the chosen alternative ───
    const chooseBranch = useCallback((fromIndex: number, bridge: BridgeResult) => {
        const fromId = steps[fromIndex].product.id;
        const other = bridge.source.id === fromId ? bridge.target : bridge.source;
        setAnimIndex(fromIndex + 1);
        setSteps((prev) => [...prev.slice(0, fromIndex + 1), { product: other, bridge }]);
        setExhausted(false);
    }, [steps]);

    // ─── Prefetch the last node's bridges so the tray is ready ────────
    const lastNode = steps[steps.length - 1];
    const lastNodeId = lastNode.product.id;
    useEffect(() => {
        if (optionsByNodeId[lastNodeId] || replaying) return;
        let cancelled = false;
        (async () => {
            try {
                const data = await getProductBridges(lastNodeId, { limit: BRIDGE_LIMIT });
                if (!cancelled) {
                    setOptionsByNodeId((prev) =>
                        prev[lastNodeId] ? prev : { ...prev, [lastNodeId]: data.bridges }
                    );
                }
            } catch {
                /* tray just won't show; pull still works on its own fetch */
            }
        })();
        return () => { cancelled = true; };
    }, [lastNodeId, optionsByNodeId, replaying]);

    // The runners-up for the last node: unvisited, auto-pick removed.
    const lastNodeBridges = optionsByNodeId[lastNodeId];
    const { autoPickAvailable, alternatives } = useMemo(() => {
        const list = lastNodeBridges ?? [];
        const unvisited = list.filter((b) => {
            const otherId = b.source.id === lastNodeId ? b.target.id : b.source.id;
            return !visitedIds.has(otherId);
        });
        return {
            autoPickAvailable: unvisited.length > 0,
            alternatives: unvisited.slice(1),
        };
    }, [lastNodeBridges, lastNodeId, visitedIds]);

    // ─── Smooth scroll-into-view on each new step ────────────────────
    useEffect(() => {
        if (animIndex == null) return;
        lastStepRef.current?.scrollIntoView({
            behavior: prefersReducedMotion ? "auto" : "smooth",
            block: "center",
        });
        // clear the animation flag after the draw completes so re-renders
        // don't re-animate (CSS `forwards` already holds the end state).
        const t = setTimeout(() => setAnimIndex(null), 900);
        return () => clearTimeout(t);
    }, [animIndex, prefersReducedMotion]);

    // ─── Share: a thread IS its path of ids ──────────────────────────
    const copyShareLink = useCallback(() => {
        const path = encodePath(steps.map((s) => s.product.id));
        const url = `${window.location.origin}/thread/${startProduct.id}?path=${path}`;
        navigator.clipboard?.writeText(url).catch(() => {});
        setCopied(true);
        setTimeout(() => setCopied(false), 2200);
    }, [steps, startProduct.id]);

    const startOver = useCallback(() => {
        setSteps([{ product: startProduct }]);
        setExhausted(false);
        setAnimIndex(null);
        // drop the ?path query without a navigation
        window.history.replaceState(null, "", `/thread/${startProduct.id}`);
        window.scrollTo({ top: 0, behavior: prefersReducedMotion ? "auto" : "smooth" });
    }, [startProduct, prefersReducedMotion]);

    const lastIdx = steps.length - 1;
    const eraSpan = useMemo(() => {
        const a = steps[0]?.product.era?.split("·")[0]?.trim();
        const b = steps[lastIdx]?.product.era?.split("·")[0]?.trim();
        return a && b && a !== b ? `${a} → ${b}` : null;
    }, [steps, lastIdx]);

    return (
        <div className="relative max-w-[720px] mx-auto">
            {/* ── Wayfinding: sticky left dot-rail (desktop only) ── */}
            {steps.length > 1 && (
                <nav
                    aria-label="Thread steps"
                    className="hidden lg:flex fixed left-6 top-1/2 -translate-y-1/2 z-40 flex-col items-center gap-3"
                >
                    {steps.map((step, i) => (
                        <button
                            key={step.product.id}
                            type="button"
                            onClick={() =>
                                document
                                    .getElementById(`thread-step-${i}`)
                                    ?.scrollIntoView({ behavior: prefersReducedMotion ? "auto" : "smooth", block: "center" })
                            }
                            aria-label={`Step ${i + 1}: ${step.product.display_title || step.product.title}`}
                            className="group relative w-[7px] h-[7px] rounded-full transition-transform hover:scale-150"
                            style={{
                                backgroundColor: i === lastIdx ? "#C4553A" : "#9B9B9B",
                                boxShadow: i === lastIdx ? "0 0 0 3px rgba(196,85,58,0.15)" : "none",
                                transform: i === lastIdx ? "scale(1.4)" : undefined,
                            }}
                        >
                            <span className="pointer-events-none absolute left-[18px] top-1/2 -translate-y-1/2 whitespace-nowrap border border-grey-200 bg-white px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.08em] text-grey-600 opacity-0 transition-opacity group-hover:opacity-100">
                                {String(i + 1).padStart(2, "0")} ·{" "}
                                {(step.product.display_title || step.product.title)
                                    .split(" ")
                                    .slice(0, 3)
                                    .join(" ")}
                            </span>
                        </button>
                    ))}
                    <span className="mt-1.5 font-mono text-[8px] tracking-[0.1em] text-grey-400 [writing-mode:vertical-rl]">
                        {steps.length}
                    </span>
                </nav>
            )}

            {steps.map((step, i) => (
                <div
                    key={step.product.id}
                    id={`thread-step-${i}`}
                    ref={i === lastIdx ? lastStepRef : undefined}
                    className={animIndex === i ? "thread-arriving" : undefined}
                >
                    {/* Edge — the connection that led here */}
                    {step.bridge && (
                        <Edge bridge={step.bridge} drawing={animIndex === i && !prefersReducedMotion} />
                    )}

                    {/* Node — the garment */}
                    <Node product={step.product} index={i} />
                </div>
            ))}

            {/* Continue / Branch / End */}
            <div className="mt-8 ml-[110px] border-l border-grey-200 pl-8 pb-8">
                {loading || replaying ? (
                    <p className="font-mono text-[11px] uppercase tracking-wider text-grey-400 animate-pulse">
                        Following the thread...
                    </p>
                ) : exhausted || !autoPickAvailable ? (
                    <ThreadEnd
                        count={steps.length}
                        eraSpan={eraSpan}
                        alternatives={alternatives}
                        lastNodeId={lastNodeId}
                        onBranch={(bridge) => chooseBranch(lastIdx, bridge)}
                        onShare={copyShareLink}
                        copied={copied}
                        onStartOver={startOver}
                        startProductId={startProduct.id}
                    />
                ) : (
                    <div className="relative">
                        {/* a short loose "slack" of thread inviting the pull */}
                        <span
                            aria-hidden
                            className="pointer-events-none absolute left-[-32px] -top-8 h-9 w-px bg-gradient-to-b from-grey-200 to-transparent"
                        />
                        <button
                            onClick={pullNext}
                            className="group flex items-center gap-2.5 font-mono text-[11px] uppercase tracking-[0.14em] text-grey-600 hover:text-black transition-colors"
                        >
                            <span className="inline-block h-px w-[26px] bg-grey-400 transition-all duration-200 group-hover:w-10 group-hover:bg-accent" />
                            ↦ pull
                            <span className="inline-block transition-transform duration-200 group-hover:translate-x-1.5">→</span>
                        </button>

                        {/* Branch tray — last node's runners-up */}
                        {alternatives.length > 0 && (
                            <BranchTray
                                fromId={lastNodeId}
                                alternatives={alternatives}
                                onPick={(bridge) => chooseBranch(lastIdx, bridge)}
                            />
                        )}
                    </div>
                )}
            </div>

            {/* ── Sticky share / overview toolbar ── */}
            {steps.length > 1 && (
                <div className="fixed bottom-5 left-1/2 z-40 flex -translate-x-1/2 items-center gap-1 rounded border border-grey-200 bg-white/95 p-1.5 shadow-[0_4px_20px_rgba(0,0,0,0.06)] backdrop-blur">
                    <span className="whitespace-nowrap px-3 py-1.5 font-mono text-[10px] tracking-[0.06em] text-grey-600">
                        {steps.length} garment{steps.length > 1 ? "s" : ""} · {steps.length - 1} connection
                        {steps.length - 1 !== 1 ? "s" : ""}
                    </span>
                    <span className="h-[18px] w-px bg-grey-200" />
                    <button
                        onClick={copyShareLink}
                        className={`whitespace-nowrap rounded px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.1em] transition-colors hover:bg-grey-100 ${copied ? "text-accent" : "text-grey-600 hover:text-black"}`}
                    >
                        {copied ? "✓ Link copied" : "↗ Share thread"}
                    </button>
                    <span className="h-[18px] w-px bg-grey-200" />
                    <button
                        onClick={startOver}
                        className="whitespace-nowrap rounded px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.1em] text-grey-600 transition-colors hover:bg-grey-100 hover:text-black"
                    >
                        ↺ Start over
                    </button>
                </div>
            )}
        </div>
    );
}


function ThreadEnd({
    count,
    eraSpan,
    alternatives,
    lastNodeId,
    onBranch,
    onShare,
    copied,
    onStartOver,
    startProductId,
}: {
    count: number;
    eraSpan: string | null;
    alternatives: BridgeResult[];
    lastNodeId: number;
    onBranch: (bridge: BridgeResult) => void;
    onShare: () => void;
    copied: boolean;
    onStartOver: () => void;
    startProductId: number;
}) {
    return (
        <div className="py-2">
            <p className="font-editorial text-[22px] italic leading-snug text-dark max-w-[480px]">
                The thread ends here — for now. {count} garment{count > 1 ? "s" : ""},{" "}
                {count - 1} connection{count - 1 !== 1 ? "s" : ""}
                {eraSpan ? `, ${eraSpan}` : ""}.
            </p>
            <p className="mt-1.5 font-mono text-[10px] tracking-[0.08em] text-grey-400">
                No unvisited bridge from this garment. The next move is yours.
            </p>

            {/* Branch from here if the last node still has unvisited alternatives */}
            {alternatives.length > 0 && (
                <div className="mt-6">
                    <BranchTray fromId={lastNodeId} alternatives={alternatives} onPick={onBranch} />
                </div>
            )}

            <div className="mt-7 flex flex-wrap gap-3">
                <button
                    onClick={onShare}
                    className={`rounded-sm border px-5 py-3 font-mono text-[11px] uppercase tracking-[0.12em] transition-colors ${copied ? "border-accent text-accent" : "border-grey-200 text-black hover:border-black"}`}
                >
                    {copied ? "✓ Link copied" : "↗ Share this thread"}
                </button>
                <button
                    onClick={onStartOver}
                    className="rounded-sm border border-grey-200 px-5 py-3 font-mono text-[11px] uppercase tracking-[0.12em] text-black transition-colors hover:border-black"
                >
                    ↺ Start a new thread
                </button>
                <Link
                    href={`/product/${startProductId}`}
                    className="inline-block rounded-sm border border-grey-200 px-5 py-3 font-mono text-[11px] uppercase tracking-[0.12em] text-black transition-colors hover:border-black"
                >
                    Return to garment
                </Link>
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
            <div className="grid grid-cols-[180px_1fr] gap-8 items-start max-[520px]:grid-cols-1 max-[520px]:gap-4">
                <Link href={`/product/${product.id}`} className="block">
                    <div className="w-[180px] aspect-[3/4] bg-off-white overflow-hidden hover:opacity-90 transition-opacity max-[520px]:w-full">
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


function Edge({ bridge, drawing }: { bridge: BridgeResult; drawing: boolean }) {
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
        <div className={`relative py-8 pl-8 ml-[110px] ${drawing ? "thread-drawing" : ""}`}>
            {/* The connector that draws itself — SVG line so stroke-dashoffset
                can animate. Replaces the old static border-l (same 110px gutter). */}
            <svg
                className="thread-line absolute left-0 top-0 bottom-0 w-0.5 overflow-visible"
                aria-hidden
                preserveAspectRatio="none"
            >
                <line
                    className="thread-line-path"
                    x1="1"
                    y1="0"
                    x2="1"
                    y2="100%"
                    stroke="#E0E0E0"
                    strokeWidth="1.5"
                    fill="none"
                />
            </svg>

            {/* The bead that rides the line down, then settles into the dot */}
            <span
                className="thread-bead absolute left-[-3.5px] w-2 h-2 rounded-full bg-accent"
                aria-hidden
            />
            {/* Static settled dot (the bead lands here; also the reduced-motion state) */}
            <div className="absolute left-[-4px] bottom-0 w-[7px] h-[7px] rounded-full bg-grey-200" />

            <div className="thread-meta">
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
        </div>
    );
}
