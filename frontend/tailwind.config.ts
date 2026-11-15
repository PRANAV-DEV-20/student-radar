import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        void: {
          DEFAULT: "#06070B",
          card: "#0E1017",
          border: "rgba(255, 255, 255, 0.08)",
          subtle: "#1F2430"
        },
        editorial: {
          paper: "#F8F9FA",
          card: "#FFFFFF",
          ink: "#111827",
          subtle: "#4B5563",
          border: "#E5E7EB"
        },
        horizon: {
          indigo: "#6366F1",
          violet: "#A855F7",
          glow: "rgba(99, 102, 241, 0.25)"
        },
        status: {
          verified: "#10B981",
          urgent: "#F59E0B",
          error: "#EF4444"
        }
      },
      fontFamily: {
        serif: ["Newsreader", "Playfair Display", "Georgia", "serif"],
        sans: ["Plus Jakarta Sans", "Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Geist Mono", "monospace"]
      },
      backgroundImage: {
        "horizon-radial": "radial-gradient(ellipse at 50% -20%, rgba(99, 102, 241, 0.35) 0%, rgba(6, 7, 11, 0) 70%)",
        "horizon-accent": "linear-gradient(135deg, #6366F1 0%, #A855F7 100%)",
      },
      animation: {
        "pulse-subtle": "pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      }
    },
  },
  plugins: [],
};
export default config;

