import { notFound } from "next/navigation";
import Link from "next/link";
import { getProduct } from "@/lib/api";
import ThreadPull from "@/components/explore/ThreadPull";
import { decodePath } from "@/lib/threadPath";
import type { ProductSummary } from "@/types";
import type { Metadata } from "next";

interface Props {
    params: Promise<{ id: string }>;
    searchParams: Promise<{ path?: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
    const { id } = await params;
    try {
        const product = await getProduct(Number(id));
        return {
            title: `Thread Pull — ${product.display_title || product.title}`,
            description: `Follow the thread from ${product.display_title || product.title} wherever the graph leads.`,
        };
    } catch {
        return { title: "Thread Pull" };
    }
}

export default async function ThreadPage({ params, searchParams }: Props) {
    const { id } = await params;
    const { path } = await searchParams;
    const numId = Number(id);
    if (Number.isNaN(numId)) notFound();

    // Shared-link replay: a path of product ids, origin first. Only honored
    // when it actually starts from this route's origin garment.
    const decoded = decodePath(path);
    const initialPathIds =
        decoded.length > 1 && decoded[0] === numId ? decoded : undefined;

    let product;
    try {
        product = await getProduct(numId);
    } catch {
        notFound();
    }

    // Convert Product to ProductSummary for the component
    const startProduct: ProductSummary = {
        id: product.id,
        platform: product.platform,
        title: product.title,
        display_title: product.display_title,
        primary_image: product.primary_image,
        era: product.era,
        decade: product.decade,
        fp_category: product.fp_category,
        silhouette: product.silhouette,
        material: product.material,
        culture: product.culture,
        ai_description: product.ai_description,
        style_tags: product.style_tags ?? [],
        colors: product.colors ?? [],
        vibe_scores: product.vibe_scores ?? null,
        designer: product.designer,
        named_movements: product.named_movements ?? [],
        influence_references: product.influence_references ?? [],
        production_mode: product.production_mode,
    };

    return (
        <div className="bg-white px-6 py-12 md:px-12">
            <div className="mx-auto max-w-[800px]">
                {/* Header */}
                <Link
                    href={`/product/${numId}`}
                    className="font-mono text-[11px] uppercase tracking-[0.1em] text-grey-400 hover:text-black"
                >
                    ← Back to product
                </Link>

                <div className="mt-8">
                    <p className="font-mono text-[11px] uppercase tracking-[0.15em] text-accent">
                        Pull the Thread
                    </p>
                    <h1 className="mt-2 font-display text-[clamp(28px,5vw,44px)] font-bold text-black">
                        {product.display_title || product.title}
                    </h1>
                    <p className="mt-3 font-editorial text-xl italic text-dark">
                        Follow this garment wherever the graph leads.
                    </p>
                </div>

                {/* Thread */}
                <div className="mt-4">
                    <ThreadPull startProduct={startProduct} initialPathIds={initialPathIds} />
                </div>
            </div>
        </div>
    );
}
