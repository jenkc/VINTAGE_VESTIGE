"use client";

import { useState, useEffect } from "react";
import { getTopBridges, getExploreFunctions } from "@/lib/api";
import { BridgeCardFull } from "@/components/bridge";
import type { BridgeResult, FunctionSummary } from "@/types";

const CONNECTION_MODES = ["contrast", "resonance", "affinity"] as const;
const TEMPORAL_TYPES = ["echo", "transmission", "continuation", "contemporary"] as const;
const AXES = ["volume", "ornament", "body", "register"] as const;

export default function BridgePage() {
    const [bridges, setBridges] = useState<BridgeResult[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [functions, setFunctions] = useState<FunctionSummary[]>([]);

    // Filters
    const [connectionMode, setConnectionMode] = useState<string | null>(null);
    const [temporalType, setTemporalType] = useState<string | null>(null);
    const [primaryAxis, setPrimaryAxis] = useState<string | null>(null);
    const [sharedFunction, setSharedFunction] = useState<string | null>(null);

    // Load function list for dropdown
    useEffect(() => {
        getExploreFunctions().then((data) => setFunctions(data.functions));
    }, []);

    // Fetch bridges when filters change
    useEffect(() => {
        setLoading(true);
        getTopBridges({
            connection_mode: connectionMode ?? undefined,
            temporal_type: temporalType ?? undefined,
            primary_axis: primaryAxis ?? undefined,
            shared_function: sharedFunction ?? undefined,
            limit: 20,
        }).then((data) => {
            setBridges(data.bridges);
            setTotal(data.total);
            setLoading(false);
        })
    }, [connectionMode, temporalType, primaryAxis, sharedFunction]);

    // Toggle helper: click same value = clear filter
    const toggle = (
        current: string | null,
        value: string,
        setter: (v: string | null) => void
    ) => setter(current === value ? null : value);

    return (
        <div className="mx-auto max-w-6xl px-4 py-10">
            <h1 className="font-serif text-3xl font-bold text-charcoal">
                Style Bridges
            </h1>
            <p className="mt-2 text-sm text-charcoal-soft">
                {total} connections across eras, cultures, and categories.
            </p>

            {/* Filters */}
            <div className="mt-6 flex flex-col gap-4">
                {/* Connection Mode */}
                <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-semibold uppercase tracking-widest text-muted">
                        Mode
                    </span>
                    {CONNECTION_MODES.map((mode) => (
                        <button
                            key={mode}
                            onClick={() => toggle(connectionMode, mode, setConnectionMode)}
                            className={`rounded-full border px-3 py-1 font-serif text-xs capitalize transition-colors ${
                                connectionMode === mode
                                    ? "border-terracotta bg-terracotta text-warm-white"
                                    : "border-border text-charcoal-soft hover:border-charcoal"
                            }`}
                        >
                            {mode}
                        </button>
                    ))}
                </div>

                {/* Temporal Type */}
                <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-semibold uppercase tracking-widest text-muted">
                        Temporal
                    </span>
                    {TEMPORAL_TYPES.map((type) => (
                        <button
                            key={type}
                            onClick={() => toggle(temporalType, type, setTemporalType)}
                            className={`rounded-full border px-3 py-1 font-serif text-xs capitalize transition-colors ${
                                    temporalType === type
                                        ? "border-terracotta bg-terracotta text-warm-white"
                                        : "border-border text-charcoal-soft hover:border-charcoal"
                            }`}
                        >
                            {type}
                        </button>
                    ))}
                </div>

                {/* Axis */}
                <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-semibold uppercase tracking-widest text-muted">
                        Axis
                    </span>
                    {AXES.map((axis) => (
                        <button
                            key={axis}
                            onClick={() => toggle(primaryAxis, axis, setPrimaryAxis)}
                            className={`rounded-full border px-3 py-1 font-serif text-xs capitalize transition-colors ${
                                primaryAxis === axis
                                    ? "border-terracotta bg-terracotta text-warm-white"
                                    : "border-border text-charcoal-soft hover:border-charcoal"
                            }`}
                        >
                            {axis}
                        </button>
                    ))}
                </div>

                {/* Social function dropdown */}
                <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold uppercase tracking-widest text-muted">
                        Function
                    </span>
                    <select
                        value={sharedFunction ?? ""}
                        onChange={(e) => setSharedFunction(e.target.value || null)}
                        className="rounded-lg border border-border bg-warm-white px-3 py-1.5 font-serif text-xs text-charcoal"
                    >
                        <option value="">All</option>
                        {functions.map((fn) => (
                            <option key={fn.function} value={fn.function}>
                                {fn.function} ({fn.count})
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Results */}
            <div className="mt-8 grid gap-6 md:grid-cols-2">
                {loading ? (
                    <p className="col-span-2 text-sm text-muted">
                        Loading...
                    </p>
                ) : bridges.length === 0 ? (
                    <p className="col-span-2 text-sm text-muted">
                        No bridges match these filters.
                    </p>
                ) : (
                    bridges.map((b) => (
                        <BridgeCardFull key={b.id} bridge={b} />
                    ))
                )}
            </div>
        </div>
    )
}