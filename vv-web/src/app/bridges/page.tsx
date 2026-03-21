"use client";

import { useState, useEffect } from "react";
import { getTopBridges } from "@/lib/api";
import { BridgeCardFull } from "@/components/bridge";
import type { BridgeResult } from "@/types";

const CONNECTION_MODES = [
    { value: "lineage", label: "Lineage" },
    { value: "shared_entity", label: "Shared" },
    { value: "visual_echo", label: "Visual Echo" },
] as const;

const CROSSING_TYPES = [
    { value: "cross_culture", label: "Cross-culture" },
    { value: "cross_category", label: "Cross-category" },
    { value: "cross_category_culture", label: "Both" },
] as const;

const TIME_FILTERS = [
    { value: 30, label: "30+ years" },
    { value: 80, label: "80+ years" },
] as const;

// Presets — each sets filters to a specific combination
const PRESETS = [
    { label: "Same Maker", filters: { connection_mode: "shared_entity" as const } },
    { label: "Longest Echoes", filters: { min_year_gap: 80 } },
    { label: "Lineage", filters: { connection_mode: "lineage" as const } },
    { label: "Visual Surprises", filters: { connection_mode: "visual_echo" as const } },
] as const;

export default function ConnectionsPage() {
    const [bridges, setBridges] = useState<BridgeResult[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);

    // Filters
    const [connectionMode, setConnectionMode] = useState<string | null>(null);
    const [crossingType, setCrossingType] = useState<string | null>(null);
    const [minYearGap, setMinYearGap] = useState<number | null>(null);

    // Fetch bridges when filters change
    useEffect(() => {
        setLoading(true);
        let cancelled = false;
        getTopBridges({
            connection_mode: connectionMode ?? undefined,
            crossing_type: crossingType ?? undefined,
            min_year_gap: minYearGap ?? undefined,
            limit: 20,
        }).then((data) => {
            if (cancelled) return;
            setBridges(data.bridges);
            setTotal(data.total);
            setLoading(false);
        });
        return () => { cancelled = true; };
    }, [connectionMode, crossingType, minYearGap]);

    const toggle = (
        current: string | null,
        value: string,
        setter: (v: string | null) => void
    ) => setter(current === value ? null : value);

    const toggleNum = (
        current: number | null,
        value: number,
        setter: (v: number | null) => void
    ) => setter(current === value ? null : value);

    const applyPreset = (preset: typeof PRESETS[number]) => {
        const f = preset.filters as Record<string, unknown>;
        setConnectionMode((f.connection_mode as string) ?? null);
        setCrossingType(null);
        setMinYearGap((f.min_year_gap as number) ?? null);
    };

    const clearFilters = () => {
        setConnectionMode(null);
        setCrossingType(null);
        setMinYearGap(null);
    };

    const hasFilters = connectionMode || crossingType || minYearGap;

    return (
        <div className="mx-auto max-w-[1200px] px-6 py-12 md:px-12">
            {/* Header */}
            <h1 className="font-display text-[clamp(36px,6vw,56px)] font-bold uppercase tracking-tight text-black">
                Connections
            </h1>
            <p className="mt-2 font-mono text-[11px] uppercase tracking-[0.1em] text-grey-400">
                {total.toLocaleString()} paths between garments across 500 years
            </p>

            {/* Filter bar */}
            <div className="mt-8 flex flex-wrap gap-8 border-b border-grey-200 pb-6">
                {/* Type */}
                <div>
                    <p className="mb-2.5 font-mono text-[9px] uppercase tracking-[0.15em] text-grey-400">
                        Type
                    </p>
                    <div className="flex gap-4">
                        {CONNECTION_MODES.map((m) => (
                            <button
                                key={m.value}
                                onClick={() => toggle(connectionMode, m.value, setConnectionMode)}
                                className={`border-b pb-1 font-mono text-[11px] uppercase tracking-[0.1em] transition-all ${
                                    connectionMode === m.value
                                        ? "border-black text-black"
                                        : "border-transparent text-grey-400 hover:text-black"
                                }`}
                            >
                                {m.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Time */}
                <div>
                    <p className="mb-2.5 font-mono text-[9px] uppercase tracking-[0.15em] text-grey-400">
                        Time
                    </p>
                    <div className="flex gap-4">
                        {TIME_FILTERS.map((t) => (
                            <button
                                key={t.value}
                                onClick={() => toggleNum(minYearGap, t.value, setMinYearGap)}
                                className={`border-b pb-1 font-mono text-[11px] uppercase tracking-[0.1em] transition-all ${
                                    minYearGap === t.value
                                        ? "border-black text-black"
                                        : "border-transparent text-grey-400 hover:text-black"
                                }`}
                            >
                                {t.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Crossing */}
                <div>
                    <p className="mb-2.5 font-mono text-[9px] uppercase tracking-[0.15em] text-grey-400">
                        Crossing
                    </p>
                    <div className="flex gap-4">
                        {CROSSING_TYPES.map((c) => (
                            <button
                                key={c.value}
                                onClick={() => toggle(crossingType, c.value, setCrossingType)}
                                className={`border-b pb-1 font-mono text-[11px] uppercase tracking-[0.1em] transition-all ${
                                    crossingType === c.value
                                        ? "border-black text-black"
                                        : "border-transparent text-grey-400 hover:text-black"
                                }`}
                            >
                                {c.label}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* Presets */}
            <div className="mt-5 flex flex-wrap gap-3">
                {PRESETS.map((p) => (
                    <button
                        key={p.label}
                        onClick={() => applyPreset(p)}
                        className="border border-grey-200 px-3.5 py-1.5 font-mono text-[10px] uppercase tracking-[0.1em] text-grey-600 transition-all hover:border-black hover:text-black"
                        style={{ borderRadius: '2px' }}
                    >
                        {p.label}
                    </button>
                ))}
                <button
                    onClick={() => {
                        clearFilters();
                        // Surprise me — random offset
                        const randomOffset = Math.floor(Math.random() * 100);
                        getTopBridges({ limit: 20, offset: randomOffset }).then((data) => {
                            setBridges(data.bridges);
                            setTotal(data.total);
                        });
                    }}
                    className="border border-accent px-3.5 py-1.5 font-mono text-[10px] uppercase tracking-[0.1em] text-accent transition-all hover:bg-accent hover:text-white"
                    style={{ borderRadius: '2px' }}
                >
                    Surprise Me ↗
                </button>
                {hasFilters && (
                    <button
                        onClick={clearFilters}
                        className="px-3.5 py-1.5 font-mono text-[10px] uppercase tracking-[0.1em] text-grey-400 hover:text-black"
                    >
                        Clear ×
                    </button>
                )}
            </div>

            {/* Results */}
            <div className="mt-10 grid gap-8 md:grid-cols-2">
                {loading ? (
                    <p className="py-20 text-center font-mono text-[11px] uppercase tracking-wider text-grey-400">
                        Loading connections...
                    </p>
                ) : bridges.length === 0 ? (
                    <p className="py-20 text-center font-mono text-[11px] uppercase tracking-wider text-grey-400">
                        No connections match these filters.
                    </p>
                ) : (
                    bridges.map((b) => (
                        <BridgeCardFull key={b.id} bridge={b} />
                    ))
                )}
            </div>
        </div>
    );
}
