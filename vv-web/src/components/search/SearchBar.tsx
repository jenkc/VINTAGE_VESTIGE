"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { Search, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface SearchBarProps {
    onSearch: (query: string) => void;
    defaultValue?: string;
    variant?: "large" | "compact";
    placeholder?: string;
    className?: string;
}

export default function SearchBar({
    onSearch,
    defaultValue = "",
    variant = "large",
    placeholder = "Search...",
    className,
}: SearchBarProps) {
    const [value, setValue] = useState(defaultValue);
    const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    // Debounced search - fires 400ms after the user stops typing
    const debouncedSearch = useCallback(
        (query: string) => {
            if (debounceRef.current) clearTimeout(debounceRef.current);
            debounceRef.current = setTimeout(() =>
                onSearch(query), 400);
        },
        [onSearch]
    );

    // Clean up timer on unmount
    useEffect(() => {
        return () => {
            if (debounceRef.current) clearTimeout(debounceRef.current);
        };
    }, []);

    function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
        const next = e.target.value;
        setValue(next);
        debouncedSearch(next);
    }

    function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
        if (e.key === "Enter") {
            if (debounceRef.current) clearTimeout(debounceRef.current);
            onSearch(value);
        }
    }

    function handleClear() {
        setValue("");
        onSearch("");
    }

    const isLarge = variant === "large";

    return (
        <div
            className={cn(
                "relative w-full",
                isLarge ? "max-w-[640px]" : "max-w-[480px]",
                className
            )}
        >
            <input
                type="text"
                value={value}
                onChange={handleChange}
                onKeyDown={handleKeyDown}
                placeholder={placeholder}
                className={cn(
                    "w-full rounded-md border border-border bg-warm-white pr-10 text-charcoal",
                    "placeholder:text-muted",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-terracotta focus-visible:ring-offset-2",
                    isLarge ? "h-12 pl-4 text-base" : "h-10 pl-3 text-sm"
                )}
            />

            {/* Right-side icon: X if there's text, Search icon otherwise */}
            <button
                type="button"
                onClick={value ? handleClear : undefined}
                className={cn(
                    "absolute right-3 top-1/2 -translate-y-1/2 text-muted",
                    value && "hover:text-terracotta cursor-pointer"
                )}
                aria-label={value ? "Clear search" : "Search"}
            >
                {value ? <X size={18} /> : <Search size={18} />}
            </button>
        </div>
    )
};