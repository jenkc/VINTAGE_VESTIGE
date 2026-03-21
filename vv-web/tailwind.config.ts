import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Core — monochrome base
        "off-white":     "#F5F5F0",
        black:           "#0A0A0A",
        dark:            "#1A1A1A",
        "grey-600":      "#6B6B6B",
        "grey-400":      "#9B9B9B",
        "grey-200":      "#E0E0E0",
        "grey-100":      "#F0F0F0",
        // Accent — one sharp color, used sparingly
        accent:          "#C4553A",
        "accent-hover":  "#A8432E",
        // Signal colors — data viz only
        "signal-blue":   "#2E5A88",
        "signal-brown":  "#8B5E3C",
        "signal-sage":   "#7A8B6F",
        // Platform labels — text color only, never fills
        met:             "#8B2332",
        smithsonian:     "#2E5A88",
        fashionpedia:    "#6B6B6B",
        va_museum:       "#4A4A4A",
      },
      fontFamily: {
        display:   ["var(--font-display)", "sans-serif"],
        editorial: ["var(--font-editorial)", "serif"],
        mono:      ["var(--font-mono)", "monospace"],
      },
      borderRadius: {
        none: "0px",
        sm:   "4px",
        tag:  "999px",
      },
    },
  },
  plugins: [],
};
export default config;
