import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "About",
    description: "Vintage Vestige connects 500 years of fashion history through entity-based connections between museum collections.",
};

export default function AboutPage() {
    return (
        <div className="bg-white px-6 py-20 md:px-12">
            <div className="mx-auto max-w-[640px]">
                <h1 className="font-display text-[clamp(36px,6vw,48px)] font-bold text-black">
                    Start from a question,<br />not a timeline.
                </h1>

                <div className="mt-10 space-y-6 text-[15px] leading-[1.8] text-dark">
                    <p>
                        Vintage Vestige connects garments across 500 years of fashion
                        history — not through similarity, but through shared DNA.
                        A shared designer, a shared construction technique, a named
                        movement that traveled across continents, an explicit influence
                        citation linking a 2020 dress to an 1890s sleeve.
                    </p>
                    <p>
                        The collection draws from The Metropolitan Museum of Art,
                        the Smithsonian, and the V&amp;A Museum. Each garment is
                        enriched by Claude AI, which extracts construction techniques,
                        social functions, named movements, designer attributions,
                        influence references, and material origins from images and
                        museum metadata.
                    </p>
                    <p>
                        Connections are discovered through entity-based matching —
                        an inverted index of shared attributes scored by rarity.
                        Sharing &ldquo;Japonisme&rdquo; is worth more than sharing
                        &ldquo;hand-sewing.&rdquo; Lineage bridges trace explicit
                        influence citations forward through time. Visual echoes catch
                        the surprises that metadata misses.
                    </p>
                    <p>
                        The result is a browsable graph of design history. Pull the
                        thread from any garment and follow where it leads — through
                        shared techniques, movements, and makers across centuries
                        and continents.
                    </p>
                </div>

                <div className="mt-16 grid gap-8 md:grid-cols-2">
                    <div>
                        <h2 className="font-mono text-[9px] uppercase tracking-[0.15em] text-grey-400">
                            Built With
                        </h2>
                        <ul className="mt-3 space-y-2 text-sm text-dark">
                            <li>Claude Sonnet 4 — enrichment &amp; narratives</li>
                            <li>all-mpnet-base-v2 — text embeddings</li>
                            <li>CLIP ViT-L/14 — image embeddings</li>
                            <li>pgvector — vector search</li>
                            <li>Next.js &amp; FastAPI</li>
                            <li>Supabase PostgreSQL</li>
                        </ul>
                    </div>
                    <div>
                        <h2 className="font-mono text-[9px] uppercase tracking-[0.15em] text-grey-400">
                            Data Sources
                        </h2>
                        <ul className="mt-3 space-y-2 text-sm text-dark">
                            <li>The Metropolitan Museum of Art</li>
                            <li>Smithsonian Institution</li>
                            <li>Victoria &amp; Albert Museum</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    );
}
