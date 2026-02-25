interface AttributePillProps {
  label: string;
  value: string;
}

export default function AttributePill({ label, value }: AttributePillProps) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-[20px] border border-sage/20 bg-sage/[0.07] px-2.5 py-1">
      <span className="text-[9px] font-semibold uppercase tracking-wider text-sage-dark">
        {label}
      </span>
      <span className="text-[9px] text-sage-dark">·</span>
      <span className="text-[11px] text-sage-text">
        {value}
      </span>
    </span>
  );
}
