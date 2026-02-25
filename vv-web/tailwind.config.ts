import { Pill } from "lucide-react";
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
        // Core
        cream:           "#F7F3ED",
        "cream-dark":    "#F0ECE4",
        "warm-white":    "#FFFCF7",
        charcoal:        "#2C2420",
        "charcoal-soft": "#4A423A",
        muted:           "#8A7E74",
        // Borders
        border:          "#E8E0D4",
        "border-light":  "#D9D0C4",
        // Accents
        terracotta:      "#C4553A",
        gold:            "#B8924A",
        sage:            "#7A8B6F",
        "sage-dark":     "#5C7A5E",
        "sage-text":     "#4A5A40",
        // Platform badges
        met:             "#8B2332",
        smithsonian:     "#2E5A88",
        fashionpedia:    "#5C7A5E",
        etsy:            "#D35400",
        depop:           "#FF2300",
        // Score breakdown
        semantic:        "#2E5A88",
        visual:          "#8B5E3C",
        structural:      "#7A8B6F",
      },
      fontFamily: {
        serif: ["var(--font-serif)"],
        sans: ["var(--font-sans)"],
      },
      boxShadow: {
        card: "0 2px 8px rgba(44,36,32,0.04)",
        "card-hover": "0 20px 40px rgba(44,36,32,0.12), 0 4px 12px rgba(44,36,32,0.06)",
        connector: "0 4px 16px rgba(44,36,32,0.15)",
      },
      borderRadius: {
        sm: "10px",
        md: "12px",
        lg: "16px",
        pill: "20px",
      },
    },
  },
  plugins: [],
};
export default config;