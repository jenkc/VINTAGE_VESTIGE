import { SCORE_COLORS } from "@/styles/theme";

interface ScoreBreakdownProps {
    text: number;
    image: number | null;
    structural: number;
}

const BARS = [
    { key: "text", label: "Semantic", color: SCORE_COLORS.semantic },
    { key: "image", label: "Visual", color: SCORE_COLORS.visual },
    { key: "structural", label: "Structural", color: SCORE_COLORS.structural },
] as const;

export default function ScoreBreakdown({
    text,
    image,
    structural,
}: ScoreBreakdownProps) {
    const scores: Record<string, number | null> = {
        text,
        image,
        structural,
    };

    return (
        <div className="flex flex-col gap-2.5">
            {BARS.map((bar) => {
                const value = scores[bar.key];
                if (value === null) return null;
                const percent = Math.round(value * 100);

                return (
                    <div key={bar.key} className="flex items-center gap-3">
                        <span className="w-16 text-[8px] font-semibold uppercase tracking-wider text-muted">
                            {bar.label}
                        </span>
                        <div
                            className="h-[3px] flex-1 rounded-full bg-border"
                        >
                            <div
                                className="h-full rounded-full"
                                style={{
                                    width: `${percent}%`,
                                    backgroundColor: `${bar.color}99`,
                                }}
                            />
                        </div>
                        <span className="w-7 text-right text-[9px] font-bold text-charcoal-soft">
                            {percent}%
                        </span>
                    </div>
                );
            })}
        </div>
    );
}

