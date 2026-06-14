import { bnpParibasPreset } from "@/lib/theme/presets/bnp-paribas";

/** Active brand preset — swap this import to change the default theme. */
export const ACTIVE_THEME_PRESET = bnpParibasPreset;

export { bnpParibasPreset };

export type BrandColors = typeof ACTIVE_THEME_PRESET.colors;
