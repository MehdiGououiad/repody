"use client";

import { useMemo, useState } from "react";
import type { Dict } from "@/content";
import { generateTheme, type ThemeInput } from "@/lib/shared/theme-generate";
import { REPODY_BRAND } from "@/lib/theme";
import { Glyph } from "./glyph";

const PRESETS: (ThemeInput & { radius: number; initial: string })[] = [
  { ...REPODY_BRAND, radius: 6, initial: "R" },
  { base: "oklch(0.6 0.012 165)", accent: "#0f7a55", contrast: 60, radius: 4, initial: "B" },
  { base: "oklch(0.6 0.01 20)", accent: "#8c1d2f", contrast: 45, radius: 10, initial: "A" },
  { base: "oklch(0.6 0.008 60)", accent: "#e8590c", contrast: 70, radius: 2, initial: "T" },
];

/**
 * White label, shown: the product's own theme engine (lib/theme/generate.ts) runs in the page and
 * re-themes a miniature of the interface from one base colour, one accent and a contrast level.
 */
export function BrandSwitcher({ t }: { t: Dict["home"]["brand"] }) {
  const [index, setIndex] = useState(1);
  const [dark, setDark] = useState(false);
  const preset = PRESETS[index];
  const tokens = useMemo(() => generateTheme(preset, dark ? "dark" : "light"), [preset, dark]);
  const style = {
    ...tokens,
    "--r": `${preset.radius}px`,
    "--r2": `${preset.radius + 2}px`,
    background: "var(--canvas)",
    color: "var(--ink)",
  } as React.CSSProperties;
  const statuses = ["failed", "warning", "passed"] as const;

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)] lg:items-center">
      <div className="flex flex-col gap-4">
        <fieldset className="flex flex-col gap-4">
          <legend className="text-sm font-medium text-ink-2">{t.pick}</legend>
          <div className="flex flex-wrap gap-2">
            {t.presets.map((name, i) => (
              <label
                key={name}
                className="flex h-9 cursor-pointer items-center gap-2 rounded-md px-3 text-sm text-ink-2 shadow-[inset_0_0_0_1px_var(--line-strong)] transition-colors duration-100 hover:text-ink has-checked:text-ink has-checked:shadow-[inset_0_0_0_2px_var(--accent)] has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-accent"
              >
                <input
                  type="radio"
                  name="brand"
                  checked={index === i}
                  onChange={() => setIndex(i)}
                  className="sr-only"
                />
                <span
                  className="size-3 rounded-full"
                  style={{ background: PRESETS[i].accent }}
                  aria-hidden
                />
                {name}
              </label>
            ))}
          </div>
        </fieldset>
        <label className="flex w-fit cursor-pointer items-center gap-2 text-sm text-ink-3">
          <input
            type="checkbox"
            checked={dark}
            onChange={(e) => setDark(e.target.checked)}
            className="size-4 accent-[var(--accent)]"
          />
          {t.darkMode}
        </label>
      </div>

      <div
        style={style}
        className="overflow-hidden rounded-xl shadow-frame transition-[background-color] duration-300"
        aria-hidden
      >
        <div className="flex">
          <div className="hidden w-40 shrink-0 flex-col gap-1 p-3 sm:flex">
            <div className="mb-2 flex items-center gap-2">
              <span
                className="flex size-5 items-center justify-center text-[10px] font-semibold"
                style={{
                  background: "var(--accent)",
                  color: "var(--on-accent)",
                  borderRadius: "calc(var(--r) - 2px)",
                }}
              >
                {preset.initial}
              </span>
              <span className="text-xs font-semibold">{t.presets[index]}</span>
            </div>
            {[0, 1, 2, 3].map((i) => (
              <span
                key={i}
                className="h-6"
                style={{
                  background: i === 1 ? "var(--selected)" : "transparent",
                  borderRadius: "var(--r)",
                }}
              >
                <span
                  className="ms-2 mt-2.5 block h-1.5 w-16 rounded-full"
                  style={{ background: "var(--ink-4)", opacity: i === 1 ? 0.9 : 0.5 }}
                />
              </span>
            ))}
          </div>
          <div
            className="m-2 flex-1 overflow-hidden shadow-[0_0_0_1px_var(--line)] sm:ms-0"
            style={{ background: "var(--panel)", borderRadius: "var(--r2)" }}
          >
            <div
              className="flex h-10 items-center justify-between border-b px-4"
              style={{ borderColor: "var(--line)" }}
            >
              <span className="text-xs font-medium">{t.mock.title}</span>
              <span
                className="flex h-6 items-center px-2.5 text-[11px] font-medium"
                style={{
                  background: "var(--accent)",
                  color: "var(--on-accent)",
                  borderRadius: "var(--r)",
                }}
              >
                {t.mock.action}
              </span>
            </div>
            <ul>
              {t.mock.rows.map((row, i) => (
                <li
                  key={row}
                  className="flex h-11 items-center gap-2.5 border-b px-4 last:border-0"
                  style={{ borderColor: "var(--line)" }}
                >
                  <Glyph status={statuses[i]} />
                  <span className="text-xs font-medium">{row}</span>
                  <span className="ms-auto text-[11px]" style={{ color: "var(--ink-3)" }}>
                    {t.mock.status[i]}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
