import Skeleton from "@/components/ui/Skeleton";

export default function Loading() {
    return (
        <div className="bg-cream-dark px-6 pt-12 pb-20 md:px-12">
            <div className="mx-auto grid max-w-[1200px] gap-12 md:grid-cols-2">
                <Skeleton className="aspect-[3/4] rounded-2xl" />
                <div className="space-y-4">
                    <Skeleton className="h-6 w-24" />
                    <Skeleton className="h-10 w-3/4" />
                    <Skeleton className="h-24 w-full" />
                </div>
            </div>
        </div>
    );
}