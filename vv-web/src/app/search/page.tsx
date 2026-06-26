"use client";

import { Suspense, useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { searchByText } from "@/lib/api";
import { DEFAULT_SEARCH_LIMIT } from "@/lib/constants";
import ProductCard from "@/components/search/ProductCard";
import type { SearchResult } from "@/types";

function SearchContent() {
    const searchParams = useSearchParams();
    const router = useRouter();

    const [query, setQuery] = useState(searchParams.get("q") ?? "");
    const [results, setResults] = useState<SearchResult[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(false);
    const [slow, setSlow] = useState(false);
    const [hasSearched, setHasSearched] = useState(false);
    const [error, setError] = useState("");

    // After a few seconds of loading, reassure the user (first search wakes the
    // search engine — the embedding model cold-loads on an idle server ~once).
    useEffect(() => {
        if (!loading) {
            setSlow(false);
            return;
        }
        const t = setTimeout(() => setSlow(true), 4000);
        return () => clearTimeout(t);
    }, [loading]);

    async function handleSearch(q: string) {
        const trimmed = q.trim();
        if (!trimmed) return;

        setLoading(true);
        setError("");
        try {
            const data = await searchByText(trimmed, undefined, DEFAULT_SEARCH_LIMIT);
            setResults(data.results);
            setTotal(data.total);
            setHasSearched(true);
            router.replace(`/search?q=${encodeURIComponent(trimmed)}`, { scroll: false });
        } catch {
            setError("Something went wrong. Please try again.");
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        const initial = searchParams.get("q");
        if (initial) handleSearch(initial);
    }, []);  // eslint-disable-line react-hooks/exhaustive-deps

    return (
        <div className="min-h-screen bg-white px-6 pt-12 pb-20 md:px-12">
            <div className="mx-auto max-w-[1200px]">

                {/* Search Bar */}
                <form
                    onSubmit={(e) => {
                        e.preventDefault();
                        handleSearch(query);
                    }}
                    className="mx-auto max-w-[600px]"
                    role="search"
                    aria-label="Search garments"
                >
                    <div className="flex items-center border-b-2 border-black pb-3">
                        <input
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="Search garments, eras, movements, or paste a question..."
                            className="flex-1 bg-transparent text-[18px] text-black outline-none placeholder:text-grey-400"
                            autoFocus={!searchParams.get("q")}
                        />
                        <button
                            type="submit"
                            className="font-mono text-[11px] uppercase tracking-[0.12em] text-grey-600 hover:text-black"
                        >
                            Search →
                        </button>
                    </div>
                </form>

                {/* Results header */}
                {hasSearched && (
                    <div className="mt-10">
                        <div className="flex items-center gap-4 font-mono text-[11px] uppercase tracking-[0.15em] text-grey-400">
                            <span>{total} {total === 1 ? "result" : "results"} for &ldquo;{searchParams.get("q")}&rdquo;</span>
                            <span className="h-px flex-1 bg-grey-200" />
                        </div>
                    </div>
                )}

                {/* Loading */}
                {loading && (
                    <div className="mt-16 text-center">
                        <p className="font-mono text-[11px] uppercase tracking-wider text-grey-400 animate-pulse">
                            Searching...
                        </p>
                        {slow && (
                            <p className="mt-3 font-editorial text-base italic text-grey-400">
                                Waking the search engine — the first query after a quiet spell
                                takes a few seconds. Hang tight.
                            </p>
                        )}
                    </div>
                )}

                {/* Error */}
                {error && (
                    <p className="mt-16 text-center font-mono text-[11px] text-accent">
                        {error}
                    </p>
                )}

                {/* Results grid */}
                {!loading && results.length > 0 && (
                    <div className="mt-8 grid grid-cols-2 gap-5 md:grid-cols-4">
                        {results.map((result) => (
                            <ProductCard key={result.id} product={result} />
                        ))}
                    </div>
                )}

                {/* Empty state */}
                {!loading && hasSearched && results.length === 0 && (
                    <p className="mt-16 text-center font-editorial text-lg italic text-grey-400">
                        No results found. Try a different search term.
                    </p>
                )}

            </div>
        </div>
    );
}

export default function SearchPage() {
    return (
        <Suspense>
            <SearchContent />
        </Suspense>
    );
}
