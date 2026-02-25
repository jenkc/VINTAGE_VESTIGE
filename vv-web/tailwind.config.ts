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
        // Vintage Vestige brand colors — inspired by vintage botanical palettes
        vintage: {
          cream: "#F7F3EC",     // lighter, less yellow — warm off-white
          beige: "#E0D0B0",     // Cremeus — honey cream
          sand: "#C9A96E",      // Ochraceus — true ochre gold
          taupe: "#8B7E74",     // Plumbeus — warm dusty gray
          burgundy: "#722F37",  // Vinosus — deep wine red
          sage: "#7B8F6E",      // Prasinus — muted olive sage
          charcoal: "#2B2B2B",  // Ardesiacus — near black
          navy: "#1B2838",      // Atro-cyaneus — deep ink blue
          caerulean: "#6B8FAD", // Caeruleus — dusty cornflower
          lilac: "#9B8EB0",     // Violaceus — muted lavender
          plum: "#4A2040",      // Atro-violaceus — deep plum
        },
      },
      fontFamily: {
        serif: ["var(--font-serif)"],
        sans: ["var(--font-sans)"],
      },
    },
  },
  plugins: [],
};
export default config;