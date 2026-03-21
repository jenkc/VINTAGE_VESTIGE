"use client";

export default function GlobalError({ reset }: { reset: () => void }) {
    return (
        <html lang="en">
            <body className="flex min-h-screen flex-col items-center justify-center bg-white px-6">
                <h1 className="font-display text-4xl font-bold text-black">
                    Something went wrong
                </h1>
                <p className="mt-3 text-dark">
                    An unexpected error occurred. Please try again.
                </p>
                <button
                    onClick={reset}
                    className="mt-8 text-sm font-medium text-accent hover:underline"
                >
                    Try again
                </button>
            </body>
        </html>
    );
}
