/**
 * A Thread Pull thread *is* a linear sequence of product IDs, origin first.
 * We encode it into the `?path=` query param on the existing /thread/[id]
 * route and replay it client-side — no backend, no new endpoint.
 *
 * Encoding: dot-joined positive integers, origin id first.
 *   encodePath([123, 456, 789]) === "123.456.789"
 *
 * Decoding is defensive: it tolerates a `null`/empty param, strips any
 * non-numeric or non-positive junk, so a hand-mangled URL degrades to a
 * shorter valid path (or just the origin) rather than throwing.
 */

export function encodePath(ids: number[]): string {
  return ids.filter((n) => Number.isInteger(n) && n > 0).join(".");
}

export function decodePath(raw: string | null | undefined): number[] {
  if (!raw) return [];
  return raw
    .split(".")
    .map((s) => Number(s))
    .filter((n) => Number.isInteger(n) && n > 0);
}
