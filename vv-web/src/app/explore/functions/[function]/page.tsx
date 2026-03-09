import Link from "next/link";
import { getExploreFunction, getTopBridges } from "@/lib/api";
import ProductCard from "@/components/search/ProductCard";
import { BridgeCardCompact, BridgeCardFull } from "@/components/bridge";

interface Props {
    params: Promise<{ function: string }>;
}

export default async function FunctionDetailPage({ params }: Props) {
    const { function: fn } = await params;
    const decoded = decodeURIComponent(fn);

    const [data, bridges, contrasts] = await Promise.all([
        getExploreFunction(decoded, { limit: 50 }),
        getTopBridges({ shared_function: decoded, limit: 6 }),
        getTopBridges({ shared_function: decoded, connection_mode: "contrast", limit: 6 }),
    ]);

    return (
        <div className="mx-auto max-w-6xl px-4 py-10">
            <Link
                href="/explore/functions"
                className="text-sm text-charcoal-soft hover:text-terracotta"
            >
                &larr; All Functions
            </Link>

            <h1 className="mt-4 font-serif text-3xl font-bold capitalize text-charcoal">
                {decoded}
            </h1>

            <p className="mt-1 text-sm text-muted">
                {data.total === 1 ? "Only one garment found" : `${data.total} garments across eras and cultures`} 
            </p>

            {/* Related bridges */}
            {bridges.bridges.length > 0 && (
                <section className="mt-8">
                    <h2 className="font-serif text-lg font-bold text-charcoal">
                        Connections
                    </h2>
                    <div className="mt-3 flex gap-4 overflow-x-auto pb-2 snap-x">
                        {bridges.bridges.map((b) => (
                            <BridgeCardCompact key={b.id} bridge={b} />
                        ))}
                    </div>
                </section>
            )}
            
            {/* Contrasts: same question, different answers */}
            {contrasts.bridges.length > 0 && (
                <section className="mt-10">
                    <h2 className="font-serif text-lg font-bold text-charcoal">
                        Same Question, Different Answers
                    </h2>
                    <p className="mt-1 text-sm text-muted">
                        Garments that serve the same purpose through opposing aesthetics.
                    </p>
                    <div className="mt-4 grid gap-6 md:grid-cols-2">
                        {contrasts.bridges.map((b) => (
                            <BridgeCardFull key={b.id} bridge={b} />
                        ))}
                    </div>
                </section>
            )}

            {/* Product grid */}
            <section className="mt-10">
                <h2 className="font-serif text-lg font-bold text-charcoal">
                    Garments
                </h2>
                <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
                    {data.products.map((p) => (
                        <ProductCard key={p.id} product={p} />
                    ))}
                </div>
            </section>
        </div>
    )
}