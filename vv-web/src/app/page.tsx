import Link from "next/link";
import { getTopBridges } from "@/lib/api";
import { BridgeCardFull } from "@/components/bridge";

export const revalidate = 3600; // Revalidate every hour

export default async function HomePage() {
    // Fetch one high-quality bridge for Bridge of the Day
    // Prefer lineage bridges with narratives
    const { bridges } = await getTopBridges({
        connection_mode: 'lineage',
        min_score: 0.6,
        limit: 10,
    }).catch(() => ({ bridges: [] }));

    // Pick one that has a narrative — use date as pseudo-random seed
    const today = new Date().toISOString().slice(0, 10);
    const seed = today.split('-').reduce((a, b) => a + parseInt(b), 0);
    const withNarrative = bridges.filter(b => b.bridge_narrative);
    const bridgeOfDay = withNarrative.length > 0
        ? withNarrative[seed % withNarrative.length]
        : bridges[0] ?? null;

    return (
        <div>
            {/* Hero */}
            <section className="flex min-h-[85vh] flex-col justify-end px-6 pb-16 md:px-12 md:pb-20">
                <div className="max-w-[720px]">
                    <h1 className="font-display text-[clamp(56px,10vw,120px)] font-bold uppercase leading-[0.9] tracking-tight text-black">
                        Vintage<br />Vestige
                    </h1>
                    <p className="mt-8 max-w-[480px] font-editorial text-[26px] italic leading-[1.4] text-dark">
                        Start from a question,<br />not a timeline.
                    </p>
                    <p className="mt-6 font-mono text-[11px] uppercase tracking-[0.1em] text-grey-400">
                        3,700+ garments · 21,000+ connections · 500 years
                    </p>
                    <Link
                        href="/search"
                        className="mt-10 inline-block bg-black px-8 py-3.5 font-mono text-[11px] uppercase tracking-[0.2em] text-white transition-colors hover:bg-dark"
                    >
                        Explore
                    </Link>
                </div>
            </section>

            {/* Bridge of the Day */}
            {bridgeOfDay && (
                <section className="bg-off-white px-6 py-20 md:px-12">
                    <div className="flex items-center gap-4 font-mono text-[11px] uppercase tracking-[0.15em] text-grey-400">
                        <span>Bridge of the Day</span>
                        <span className="h-px flex-1 bg-grey-200" />
                    </div>
                    <div className="mx-auto mt-8 max-w-[900px]">
                        <BridgeCardFull bridge={bridgeOfDay} />
                    </div>
                </section>
            )}

            {/* Entry Points */}
            <section className="px-6 py-20 md:px-12">
                <div className="flex items-center gap-4 font-mono text-[11px] uppercase tracking-[0.15em] text-grey-400">
                    <span>Explore</span>
                    <span className="h-px flex-1 bg-grey-200" />
                </div>
                <div className="mt-0 flex flex-col">
                    {[
                        {
                            title: "Browse by Era",
                            desc: "Where design ideas traveled · 1400s to present",
                            href: "/search?tab=era",
                        },
                        {
                            title: "Browse by Culture",
                            desc: "Independent inventions · cross-cultural lineage · shared technique",
                            href: "/search?tab=culture",
                        },
                        {
                            title: "Browse by Function",
                            desc: "Ceremonial · Mourning · Labor · Courtship · Military · Performance",
                            href: "/explore/functions",
                        },
                        {
                            title: "Explore Connections",
                            desc: "21,000+ garment connections · lineage · shared entity · visual echo",
                            href: "/bridges",
                        },
                    ].map((entry) => (
                        <Link
                            key={entry.title}
                            href={entry.href}
                            className="group flex items-baseline justify-between border-b border-grey-200 py-8 text-black no-underline transition-all"
                        >
                            <span className="font-display text-[clamp(28px,5vw,40px)] font-bold uppercase tracking-[0.02em] transition-[letter-spacing] duration-300 group-hover:tracking-[0.08em]">
                                {entry.title}
                                <span className="ml-4 text-[24px] text-grey-400 transition-all duration-200 group-hover:translate-x-2 group-hover:text-accent inline-block">
                                    →
                                </span>
                            </span>
                            <span className="hidden max-w-[300px] text-right font-mono text-[11px] uppercase leading-[1.6] tracking-[0.08em] text-grey-600 md:block">
                                {entry.desc}
                            </span>
                        </Link>
                    ))}
                </div>
            </section>
        </div>
    );
}
