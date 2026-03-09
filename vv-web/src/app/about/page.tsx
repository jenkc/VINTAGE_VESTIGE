import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "About",
    description: "Vintage Vestige connects 500 years of fashion history through AI-computed style bridges between museum collections and contemporary design.",
};

export default function AboutPage() {
    return (
        <div className="bg-cream-dark px-6 py-20 md:px-12">
            <div className="mx-auto max-w-[680px]">
                <p className="font-serif text-[10px] font-semibold uppercase tracking-[6px] text-gold">
                    About
                </p>
                <h1 className="mt-4 font-serif text-4xl font-bold text-charcoal md:text-5xl">
                    Vintage Vestige
                </h1>

                <div className="mt-10 space-y-6 leading-[1.8] text-charcoal-soft">
                    <p>
                        Vintage Vestige is a fashion knowledge graph that connects
                        500&nbsp;years of design history through AI-computed style
                        bridges. It reveals how historical garments from museum
                        collections inspire — and are echoed by — contemporary fashion.
                    </p>
                    <p>
                        The system ingests garments from The Metropolitan Museum of Art,
                        the Smithsonian, and Fashionpedia. Each item is enriched by
                        Claude&nbsp;AI, which extracts era, silhouette, material, vibe,
                        and dozens of other style attributes from raw museum metadata.
                    </p>
                    <p>
                        Dual embeddings — semantic (all-MiniLM-L6-v2) and visual
                        (CLIP ViT-B/32) — power a multi-modal search that finds
                        matches across both meaning and appearance. Style bridges are
                        then computed in three passes: cross-temporal, cross-category,
                        and cross-vibe, scoring each connection on text similarity,
                        image similarity, and structural overlap.
                    </p>
                    <p>
                        The result is a browsable web of design DNA that lets you trace
                        a Victorian bustle through Art Deco streamlining to a modern
                        runway silhouette — or upload a photo of a thrift-store find and
                        discover its historical ancestors.
                    </p>
                </div>

                <div className="mt-16 grid gap-8 md:grid-cols-2">
                    <div>
                        <h2 className="font-serif text-[9px] font-semibold uppercase tracking-[2px] text-muted">
                            Built With
                        </h2>
                        <ul className="mt-3 space-y-2 text-sm text-charcoal-soft">
                            <li>Claude API — enrichment &amp; narratives</li>
                            <li>CLIP — image embeddings</li>
                            <li>Qdrant — vector search</li>
                            <li>Next.js &amp; FastAPI</li>
                            <li>PostgreSQL</li>
                        </ul>
                    </div>
                    <div>
                        <h2 className="font-serif text-[9px] font-semibold uppercase tracking-[2px] text-muted">
                            Data Sources
                        </h2>
                        <ul className="mt-3 space-y-2 text-sm text-charcoal-soft">
                            <li>The Metropolitan Museum of Art</li>
                            <li>Smithsonian</li>
                            <li>Fashionpedia</li>
                        </ul>
                    </div>
                </div>

            </div>
        </div>
    )
}