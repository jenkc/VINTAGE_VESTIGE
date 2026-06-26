"use client";

import { useState } from "react";
import ImageWithFallback from "@/components/ui/ImageWithFallback";
import { CONNECTION_MODE_COLORS } from "@/styles/theme";
import type { BridgeResult, ProductSummary } from "@/types";

/**
 * The runners-up menu under the current node: "› N other paths from here".
 * Collapsed by default so the default thread reads as one clean line.
 *
 * Each row shows the SAME "why" vocabulary as the Edge — a connection-mode
 * color dot + the reason (lineage reference or shared-entity summary) + the
 * bridge_score — so picking a branch is an informed choice, not a bare list.
 *
 * Picking a row calls onPick(bridge); the parent truncates the tail and
 * appends the chosen step (replace-the-tail, Decision #47).
 */

interface BranchTrayProps {
  /** The node these alternatives branch FROM. */
  fromId: number;
  /** Already-fetched, unvisited alternatives (the auto-pick removed). */
  alternatives: BridgeResult[];
  onPick: (bridge: BridgeResult) => void;
}

/** The "why" line for a single alternative — reason + colored mode dot. */
function branchWhy(bridge: BridgeResult, fromId: number): string {
  const shared = bridge.shared_entities ?? {};
  const lineageRef = shared.lineage_reference;
  if (lineageRef) return `Lineage · ${lineageRef}`;

  // pull a couple of human-readable entity values for the summary
  const reasons: string[] = [];
  const ordered: (keyof typeof shared)[] = [
    "named_movements",
    "construction_technique",
    "motif_family",
    "social_function",
    "garment_system",
    "designer",
    "influence_references",
  ];
  for (const key of ordered) {
    const val = shared[key];
    if (Array.isArray(val)) {
      for (const v of val) {
        if (reasons.length < 2) reasons.push(String(v));
      }
    }
  }
  // (fromId reserved for future "which end is which" copy; current rows are
  // symmetric on the reason, so it's unused in the string today.)
  void fromId;
  if (reasons.length > 0) return reasons.join(" + ");
  return "Connected";
}

function otherEnd(bridge: BridgeResult, fromId: number): ProductSummary {
  return bridge.source.id === fromId ? bridge.target : bridge.source;
}

export default function BranchTray({ fromId, alternatives, onPick }: BranchTrayProps) {
  const [open, setOpen] = useState(false);
  if (alternatives.length === 0) return null;

  const count = alternatives.length;

  return (
    <div className="mt-3.5">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="group flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.1em] text-grey-400 hover:text-accent transition-colors"
      >
        <span
          className="inline-block transition-transform duration-200"
          style={{ transform: open ? "rotate(90deg)" : "none" }}
          aria-hidden
        >
          ›
        </span>
        {count} other path{count > 1 ? "s" : ""} from here
      </button>

      {open && (
        <ul className="mt-3 flex flex-col">
          {alternatives.map((alt) => {
            const target = otherEnd(alt, fromId);
            const mode = alt.connection_mode ?? "shared_entity";
            const dot = CONNECTION_MODE_COLORS[mode] ?? "#9B9B9B";
            const score = alt.bridge_score;
            return (
              <li key={alt.id}>
                <button
                  type="button"
                  onClick={() => onPick(alt)}
                  className="group grid w-full grid-cols-[56px_1fr_auto] items-center gap-4 border-t border-grey-100 px-1 py-3.5 text-left hover:bg-off-white transition-colors"
                >
                  <div className="w-[56px] aspect-[3/4] bg-off-white overflow-hidden">
                    {target.primary_image ? (
                      <ImageWithFallback
                        src={target.primary_image}
                        alt={target.display_title || target.title}
                        width={56}
                        height={72}
                        className="w-full h-full object-contain"
                      />
                    ) : (
                      <div className="w-full h-full bg-gradient-to-br from-grey-100 to-grey-200" />
                    )}
                  </div>

                  <div className="min-w-0">
                    <p className="font-display text-[15px] font-semibold leading-tight text-black group-hover:text-accent transition-colors truncate">
                      {target.display_title || target.title}
                    </p>
                    <p className="mt-1.5 flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-[0.05em] text-grey-600">
                      <span
                        className="inline-block w-1.5 h-1.5 rounded-full shrink-0"
                        style={{ backgroundColor: dot }}
                        aria-hidden
                      />
                      <span className="truncate">{branchWhy(alt, fromId)}</span>
                    </p>
                  </div>

                  <span className="font-mono text-[12px] text-grey-400 group-hover:text-dark transition-colors tabular-nums">
                    {score != null ? score.toFixed(2) : "—"}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
