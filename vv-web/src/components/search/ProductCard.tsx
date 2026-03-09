import Link from "next/link";
import ImageWithFallback from "@/components/ui/ImageWithFallback";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import { PLATFORM_COLORS, PLATFORM_NAMES } from "@/styles/theme";
import type { SearchResult, ProductSummary, Product } from "@/types";

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
        PLATFORM_COLORS[platform as keyof typeof PLATFORM_COLORS] ?? "#8A7E74";

    return (
        <Link
            href={`/product/${product.id}`}
            className={cn(
                "group block overflow-hidden rounded-lg border border-border bg-warm-white shadow-card",
                "transition-all duration-300",
                "hover:-translate-y-1 hover:shadow-card-hover",
                className
            )}
        >
            {/* Image container - 3:4 ratio */}
            <div className="relative aspect-[3/4] overflow-hidden bg-cream">
                {product.primary_image ? (
                    <ImageWithFallback
                        src={product.primary_image ?? ""}
                        alt={product.title}
                        fill
                        sizes="(max-width: 768px) 50vw, 25vw"
                        className="object-cover transition-transform duration-300 group-hover:scale-105"
                    />
                ) : (
                    <div className="flex h-full items-center justify-center bg-gradient-to-br from-cream to-border">
                        <span className="font-serif text-lg text-muted">No image</span>
                    </div>
                )}
            
                {/* Platform badge - top left */}
                <span
                    className="absolute top-2 left-2 rounded-full bg-warm-white/90 backdrop-blur-sm px-2.5 py-0.5 text-[10px] font-semibold font-serif"
                    style={{ color: platformColor }}
                >
                    {platformName}
                </span>
            </div>

            {/* Card body */}
            <div className="p-3">
                <h3 className="font-serif text-sm font-bold leading-tight text-charcoal line-clamp-2">
                    {product.title}
                </h3>

                <div className="mt-2 flex items-center justify-between gap-2">
                    {product.era && (
                        <Badge variant="era" className="text-[11px]">
                            {product.era}
                        </Badge>
                    )}

                    {matchScore !== undefined && (
                        <span className="ml-auto text-xs font-semibold text-terracotta">
                            {Math.round(matchScore *100)}%
                        </span>
                    )}
                </div>
            </div>
        </Link>
    );
}