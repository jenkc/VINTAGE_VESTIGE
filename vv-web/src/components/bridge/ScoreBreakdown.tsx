import { SCORE_COLORS } from "@/styles/theme";

interface ScoreBreakdownProps {
    text: number | null;
    image: number | null;
    entity: number | null;
    variant?: "vertical" | "horizontal";
}

const BARS = [
    { key: "text", label: "Text", color: SCORE_COLORS.text },
    { key: "image", label: "Image", color: SCORE_COLORS.image },
    { key: "entity", label: "Entity", color: SCORE_COLORS.entity },
] as const;

export default function ScoreBreakdown({
    text,
    image,
    entity,
    variant = "vertical",
}: ScoreBreakdownProps) {
    const scores: Record<string, number | null> = {
        text,
        image,
        entity,
    };

    return (
        <div className={variant === "horizontal" ? "flex gap-5" : "flex flex-col gap-2.5"}>
            {BARS.map((bar) => {
                const value = scores[bar.key];
                if (value === null || value === undefined) return null;
                // entity_score is unbounded (IDF-weighted), normalize for display
                const percent = bar.key === "entity"
                    ? Math.min(Math.round(value / 50 * 100), 100)
                    : Math.round(value * 100);

                return (
                    <div key={bar.key} className={variant === "horizontal"
                        ? "flex flex-1 flex-col gap-1"
                        : "flex items-center gap-3"
                    }>
                        {variant === "horizontal" ? (
                            <>
                                <div className="flex items-center justify-between">
                                    <span className="font-mono text-[8px] font-semibold uppercase tracking-[2.5px] text-grey-400">
                                        {bar.label}
                                    </span>
                                    <span className="font-mono text-[9px] font-bold" style={{ color: bar.color }}>
                                        {percent}%
                                    </span>
                                </div>
                                <div className="h-[2px] bg-grey-200">
                                    <div
                                        className="h-full"
                                        style={{
                                            width: `${percent}%`,
                                            backgroundColor: `${bar.color}99`,
                                        }}
                                    />
                                </div>
                            </>
                        ) : (
                            <>
                                <span className="w-12 font-mono text-[8px] font-semibold uppercase tracking-wider text-grey-400">
                                    {bar.label}
                                </span>
                                <div className="h-[2px] flex-1 bg-grey-200">
                                    <div
                                        className="h-full"
                                        style={{
                                            width: `${percent}%`,
                                            backgroundColor: `${bar.color}99`,
                                        }}
                                    />
                                </div>
                                <span className="w-7 text-right font-mono text-[9px] font-bold text-dark">
                                    {percent}%
                                </span>
                            </>
                        )}
                    </div>
                );
            })}
        </div>
    );
}
