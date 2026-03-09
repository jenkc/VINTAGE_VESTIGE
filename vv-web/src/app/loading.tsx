import Skeleton from "@/components/ui/Skeleton";

export default function Loading() {
    return (
        <div>
            {/* Hero skeleton */}
            <section className="bg-cream-dark px-6 pt-24 pb-16">
                <div className="mx-auto flex max-w-[680px] flex-col items-center space-y-6">
                    <Skeleton className="h-4 w-32" />
                    <Skeleton className="h-14 w-full" />
                    <Skeleton className="h-6 w-3/4" />
                    <div className="flex gap-4 pt-4">
                        <Skeleton className="h-11 w-36 rounded-full" />
                        <Skeleton className="h-11 w-36 rounded-full" />
                    </div>
                </div>
            </section>

            {/* How it Works skeleton */}
            <section className="px-6 py-20 md:px-12">
                <div className="mx-auto max-w-[960px] space-y-8">
                    <Skeleton className="mx-auto h-10 w-48" />
                    <div className="grid gap-8 md:grid-cols-3">
                        <Skeleton className="h-52 rounded-2xl" />
                        <Skeleton className="h-52 rounded-2xl" />
                        <Skeleton className="h-52 rounded-2xl" />
                    </div>
                </div>
            </section>
        </div>
    );
}