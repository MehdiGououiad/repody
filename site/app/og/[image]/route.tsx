import { formatHex } from "culori";
import { ImageResponse } from "next/og";
import { dict } from "@/content";
import { generateTheme } from "@/lib/shared/theme-generate";
import { LOCALES, type Locale } from "@/lib/site";
import { REPODY_BRAND } from "@/lib/theme";

export const dynamic = "force-static";
export const dynamicParams = false;

/** /og/fr.png and /og/en.png: real files with an extension, so any static host serves them as images. */
export function generateStaticParams() {
  return LOCALES.map((locale) => ({ image: `${locale}.png` }));
}

/** The social card of every page: the promise and the proof, in the brand's dark theme. */
export async function GET(_request: Request, { params }: { params: Promise<{ image: string }> }) {
  const { image } = await params;
  const locale = image.replace(/\.png$/, "") as Locale;
  const t = dict(locale).home;
  const tokens = generateTheme(REPODY_BRAND, "dark");
  // The image renderer reads hex, not OKLCH.
  const c = (name: string) => formatHex(tokens[name]) ?? "#000000";
  return new ImageResponse(
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        width: "100%",
        height: "100%",
        padding: 72,
        background: c("--canvas"),
        color: c("--ink"),
      }}
    >
      <div
        style={{ display: "flex", alignItems: "center", gap: 16, fontSize: 32, fontWeight: 600 }}
      >
        <div
          style={{
            display: "flex",
            width: 44,
            height: 44,
            borderRadius: 10,
            background: c("--accent"),
            alignItems: "center",
            justifyContent: "center",
            color: c("--on-accent"),
            fontSize: 26,
          }}
        >
          R
        </div>
        Repody
      </div>
      <div
        style={{
          display: "flex",
          marginTop: 64,
          fontSize: 64,
          fontWeight: 600,
          lineHeight: 1.08,
          letterSpacing: -1.5,
          maxWidth: 980,
        }}
      >
        {t.hero.title}
      </div>
      <div
        style={{ display: "flex", marginTop: "auto", gap: 48, fontSize: 24, color: c("--ink-3") }}
      >
        {t.proof.slice(0, 3).map((p) => (
          <div
            key={p.label}
            style={{ display: "flex", flexDirection: "column", gap: 6, maxWidth: 300 }}
          >
            <span style={{ fontSize: 44, fontWeight: 600, color: c("--ink") }}>{p.value}</span>
            <span>{p.label}</span>
          </div>
        ))}
      </div>
    </div>,
    { width: 1200, height: 630 }
  );
}
