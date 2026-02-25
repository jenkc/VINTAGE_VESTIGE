import { PLATFORM_COLORS, PLATFORM_NAMES } from "@/styles/theme";

interface PlatformBadgeProps {
    platform: string;
}

export default function PlatformBadge({ platform }: PlatformBadgeProps) {
    const name = PLATFORM_NAMES[platform as keyof typeof PLATFORM_NAMES] ?? platform;
    const color = PLATFORM_COLORS[platform as keyof typeof PLATFORM_COLORS] ?? "#8A7E74";

    return (
        <span
            className="inline-flex items-center rounded-[20px] bg-warm-white/[0.92] backdrop-blur-sm px-2.5 py-1 font-serif text-[10px] font-semibold"
            style={{ color }}
        >
            {name}
        </span>
    );
}