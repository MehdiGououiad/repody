import {
  clampChroma,
  converter,
  formatCss,
  formatHex,
  type Oklch,
  parse,
  wcagContrast,
} from "culori";

const toOklchSpace = converter("oklch");

/**
 * A theme from three inputs, as Linear generates its themes (base, accent, contrast), in OKLCH so
 * equal lightness looks equally light whatever the hue. Every colour token of the interface comes
 * out of here; components only read the tokens.
 */
export type ThemeInput = {
  /** The neutral: its hue and chroma tint every surface, line and text (keep it near grey). */
  base: string;
  /** The one colour of the interface: primary action, focus, selection. */
  accent: string;
  /** 30 (soft) to 100 (crisp): how far apart surfaces, lines and ink levels sit. */
  contrast: number;
};

type Mode = "light" | "dark";
type ThemeTokens = Record<string, string>;

const toOklch = (color: string): Oklch => {
  const parsed = parse(color);
  if (!parsed) throw new Error(`Not a colour: ${color}`);
  const oklch = toOklchSpace(parsed);
  return { mode: "oklch", l: oklch.l, c: oklch.c ?? 0, h: oklch.h ?? 0 };
};

const css = (l: number, c: number, h: number, alpha?: number): string =>
  formatCss(
    clampChroma({ mode: "oklch", l: Math.min(Math.max(l, 0), 1), c, h, alpha }, "oklch") as Oklch
  );

/** The colour moved in lightness (darker or lighter) until it reaches `ratio` against `bg`. */
function withContrast(color: Oklch, bg: string, ratio: number, direction: -1 | 1): Oklch {
  // Measured on the colour as it will be written (clamped into the gamut), with a small margin
  // so rounding in the stylesheet never lands it under the ratio.
  const shown = (c: Oklch) => formatHex(clampChroma(c, "oklch") as Oklch);
  let current = { ...color };
  for (let i = 0; i < 40 && wcagContrast(shown(current), bg) < ratio + 0.05; i++) {
    current = { ...current, l: Math.min(Math.max(current.l + direction * 0.02, 0), 1) };
  }
  return current;
}

export function generateTheme(input: ThemeInput, mode: Mode): ThemeTokens {
  const base = toOklch(input.base);
  const accent = toOklch(input.accent);
  const k = Math.min(Math.max((input.contrast - 30) / 70, 0), 1);
  const h = base.h ?? 0;
  // Dark surfaces stay almost neutral: a tinted black reads as grey-blue on OLED panels.
  const surfaceC = Math.min(base.c, 0.03) * (mode === "dark" ? 0.35 : 1);
  const inkC = Math.min(base.c, 0.02);
  const light = mode === "light";

  // Surfaces step up in lightness: canvas (behind the chrome), panel (where work happens, the
  // brightest), raised (inside a panel), overlay (menus, dialogs), field (inputs, inset).
  // Dark is graphite, not black: panels a clear step above the canvas so cards and shadows
  // still read, and off-white text that does not bloom.
  const surface = light
    ? { canvas: 0.968 - 0.012 * k, panel: 0.998, raised: 0.978, overlay: 1, field: 0.99 }
    : { canvas: 0.16, panel: 0.215, raised: 0.245, overlay: 0.265, field: 0.19 };
  const ink = light
    ? [0.235 - 0.06 * k, 0.43 - 0.07 * k, 0.56 - 0.06 * k, 0.7 - 0.05 * k]
    : [0.93 + 0.03 * k, 0.76 + 0.04 * k, 0.6 + 0.04 * k, 0.47 + 0.04 * k];
  const inkL = light ? 0.18 : 0.98; // translucent ink: lines, hover and selection washes
  const alpha = (a: number) => css(inkL, inkC, h, a);
  const panelHex = formatHex({ mode: "oklch", l: surface.panel, c: surfaceC, h });

  // The fill of primary buttons: text on it reaches 4.5:1 with white or near-black, and when a
  // mid-lightness accent allows neither, the fill darkens until white text does.
  const darkText = { mode: "oklch" as const, l: 0.2, c: inkC, h };
  let accentFill: Oklch = light
    ? accent
    : { ...accent, l: Math.min(Math.max(accent.l, 0.5), 0.58) };
  const readable = (text: string) => wcagContrast(text, formatHex(accentFill)) >= 4.5;
  if (!readable("#ffffff") && !readable(formatHex(darkText))) {
    accentFill = withContrast(accentFill, "#ffffff", 4.5, -1);
  }
  const onAccent = readable("#ffffff") ? "oklch(1 0 0)" : css(darkText.l, darkText.c, h);
  const accentInk = withContrast(accentFill, panelHex, 4.5, light ? -1 : 1);

  // Status colours sit inside the palette: one lightness, toned-down chroma.
  const status = (hue: number) => {
    const fill = light ? { l: 0.56, c: 0.14 } : { l: 0.7, c: 0.12 };
    const inkTone = withContrast(
      { mode: "oklch", l: fill.l, c: fill.c, h: hue },
      panelHex,
      4.5,
      light ? -1 : 1
    );
    return {
      fill: css(fill.l, fill.c, hue),
      ink: css(inkTone.l, inkTone.c, hue),
      wash: css(fill.l, fill.c, hue, light ? 0.12 : 0.16),
    };
  };
  const pass = status(152);
  const warn = status(70);
  const fail = status(25);

  // Document colours: eight hues around the wheel from the accent's, at the status tone, so each
  // document of a workflow keeps one colour across the builder, rules, runs and report.
  const documents = Array.from({ length: 8 }, (_, i) => status(((accent.h ?? 250) + i * 45) % 360));
  const documentTokens = Object.fromEntries(
    documents.flatMap((d, i) => [
      [`--doc-${i + 1}`, d.fill],
      [`--doc-${i + 1}-ink`, d.ink],
      [`--doc-${i + 1}-wash`, d.wash],
    ])
  );

  return {
    "--canvas": css(surface.canvas, surfaceC, h),
    "--panel": css(surface.panel, surfaceC * 0.6, h),
    "--raised": css(surface.raised, surfaceC, h),
    "--overlay": css(surface.overlay, surfaceC * 0.5, h),
    "--field": css(surface.field, surfaceC, h),
    "--ink": css(ink[0], inkC, h),
    "--ink-2": css(ink[1], inkC, h),
    "--ink-3": css(ink[2], inkC, h),
    "--ink-4": css(ink[3], inkC, h),
    "--line": alpha(light ? 0.075 + 0.04 * k : 0.09 + 0.04 * k),
    "--line-strong": alpha(light ? 0.13 + 0.06 * k : 0.15 + 0.06 * k),
    "--hover": alpha(light ? 0.035 : 0.05),
    "--selected": alpha(light ? 0.065 : 0.09),
    "--accent": css(accentFill.l, accentFill.c, accentFill.h ?? 0),
    "--accent-hover": css(accentFill.l + (light ? -0.05 : 0.05), accentFill.c, accentFill.h ?? 0),
    "--accent-ink": css(accentInk.l, accentInk.c, accentInk.h ?? 0),
    "--accent-wash": css(accentFill.l, accentFill.c, accentFill.h ?? 0, light ? 0.11 : 0.18),
    "--on-accent": onAccent,
    "--focus": css(accentFill.l, accentFill.c, accentFill.h ?? 0, 0.55),
    "--pass": pass.fill,
    "--pass-ink": pass.ink,
    "--pass-wash": pass.wash,
    "--warn": warn.fill,
    "--warn-ink": warn.ink,
    "--warn-wash": warn.wash,
    "--fail": fail.fill,
    "--fail-ink": fail.ink,
    "--fail-wash": fail.wash,
    ...documentTokens,
    "--shadow-color": light ? css(0.2, inkC, h, 0.08) : "oklch(0 0 0 / 0.45)",
    // Charts: the accent leads, neutral steps follow.
    "--chart-1": css(accentFill.l, accentFill.c, accentFill.h ?? 0),
    "--chart-2": css(ink[2], inkC, h),
    "--chart-3": css(ink[3], inkC, h),
    "--chart-4": pass.fill,
    "--chart-5": fail.fill,
  };
}

const block = (selector: string, tokens: ThemeTokens) =>
  `${selector}{${Object.entries(tokens)
    .map(([name, value]) => `${name}:${value}`)
    .join(";")}}`;

/** The stylesheet for both modes, written into the page at server render (no flash). */
export function themeStylesheet(input: ThemeInput, radius: number): string {
  const r = Math.min(Math.max(radius, 0), 12);
  const shape = {
    "--radius-sm": `${Math.max(r - 2, 0)}px`,
    "--radius-md": `${r}px`,
    "--radius-lg": `${r + 2}px`,
    "--radius-xl": `${r + 6}px`,
  };
  return [
    block(":root", { ...shape, ...generateTheme(input, "light"), "color-scheme": "light" }),
    block(".dark", { ...generateTheme(input, "dark"), "color-scheme": "dark" }),
  ].join("");
}
