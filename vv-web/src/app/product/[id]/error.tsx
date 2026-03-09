"use client";

export default function Error({ reset }: { reset: () => void }) {
    return (
        <div className="flex min-h-[60vh] flex-col items-center justify-center bg-cream-dark px-6">
            <h1 className="font-serif text-4xl font-bold text-charcoal">
                Something went wrong
            </h1>
            <p className="mt-3 text-charcoal-soft">
                We couldn&apos;t load this product. Please try again.
            </p>
            <button
                onClick={reset}
                className="mt-8 text-sm font-medium text-terracotta hover:underline"
            >
                Try again
            </button>
        </div>
    )
}