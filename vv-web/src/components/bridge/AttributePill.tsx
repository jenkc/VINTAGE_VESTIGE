interface AttributePillProps {
  label: string;
  value: string;
  size?: "default" | "sm";
}

export default function AttributePill({ label, value, size = "default" }: AttributePillProps) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-tag border border-grey-200 ${
      size === "sm" ? "px-2 py-0.5" : "px-3 py-1"
    }`}>
      <span className="text-[9px] font-semibold uppercase tracking-wider text-grey-600">
        {label}
      </span>
      <span className="text-[9px] text-grey-600">·</span>
      <span className={`${size === "sm" ? "text-[9.5px]" : "text-[11px]"} text-grey-600`}>
        {value}
      </span>
    </span>
  );
}
