import { generateTheme, type ThemeInput } from "@/lib/shared/theme-generate";

/** Repody's own brand, the product's default (lib/theme/brand.ts). */
export const REPODY_BRAND: ThemeInput = {
  base: "oklch(0.6 0.006 75)",
  accent: "oklch(0.55 0.15 255)",
  contrast: 50,
};

const block = (selector: string, tokens: Record<string, string>) =>
  `${selector}{${Object.entries(tokens)
    .map(([name, value]) => `${name}:${value}`)
    .join(";")}}`;

/** The same tokens as the product: light, and dark under `.dark` (the reader's system until they
 * choose, see components/theme-toggle.tsx). */
export function siteStylesheet(): string {
  const radius = {
    "--radius-sm": "2px",
    "--radius-md": "4px",
    "--radius-lg": "6px",
    "--radius-xl": "10px",
  };
  return [
    block(":root", { ...radius, ...generateTheme(REPODY_BRAND, "light"), "color-scheme": "light" }),
    block(".dark", { ...generateTheme(REPODY_BRAND, "dark"), "color-scheme": "dark" }),
  ].join("");
}
