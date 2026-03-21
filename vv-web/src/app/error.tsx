"use client";

export default function Error({ reset }: { reset: () => void }) {
    return (
        <div className="flex min-h-[60vh] flex-col items-center justify-center bg-white px-6">
            <h1 className="font-display text-4xl font-bold text-black">
                Something went wrong
            </h1>
            <p className="mt-3 text-dark">
                We couldn&apos;t load the page. Please try again.
            </p>
            <button
                onClick={reset}
                className="mt-8 text-sm font-medium text-accent hover:underline"
            >
                Try again
            </button>
        </div>
    );
}
