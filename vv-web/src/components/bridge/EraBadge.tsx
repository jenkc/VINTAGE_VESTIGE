interface EraBadgeProps {
  era: string;
  date?: string | null;
}

export default function EraBadge({ era, date }: EraBadgeProps) {
  const label = date ? `${era} · ${date}` : era;

  return (
    <span className="font-mono text-[11px] text-grey-600">
      {label}
    </span>
  );
}
