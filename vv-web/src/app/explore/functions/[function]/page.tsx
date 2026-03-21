import Link from "next/link";
import { getExploreFunction, getTopBridges } from "@/lib/api";
import ProductCard from "@/components/search/ProductCard";
import { BridgeCardCompact } from "@/components/bridge";

interface Props {
    params: Promise<{ function: string }>;
}

export default async function FunctionDetailPage({ params }: Props) {
    const { function: fn } = await params;
    const decoded = decodeURIComponent(fn);

    const [data, bridges] = await Promise.all([
        getExploreFunction(decoded, { limit: 50 }),
        getTopBridges({ limit: 6 }),
    ]);

    return (
        <div className="mx-auto max-w-[1200px] px-6 py-12 md:px-12">
            <Link
                href="/explore/functions"
                className="font-mono text-[11px] uppercase tracking-[0.1em] text-grey-400 hover:text-black"
            >
                ← All Functions
            </Link>

            <h1 className="mt-6 font-display text-[clamp(32px,5vw,48px)] font-bold capitalize text-black">
                {decoded}
            </h1>

            <p className="mt-2 font-mono text-[11px] uppercase tracking-[0.1em] text-grey-400">
                {data.total} garments across eras and cultures
            </p>

            {/* Product carousel */}
            <section className="mt-10">
                <div className="flex items-center gap-4 font-mono text-[11px] uppercase tracking-[0.15em] text-grey-400">
                    <span>Garments</span>
                    <span className="h-px flex-1 bg-grey-200" />
                </div>
                <div className="mt-6 flex gap-5 overflow-x-auto pb-4 snap-x">
                    {data.products.map((p) => (
                        <div key={p.id} className="w-[180px] md:w-[200px] flex-shrink-0 snap-start">
                            <ProductCard product={p} />
                        </div>
                    ))}
                </div>
            </section>

            {/* Connections */}
            {bridges.bridges.length > 0 && (
                <section className="mt-12">
                    <div className="flex items-center gap-4 font-mono text-[11px] uppercase tracking-[0.15em] text-grey-400">
                        <span>Connections</span>
                        <span className="h-px flex-1 bg-grey-200" />
                    </div>
                    <div className="mt-6 flex gap-5 overflow-x-auto pb-4 snap-x">
                        {bridges.bridges.map((b) => (
                            <BridgeCardCompact key={b.id} bridge={b} />
                        ))}
                    </div>
                </section>
            )}
        </div>
    );
}
