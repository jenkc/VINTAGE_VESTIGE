import Link from "next/link";
import { getExploreFunctions } from "@/lib/api"

export const dynamic = 'force-dynamic';

export default async function ExploreFuntionsPage() {
    const data = await getExploreFunctions();

    return (
        <div className="mx-auto max-w-5xl px-4 py-10">
            <h1 className="font-serif text-3xl font-bold text-charcoal">
                Explore by Social Function
            </h1>
            <p className="mt-2 text-sm text-charcoal-soft">
                How garments across eras and cultures serve the same human purposes.
            </p>
            <div className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
                {data.functions.map((socialFunc) => (
                    <Link
                        key={socialFunc.function}
                        href={`/explore/functions/${encodeURIComponent(socialFunc.function)}`}
                        className="group flex flex-col items-center gap-2 rounded-xl border border-border bg-warm-white px-4 py-6 shadow-card transition-all hover:-translate-y-0.5 hover:shadow-md"
                    >
                        <span className="font-serif text-sm font-bold text-charcoal group-hover:text-terracotta">
                            {socialFunc.function}
                        </span>
                        <span className="text-xs text-muted">
                            {socialFunc.count} {socialFunc.count === 1 ? "garment" : "garments"}
                        </span>
                    </Link>
                ))}
            </div>
        </div>
    );
}

