import Link from "next/link";
import ImageWithFallback from "@/components/ui/ImageWithFallback";
import { cn } from "@/lib/utils";
import { PLATFORM_COLORS, PLATFORM_NAMES } from "@/styles/theme";
import type { SearchResult, ProductSummary } from "@/types";

type CardData = SearchResult | ProductSummary;

interface ProductCardProps {
    product: CardData;
    score?: number;
    className?: string;
}

function hasScore(p: CardData): p is SearchResult {
    return "score" in p;
}

export default function ProductCard({
    product,
    score,
    className,
}: ProductCardProps) {
    const matchScore = score ?? (hasScore(product) ? product.score : undefined);
    const platform = product.platform;
    const platformName =
        PLATFORM_NAMES[platform as keyof typeof PLATFORM_NAMES] ?? platform;
    const platformColor =
        PLATFORM_COLORS[platform as keyof typeof PLATFORM_COLORS] ?? "#6B6B6B";

    return (
        <Link
            href={`/product/${product.id}`}
            className={cn(
                "group block overflow-hidden",
                "transition-all duration-300",
                className
            )}
        >
            {/* Image container - 3:4 ratio */}
            <div className="relative aspect-[3/4] overflow-hidden bg-off-white">
                {product.primary_image ? (
                    <ImageWithFallback
                        src={product.primary_image ?? ""}
                        alt={product.title}
                        fill
                        sizes="(max-width: 768px) 50vw, 25vw"
                        className="object-cover transition-transform duration-300 group-hover:scale-[1.02]"
                    />
                ) : (
                    <div className="flex h-full items-center justify-center bg-gradient-to-br from-grey-100 to-grey-200">
                        <span className="font-mono text-sm text-grey-400">No image</span>
                    </div>
                )}

                {/* Platform label - top left */}
                <span
                    className="absolute top-2 left-2 font-mono text-[10px] uppercase tracking-wider"
                    style={{ color: platformColor }}
                >
                    {platformName}
                </span>
            </div>

            {/* Card body */}
            <div className="py-3">
                <h3 className="font-display text-sm font-bold leading-tight text-black line-clamp-2">
                    {'display_title' in product && product.display_title ? product.display_title : product.title}
                </h3>

                <div className="mt-1.5 flex items-center justify-between gap-2">
                    {product.era && (
                        <span className="font-mono text-[10px] text-grey-600">
                            {product.era}
                        </span>
                    )}

                    {matchScore !== undefined && (
                        <span className="ml-auto font-mono text-xs text-grey-600">
                            {Math.round(matchScore * 100)}%
                        </span>
                    )}
                </div>

                {'named_movements' in product && Array.isArray(product.named_movements) && product.named_movements.length > 0 && (
                    <div className="mt-1.5 flex flex-wrap gap-1">
                        {product.named_movements.slice(0, 2).map((m: string) => (
                            <span
                                key={m}
                                className="font-mono text-[9px] uppercase tracking-[0.06em] text-accent"
                            >
                                {m}
                            </span>
                        ))}
                    </div>
                )}
            </div>
        </Link>
    );
}
