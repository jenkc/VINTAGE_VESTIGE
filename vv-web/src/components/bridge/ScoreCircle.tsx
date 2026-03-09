import { scoreColorByValue } from "@/styles/theme";

interface ScoreCircleProps {
  score: number;
}

export default function ScoreCircle({ score }: ScoreCircleProps) {
  const color = scoreColorByValue(score);
  const percent = Math.round(score * 100);

  return (
    <div
      className="flex flex-col items-center justify-center rounded-full size-11 md:size-[52px]"
      style={{ border: `2.5px solid ${color}` }}
      role="img"
      aria-label={`${percent}% match score`}
    >
      <span
        className="font-serif text-base font-bold leading-none"
        style={{ color }}
      >
        {percent}
      </span>
      <span
        className="font-serif text-[7px] uppercase tracking-wide leading-none"
        style={{ color }}
      >
        match
      </span>
    </div>
  );
}
