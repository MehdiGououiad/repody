/**
 * BNP Paribas brand preset.
 * CSS mirror: app/theme.css — keep both in sync when editing colors.
 * To switch presets later: change ACTIVE_THEME_PRESET and import the matching theme.css.
 */
export const bnpParibasPreset = {
  id: "bnp-paribas",
  name: "Repody",
  colors: {
    primary: "#00965e",
    primaryDark: "#007348",
    primaryLight: "#39a87b",
    primarySoft: "#d4ede3",
    primaryGlow: "rgba(0, 150, 94, 0.22)",
    onPrimary: "#ffffff",
    secondary: "#1a1a1a",
    surface: "#f7faf8",
    onSurface: "#1a1a1a",
    sidebar: "#003d27",
    sidebarAccent: "#005c3a",
    success: "#00965e",
    warning: "#e67e22",
    danger: "#c0392b",
    info: "#007348",
  },
  fonts: {
    sans: "Source Sans 3",
    mono: "JetBrains Mono",
  },
} as const;

export type ThemePreset = typeof bnpParibasPreset;
