"use client";

/**
 * Decorative hero animation: a "thread" draws itself down the page, dropping
 * garment-nodes as it passes them, then loops — a quiet, looping echo of the
 * Thread Pull interaction. Pure CSS/SVG, no data, no deps. aria-hidden.
 *
 * Honors prefers-reduced-motion (via the CSS in globals.css): the line and
 * nodes appear in their settled state with no looping draw.
 */

// Node positions along the vertical thread (in the 200×620 viewBox), each with a
// real garment thumbnail that appears beside the dot — alternating sides — so the
// hero shows what Thread Pull actually surfaces (the dark-silk / brocade lineage,
// seeded from /thread/2336?path=2336.3336). Slight horizontal sway so the thread
// reads as hand-drawn, not a ruler line.
const IMG = (id: number) =>
    `https://tusswxlrdoamintvswjs.supabase.co/storage/v1/object/public/product-images/${id}.jpg`;

const NODES: { cx: number; cy: number; side: "left" | "right"; img: string }[] = [
    { cx: 100, cy: 70,  side: "right", img: IMG(2336) }, // Brown Wool Bustle Dress
    { cx: 118, cy: 190, side: "left",  img: IMG(3336) }, // Black Silk Mourning Gown
    { cx: 86,  cy: 310, side: "right", img: IMG(2220) }, // Black Silk Velvet Ensemble
    { cx: 112, cy: 430, side: "left",  img: IMG(303)  }, // Sage Green Brocade Ballgown
    { cx: 92,  cy: 545, side: "right", img: IMG(2659) }, // Green Brocade Open Robe
];

// cy in the 620-tall viewBox → percentage top for the overlaid HTML thumbnails.
const VB_HEIGHT = 620;

// A gentle path threading through the nodes (cubic curves between them).
const THREAD_D = `
    M 100 40
    C 100 110, 118 130, 118 190
    C 118 250, 86 250, 86 310
    C 86 370, 112 370, 112 430
    C 112 490, 92 490, 92 545
    L 92 580
`;

export default function HeroThread() {
    return (
        <div className="hero-thread-stage">
            <svg
                className="hero-thread"
                viewBox="0 0 200 620"
                fill="none"
                aria-hidden="true"
                preserveAspectRatio="xMidYMid meet"
            >
                {/* faint static guide so the space isn't empty before the draw starts */}
                <path d={THREAD_D} stroke="var(--color-grey-100, #F0F0F0)" strokeWidth="1.5" />

                {/* the thread that draws itself */}
                <path
                    className="hero-thread-line"
                    d={THREAD_D}
                    stroke="#C4553A"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                />

                {/* garment-nodes: appear as the line reaches them, staggered down */}
                {NODES.map((n, i) => (
                    <g key={i} className="hero-thread-node" style={{ ["--i" as string]: i }}>
                        <circle cx={n.cx} cy={n.cy} r="9" fill="var(--color-off-white, #F5F5F0)" stroke="#C4553A" strokeWidth="1" />
                        <circle cx={n.cx} cy={n.cy} r="3" fill="#C4553A" />
                    </g>
                ))}
            </svg>

            {/* Real garment thumbnails overlaid beside each dot, alternating sides.
                Positioned by % to match each node's cy; share the node's --i stagger. */}
            {NODES.map((n, i) => (
                <img
                    key={i}
                    src={n.img}
                    alt=""
                    aria-hidden="true"
                    loading="lazy"
                    className="hero-thumb"
                    style={{
                        ["--i" as string]: i,
                        top: `${(n.cy / VB_HEIGHT) * 100}%`,
                        ...(n.side === "right"
                            ? { left: "calc(50% + 16px)" }
                            : { right: "calc(50% + 16px)" }),
                    }}
                />
            ))}
        </div>
    );
}
