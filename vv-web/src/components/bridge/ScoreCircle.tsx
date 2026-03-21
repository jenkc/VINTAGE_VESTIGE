interface ScoreCircleProps {
  score: number;
}

export default function ScoreCircle({ score }: ScoreCircleProps) {
  const percent = Math.round(score * 100);

  return (
    <span
      className="font-mono text-sm text-grey-600"
      role="img"
      aria-label={`${percent}% match score`}
    >
      {percent}%
    </span>
  );
}
