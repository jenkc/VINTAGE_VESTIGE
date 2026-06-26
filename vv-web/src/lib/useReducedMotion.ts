"use client";

import { useEffect, useState } from "react";

/**
 * Subscribes to the OS `prefers-reduced-motion: reduce` setting.
 *
 * The CSS media query in globals.css is the real guarantee for the
 * declarative animations; this hook keeps the JS-scheduled motion honest
 * (scrollIntoView behavior, the deliberate "Following the thread…" beat,
 * and whether to add the .thread-drawing class at all).
 *
 * Starts `false` so SSR and first paint match the common case, then
 * reconciles on mount. Re-renders if the user toggles the OS setting.
 */
export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const onChange = (e: MediaQueryListEvent) => setReduced(e.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  return reduced;
}
