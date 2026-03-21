import Link from "next/link";

export default function NotFound() {
    return (
        <div className="flex min-h-[60vh] flex-col items-center justify-center bg-white px-6">
            <h1 className="font-display text-4xl font-bold text-black">
                Product Not Found
            </h1>
            <p className="mt-3 text-dark">
                The garment you&apos;re looking for doesn&apos;t exist in our collection.
            </p>
            <Link
                href="/search"
                className="mt-8 text-sm font-medium text-accent hover:underline"
            >
                Back to Search
            </Link>
        </div>
    )
}
