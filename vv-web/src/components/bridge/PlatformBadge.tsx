import { PLATFORM_COLORS, PLATFORM_NAMES } from "@/styles/theme";

interface PlatformBadgeProps {
    platform: string;
}

export default function PlatformBadge({ platform }: PlatformBadgeProps) {
    const name = PLATFORM_NAMES[platform as keyof typeof PLATFORM_NAMES] ?? platform;
    const color = PLATFORM_COLORS[platform as keyof typeof PLATFORM_COLORS] ?? "#6B6B6B";

    return (
        <span
            className="font-mono text-[11px] uppercase tracking-wider"
            style={{ color }}
        >
            {name}
        </span>
    );
}
