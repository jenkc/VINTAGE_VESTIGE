"use client";

import { Suspense, useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Search } from "lucide-react";
import { searchByText } from "@/lib/api";
import { DEFAULT_SEARCH_LIMIT } from "@/lib/constants";
import ProductCard from "@/components/search/ProductCard";
import { Input } from "@/components/ui";
import type { SearchResult } from "@/types";

function SearchContent() {
    const searchParams = useSearchParams();
    const router = useRouter();

    const [query, setQuery] = useState(searchParams.get("q") ?? "");
    const [results, setResults] = useState<SearchResult[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(false);
    const [hasSearched, setHasSearched] = useState(false);
    const [error, setError] = useState("");

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
        <div className="min-h-screen bg-cream-dark px-6 pt-12 pb-20 md:px-12">
            <div className="mx-auto max-w-[1200px]">
                {/* Search Bar */}
                <form
                    onSubmit={(e) => {
                        e.preventDefault();
                        handleSearch(query);
                    }}
                    className="relative mx-auto max-w-[480px]"
                    role="search"
                    aria-label="Search garments"
                >
                    <Input 
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Search by style, era, or description..."
                        className="h-9 rounded-full bg-warm-white pl-4 pr-10 text-[13px]"
                        autoFocus={!searchParams.get("q")}
                    />
                    <button
                        type="submit"
                        className="absolute right-1 top-1/2 -translate-y-1/2 flex size-11 items-center justify-center text-muted"
                        aria-label="Submit search"   
                    >
                        <Search className="size-4" />
                    </button>
                </form>

                {/* Results header */}
                {hasSearched && (
                    <div className="mt-10">
                        <h1 className="font-serif text-[28px] font-bold text-charcoal">
                            Search Results for &ldquo;{searchParams.get("q")}&rdquo;
                        </h1>
                        <p className="mt-1 text-sm text-muted">
                            {total} {total === 1 ? "result" : "results"}
                        </p>
                    </div>
                )}

                {/* Loading state */}
                {loading && (
                    <p className="mt-16 text-center text-sm text-muted">
                        Searching...
                    </p>
                )}

                {/* Error state */}
                {error && (
                    <p className="mt-16 text-center text-sm text-terracotta">
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
                    <p className="mt-16 text-center font-serif text-lg text-muted">
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