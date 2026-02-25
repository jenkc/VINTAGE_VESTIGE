import { cn } from "@/lib/utils";
import { ArrowLeftRight } from "lucide-react";

interface BridgeConnectorProps {
  variant?: "full" | "compact";
}

export default function BridgeConnector({
  variant = "full",
}: BridgeConnectorProps) {
  const isCompact = variant === "compact";

  return (
    <div
      className={cn(
        "flex items-center justify-center rounded-full border-gold bg-warm-white shadow-connector",
        isCompact
          ? "size-[30px] border-[1.5px]"
          : "size-11 border-2"
      )}
    >
      <ArrowLeftRight
        size={isCompact ? 14 : 18}
        className="text-gold"
      />
    </div>
  );
}
