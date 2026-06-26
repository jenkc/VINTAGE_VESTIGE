import { notFound } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { getProduct, getStyleAncestry, getProductBridges } from "@/lib/api";
import { PLATFORM_NAMES, PLATFORM_COLORS } from "@/styles/theme";
import { BridgeCardFull, BridgeCardCompact } from "@/components/bridge";
import type { Metadata } from "next";

export async function generateMetadata({ params }: Props): Promise<Metadata> {
    const { id } = await params;
    try {
        const product = await getProduct(Number(id));
        const title = product.display_title || product.title;
        return {
            title,
            description: product.ai_description ?? `${title} — explore connections and design history.`,
            openGraph: {
                title,
                description: product.ai_description ?? undefined,
                images: product.primary_image ? [product.primary_image] : [],
            }
        };
    } catch {
        return { title: "Product not found" };
    }
}

interface Props {
    params: Promise<{ id: string }>;
}

export default async function ProductDetailPage({ params }: Props) {
    const { id } = await params;
    const numId = Number(id);
    if (Number.isNaN(numId)) notFound();

    let product;
    try {
        product = await getProduct(numId);
    } catch {
        notFound();
    }

    const [connectedData, echoesData] = await Promise.all([
        getProductBridges(numId, { limit: 4 }),
        getStyleAncestry(numId, { limit: 6 }),
    ]);

    const platformName = PLATFORM_NAMES[product.platform as keyof typeof PLATFORM_NAMES] ?? product.platform;
    const platformColor = PLATFORM_COLORS[product.platform as keyof typeof PLATFORM_COLORS] ?? "#6B6B6B";

    const displayTitle = product.display_title || product.title;

    // Parse named_movements and influence_references for display
    const movements = product.named_movements ?? [];
    const influences = product.influence_references ?? [];

    return (
        <div className="bg-white">
            {/* Hero */}
            <section className="mx-auto grid max-w-[1200px] gap-12 px-6 pt-12 pb-16 md:grid-cols-2 md:px-12">
                {/* Image — capped height so a portrait frame doesn't dominate the hero */}
                <div className="relative aspect-[3/4] max-h-[600px] w-full overflow-hidden bg-off-white md:self-start">
                    {product.primary_image && (
                        <Image
                            src={product.primary_image}
                            alt={displayTitle}
                            fill
                            priority
                            sizes="(max-width: 768px) 100vw, 50vw"
                            className="object-contain"
                        />
                    )}
                </div>

                {/* Info */}
                <div className="flex flex-col justify-center">
                    <span
                        className="w-fit font-mono text-[10px] font-semibold uppercase tracking-wider"
                        style={{ color: platformColor }}
                    >
                        {platformName}
                    </span>

                    <h1 className="mt-4 font-display text-3xl font-bold leading-tight text-black md:text-[44px] md:leading-[1.05]">
                        {displayTitle}
                    </h1>

                    <p className="mt-2 font-mono text-[11px] text-grey-600">
                        {[product.era, product.decade, product.culture].filter(Boolean).join(" · ")}
                    </p>

                    {/* KG metadata grid */}
                    <div className="mt-6 grid grid-cols-2 gap-x-6 gap-y-3">
                        {[
                            { label: "Designer", value: product.designer },
                            { label: "Production", value: product.production_mode },
                            { label: "Material", value: product.material },
                            { label: "Culture", value: product.culture },
                        ].filter((m) => m.value)
                        .map((m) => (
                            <div key={m.label}>
                                <p className="font-mono text-[9px] uppercase tracking-[0.12em] text-grey-400">
                                    {m.label}
                                </p>
                                <p className="mt-0.5 text-[13px] text-dark">
                                    {m.value}
                                </p>
                            </div>
                        ))}
                        {movements.length > 0 && (
                            <div>
                                <p className="font-mono text-[9px] uppercase tracking-[0.12em] text-grey-400">
                                    Movement
                                </p>
                                <p className="mt-0.5 text-[13px] text-dark">
                                    {movements.join(" · ")}
                                </p>
                            </div>
                        )}
                        {influences.length > 0 && (
                            <div>
                                <p className="font-mono text-[9px] uppercase tracking-[0.12em] text-grey-400">
                                    Influences
                                </p>
                                <p className="mt-0.5 text-[13px] text-dark">
                                    {influences.join(" · ")}
                                </p>
                            </div>
                        )}
                    </div>

                    {product.ai_description && (
                        <p className="mt-6 text-[15px] leading-[1.7] text-dark">
                            {product.ai_description}
                        </p>
                    )}

                    {/* Pull the Thread CTA — the signature interaction, surfaced in the hero */}
                    <div className="mt-8">
                        <Link
                            href={`/thread/${numId}`}
                            className="group inline-flex items-center gap-3 border border-black px-6 py-3 font-mono text-[12px] uppercase tracking-[0.12em] text-black no-underline transition-colors hover:bg-black hover:text-white"
                        >
                            Pull the Thread
                            <span className="transition-transform duration-200 group-hover:translate-x-1.5">→</span>
                        </Link>
                        <p className="mt-2 font-mono text-[10px] tracking-[0.06em] text-grey-400">
                            Follow this garment wherever the graph leads
                        </p>
                    </div>

                    {/* Attribute tags */}
                    {product.fp_category && (
                        <div className="mt-6 flex flex-wrap gap-2">
                            {[product.fp_category, product.silhouette, product.neckline, product.length]
                                .filter(Boolean)
                                .map((tag) => (
                                    <span
                                        key={tag}
                                        className="border border-grey-200 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.06em] text-grey-600"
                                        style={{ borderRadius: '999px' }}
                                    >
                                        {tag}
                                    </span>
                                ))}
                        </div>
                    )}
                </div>
            </section>

            {/* Connected To */}
            {connectedData.bridges.length > 0 && (
                <section className="mx-auto max-w-[1200px] px-6 pt-12 pb-16 md:px-12">
                    <div className="flex items-center gap-4 font-mono text-[11px] uppercase tracking-[0.15em] text-grey-400">
                        <span>Connected To</span>
                        <span className="h-px flex-1 bg-grey-200" />
                    </div>

                    <div className="mt-8 grid gap-6 md:grid-cols-2">
                        {connectedData.bridges.map((bridge) => (
                            <BridgeCardFull key={bridge.id} bridge={bridge} />
                        ))}
                    </div>
                </section>
            )}

            {/* Echoes Across Time */}
            {echoesData.bridges.length > 0 && (
                <section className="border-t border-grey-200 px-6 pt-12 pb-16 md:px-12">
                    <div className="mx-auto max-w-[1200px]">
                        <div className="flex items-center gap-4 font-mono text-[11px] uppercase tracking-[0.15em] text-grey-400">
                            <span>Echoes Across Time</span>
                            <span className="h-px flex-1 bg-grey-200" />
                        </div>

                        <div
                            className="mt-8 flex snap-x snap-mandatory gap-5 overflow-x-auto pb-4"
                            role="region"
                            aria-label="Cross-time connections"
                        >
                            {echoesData.bridges.map((bridge) => (
                                <BridgeCardCompact key={bridge.id} bridge={bridge} />
                            ))}
                        </div>
                    </div>
                </section>
            )}

        </div>
    );
}
