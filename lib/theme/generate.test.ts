import { formatHex, parse, wcagContrast } from "culori";
import { describe, expect, it } from "bun:test";
import { generateTheme, themeStylesheet } from "@/lib/theme/generate";

const hex = (css: string) => {
  const color = parse(css);
  if (!color) throw new Error(`Not a colour: ${css}`);
  return formatHex({ ...color, alpha: undefined });
};

// Brands a client could plausibly bring: a pale yellow, a deep navy, a neon green, a red.
const BRANDS = [
  { base: "#8a8580", accent: "#2f6fde", contrast: 50 },
  { base: "#7d8a99", accent: "#f5d90a", contrast: 30 },
  { base: "#556070", accent: "#0b1f4b", contrast: 100 },
  { base: "#808080", accent: "#39ff14", contrast: 50 },
  { base: "#9a8e84", accent: "#c8102e", contrast: 70 },
];

describe("theme generation", () => {
  for (const brand of BRANDS) {
    for (const mode of ["light", "dark"] as const) {
      it(`keeps text readable for accent ${brand.accent} in ${mode} mode`, () => {
        const theme = generateTheme(brand, mode);
        const panel = hex(theme["--panel"]);
        // WCAG AA for body text and for the accent used as text.
        expect(wcagContrast(hex(theme["--ink"]), panel)).toBeGreaterThanOrEqual(7);
        expect(wcagContrast(hex(theme["--ink-2"]), panel)).toBeGreaterThanOrEqual(4.5);
        expect(wcagContrast(hex(theme["--accent-ink"]), panel)).toBeGreaterThanOrEqual(4.5);
        expect(wcagContrast(hex(theme["--fail-ink"]), panel)).toBeGreaterThanOrEqual(4.5);
        for (let i = 1; i <= 8; i++) {
          expect(wcagContrast(hex(theme[`--doc-${i}-ink`]), panel)).toBeGreaterThanOrEqual(4.5);
        }
        // Text on the accent fill picks white or near-black, whichever reads.
        expect(
          wcagContrast(hex(theme["--on-accent"]), hex(theme["--accent"]))
        ).toBeGreaterThanOrEqual(4.5);
      });
    }
  }

  it("draws dark mode on graphite, with panels a visible step above the canvas", () => {
    const theme = generateTheme(BRANDS[0], "dark");
    expect(hex(theme["--canvas"])).not.toBe("#000000");
    expect(wcagContrast(hex(theme["--panel"]), hex(theme["--canvas"]))).toBeGreaterThan(1.1);
  });

  it("writes both modes and the radius scale", () => {
    const css = themeStylesheet(BRANDS[0], 6);
    expect(css).toContain(":root{--radius-sm:4px;--radius-md:6px");
    expect(css).toContain(".dark{--canvas:");
  });
});
