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
        background: "var(--bg-dark)",
        foreground: "var(--text-main)",
        panel: "var(--bg-panel)",
        card: "var(--bg-card)",
        muted: "var(--text-muted)",
        cyan: { DEFAULT: "#00f3ff", 400: "#00f3ff" },
        safe: "#00ff88",
        warning: "#ffb700",
        danger: "#ff0055",
        purple: { DEFAULT: "#8a2be2" },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Courier New", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
