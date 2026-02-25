interface EraBadgeProps {
  era: string;
  date?: string | null;
}

export default function EraBadge({ era, date }: EraBadgeProps) {
  const label = date ? `${era} · ${date}` : era;

  return (
    <span className="inline-flex items-center rounded-md bg-charcoal/[0.72] backdrop-blur-sm px-2.5 py-0.5 font-serif text-[11px] text-cream">
      {label}
    </span>
  );
}
