interface AttributePillProps {
  label: string;
  value: string;
  size?: "default" | "sm";
}

export default function AttributePill({ label, value, size = "default" }: AttributePillProps) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-[20px] border border-sage/20 bg-sage/[0.07] ${
      size === "sm" ? "px-[9px] py-1 h-[20px]" : "px-[13px] py-px h-[26px]"
    }`}>
      <span className="text-[9px] font-semibold uppercase tracking-wider text-sage-dark">
        {label}
      </span>
      <span className="text-[9px] text-sage-dark">·</span>
      <span className={`${size === "sm" ? "text-[9.5px]" : "text-[11px]"} text-sage-text`}>
        {value}
      </span>
    </span>
  );
}
