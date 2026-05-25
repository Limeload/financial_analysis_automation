import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas:  "#0A0A0A",
        surface: "#111111",
        raised:  "#181818",
        overlay: "#1F1F1F",
        line:    "#262626",
        subtle:  "#333333",
        muted:   "#525252",
        dim:     "#737373",
        secondary: "#A3A3A3",
        primary: "#FAFAFA",
        accent:  { DEFAULT: "#7C3AED", hover: "#6D28D9", soft: "#4C1D95" },
        pos:     { DEFAULT: "#22C55E", bg: "#052E16" },
        neg:     { DEFAULT: "#EF4444", bg: "#450A0A" },
        warn:    { DEFAULT: "#F59E0B", bg: "#451A03" },
        info:    { DEFAULT: "#3B82F6", bg: "#172554" },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      fontSize: {
        "2xs": ["0.625rem", { lineHeight: "0.875rem" }],
      },
      animation: {
        "fade-in": "fadeIn 0.2s ease-out",
        "slide-up": "slideUp 0.25s ease-out",
        pulse2: "pulse2 2s ease-in-out infinite",
      },
      keyframes: {
        fadeIn:  { from: { opacity: "0" }, to: { opacity: "1" } },
        slideUp: { from: { opacity: "0", transform: "translateY(8px)" }, to: { opacity: "1", transform: "translateY(0)" } },
        pulse2:  { "0%,100%": { opacity: "1" }, "50%": { opacity: "0.4" } },
      },
    },
  },
  plugins: [],
} satisfies Config;
