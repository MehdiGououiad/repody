import "server-only";
import type { ThemeInput } from "@/lib/theme/generate";

/**
 * The deployment's brand: each client runs their own deployment, so the brand is set once per
 * deployment (REPODY_BRAND_* in the web container's environment). Unset values keep Repody's.
 */
export type Brand = ThemeInput & {
  name: string;
  /** A logo image URL; without one the product name is the logo. */
  logoUrl: string | null;
  /** Corner radius of controls in px (0 to 12); panels and dialogs follow from it. */
  radius: number;
};

const DEFAULT_BRAND: Brand = {
  name: "Repody",
  logoUrl: null,
  base: "oklch(0.6 0.006 75)", // a warm grey
  accent: "oklch(0.55 0.15 255)", // ink blue
  contrast: 50,
  radius: 6,
};

const number = (value: string | undefined, fallback: number) => {
  const parsed = Number(value);
  return value && Number.isFinite(parsed) ? parsed : fallback;
};

export function currentBrand(): Brand {
  const env = process.env;
  return {
    name: env.REPODY_BRAND_NAME?.trim() || DEFAULT_BRAND.name,
    logoUrl: env.REPODY_BRAND_LOGO_URL?.trim() || DEFAULT_BRAND.logoUrl,
    base: env.REPODY_BRAND_BASE?.trim() || DEFAULT_BRAND.base,
    accent: env.REPODY_BRAND_ACCENT?.trim() || DEFAULT_BRAND.accent,
    contrast: number(env.REPODY_BRAND_CONTRAST, DEFAULT_BRAND.contrast),
    radius: number(env.REPODY_BRAND_RADIUS, DEFAULT_BRAND.radius),
  };
}
