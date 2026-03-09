import Link from "next/link";
import { Sparkles, Search, ArrowLeftRight } from "lucide-react";
import { getTopBridges } from "@/lib/api";
import { FEATURED_BRIDGES_LIMIT } from "@/lib/constants";
import { BridgeCardCompact } from "@/components/bridge";
import { buttonVariants } from "@/components/ui/Button";

export const revalidate = 3600; // Revalidate every hour
export default async function HomePage() {
    const { bridges } = await getTopBridges({ limit: FEATURED_BRIDGES_LIMIT });

    return (
        <div>
            {/* Hero Section */}
            <section className="bg-cream-dark px-6 pt-24 pb-16 md:pt-28 md:pb-20">
                <div className="mx-auto max-w-[680px] text-center">
                    <p className="font-serif text-[10px] font-semibold uppercase tracking-[6px] text-gold">
                        Vintage Vestige
                    </p>

                    <h1 className="mt-6 font-serif text-4xl font-bold leading-[1.1] tracking-tight text-charcoal md:text-[56px] md:leading-[61.6px]">
                        A fashion knowledge graph connecting 500&nbsp;years of design history
                    </h1>

                    <p className="mt-6 text-lg leading-[1.6] text-charcoal-soft">
                        Discover how historical garments inspire contemporary fashion through AI-computed style bridges. Explore connections across centuries of design.
                    </p>

                    <div className="mt-10 flex items-center justify-center gap-4">
                        <Link
                            href="/search"
                            className={buttonVariants({ size: "lg" })}
                        >
                            Start Searching
                        </Link>
                        <Link
                            href="/search?mode=image"
                            className={buttonVariants({ variant: "outline", size: "lg" })}
                        >
                            Upload Image
                        </Link>
                    </div>
                </div>
            </section>

            {/* How It Works */}
            <section className="px-6 py-20 md:px-12">
                <p className="text-center font-serif text-[10px] font-semibold uppercase tracking-[3px] text-charcoal-soft">
                    The Pipeline
                </p>
                <h2 className="mt-2 text-center font-serif text-3xl font-bold text-charcoal md:text-4xl">
                    How It Works
                </h2>
                <div className="mx-auto mt-12 grid max-w-[960px] gap-8 md:grid-cols-3">
                    {[
                        {
                            icon: Sparkles,
                            title: "AI Style Analysis",
                            description: "Every garment is analyzed by Claude AI to extract era, style attributes, materials, and aesthetic vibes from museum metadata.",
                        },
                        {
                            icon: Search,
                            title: "Multi-Modal Search",
                            description: "Search by text description or upload an image. Our dual-embedding system finds matches across semantic meaning and visual similarity.",
                        },
                        {
                            icon: ArrowLeftRight,
                            title: "Style Bridges",
                            description: "Discover design connections across centuries. Each bridge reveals shared DNA between historical and contemporary garments.",
                        }
                    ].map((step) => (
                        <div
                            key={step.title}
                            className="flex flex-col items-center rounded-2xl border border-border bg-warm-white px-6 py-8 text-center"
                        >
                            <div className="flex size-14 items-center justify-center rounded-full bg-gold/8">
                                <step.icon className="size-6 text-gold" />
                            </div>
                            <h3 className="mt-5 font-serif text-xl font-bold text-charcoal">
                                {step.title}
                            </h3>
                            <p className="mt-2 text-sm leading-[1.6] text-charcoal-soft">
                                {step.description}
                            </p>
                        </div>
                    ))}
                </div>
            </section>

            {/* Featured Bridges */}
            <section className="border-t border-border bg-warm-white px-6 py-20 md:px-12">
                <p className="font-serif text-[10px] font-semibold uppercase tracking-[3px] text-charcoal-soft">
                    Discover
                </p>
                <h2 className="mt-2 text-center font-serif text-3xl font-bold text-charcoal md:text-4xl">
                    Featured Bridges
                </h2>
                <div 
                    className="mt-12 flex snap-x snap-mandatory gap-5 overflow-x-auto pb-4"
                    role="region"
                    aria-label="Featured style bridges"
                >
                    {bridges.map((bridge) => (
                        <BridgeCardCompact key={bridge.id} bridge={bridge} />
                    ))}
                </div>
            </section>

        </div>
    );
}
