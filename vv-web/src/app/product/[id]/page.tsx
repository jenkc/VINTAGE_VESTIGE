import { notFound } from "next/navigation";
import Image from "next/image";
import { getProduct, getStyleAncestry, getStyleSiblings } from "@/lib/api";
import { PLATFORM_NAMES, PLATFORM_COLORS } from "@/styles/theme";
import { BridgeCardFull, BridgeCardCompact } from "@/components/bridge";
import type { Metadata } from "next";

export async function generateMetadata({ params }: Props): Promise<Metadata> {
    const { id } = await params;
    try {
        const product = await getProduct(Number(id));
        return {
            title: product.title,
            description: product.ai_description ?? `${product.title} - explore style bridges and design connections.`,
            openGraph: {
                title: product.title,
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

    const [ancestryData, siblingsData] = await Promise.all([
        getStyleAncestry(numId, { limit: 4 }),
        getStyleSiblings(numId, { limit: 6 }),
    ]);

    const platformName = PLATFORM_NAMES[product.platform as keyof typeof PLATFORM_NAMES] ?? product.platform;

    const platformColor = PLATFORM_COLORS[product.platform as keyof typeof PLATFORM_COLORS] ?? "#8A7E74";

    const tags = [product.era, product.garment_type, product.vibe, product.material]
        .filter(Boolean) as string[];

    return (
        <div className="bg-cream-dark">
            {/* Hero */}
            <section className="mx-auto grid max-w-[1200px] gap-12 px-6 pt-12 pb-16 md:grid-cols-2 md:px-12">
                {/* Image */}
                <div className="relative aspect-[3/4] overflow-hidden rounded-2xl bg-gradient-to-br from-border to-border-light">
                    {product.primary_image && (
                        <Image
                            src={product.primary_image}
                            alt={product.title}
                            fill
                            priority
                            sizes="(max-width: 768px) 100vw, 50vw"
                            className="object-cover"
                        />
                    )}
                </div>

                {/* Info */}
                <div className="flex flex-col justify-center">
                    <span
                        className="w-fit rounded-full bg-warm-white/90 px-2.5 py-1 font-serif text-[10px] font-semibold uppercase tracking-[0.3px]"
                        style={{ color: platformColor }}
                    >
                        {platformName}
                    </span>

                    <h1 className="mt-4 font-serif text-3xl font-bold leading-tight text-charcoal md:text-4xl">
                        {product.title}
                    </h1>

                    {tags.length > 0 && (
                        <div className="mt-4 flex flex-wrap gap-2">
                            {tags.map((tag) => (
                                <span
                                    key={tag}
                                    className="rounded-full bg-gold/8 px-3 py-1 font-serif text-xs text-gold"
                                >
                                    {tag}
                                </span>
                            ))}
                        </div>
                    )}

                    {product.ai_description && (
                        <p className="mt-6 leading-[1.6] text-charcoal-soft">
                            {product.ai_description}
                        </p>
                    )}

                    {/* Metadata grid */}
                    <div className="mt-8 grid grid-cols-2 gap-4">
                        {[
                            { label: "Era", value: product.era },
                            { label: "Date", value: product.object_date },
                            { label: "Material", value: product.material },
                            { label: "Culture", value: product.culture },
                        ].filter((m) => m.value)
                        .map((m) => (
                            <div key={m.label}>
                                <p className="font-serif text-[9px] font-semibold uppercase tracking-[2px] text-muted">
                                    {m.label}
                                </p>
                                <p className="mt-1 font-serif text-base font-bold text-charcoal">
                                    {m.value}
                                </p>
                            </div>    
                        ))}
                    </div>
                </div>
            </section>

            {/* Style Ancestry */}
            {ancestryData.bridges.length > 0 && (
                <section className="mx-auto max-w-[1200px] px-6 pt-12 pb-16 md:px-12">
                    <p className="font-serif text-[10px] font-semibold uppercase tracking-[3px] text-muted">
                        Style Ancestry
                    </p>
                    <h2 className="mt-2 font-serif text-[28px] font-bold text-charcoal">
                        Historical Influences
                    </h2>
                    <p className="mt-1 text-sm text-muted">
                        Garments that share design DNA across centuries
                    </p>

                    <div className="mt-8 grid gap-6 md:grid-cols-2">
                        {ancestryData.bridges.map((bridge) => (
                            <BridgeCardFull key={bridge.id} bridge={bridge} />
                        ))}
                    </div>
                </section>
            )}

            {/* Style Siblings */}
            {siblingsData.bridges.length > 0 && (
                <section className="border-t border-border px-6 pt-12 pb-16 md:px-12">
                    <div className="mx-auto max-w-[1200px]">
                        <p className="font-serif text-[10px] font-semibold uppercase tracking-[3px] text-muted">
                            Style Siblings
                        </p>
                        <h2 className="mt-2 font-serif text-[28px] font-bold text-charcoal">
                            Related Garments
                        </h2>
                        <p className="mt-1 text-sm text-muted">
                            Similar design DNA across the collection
                        </p>

                        <div 
                            className="mt-8 flex snap-x snap-mandatory gap-5 overflow-x-auto pb-4"
                            role="region"
                            aria-label="Related garments"
                        >
                            {siblingsData.bridges.map((bridge) => (
                                <BridgeCardCompact key={bridge.id} bridge={bridge} />
                            ))}
                        </div>
                    </div>
                </section>
            )}

        </div>
    )
}



