import type { Locale } from "@/lib/site";

/**
 * A real screen of the product in a quiet window frame, in the reader's language and theme (the
 * header's switch). Captured from the running product by scripts/capture-site-screens.mjs
 * (1440 × 900 at 2×, WebP).
 */
export function Screenshot({
  name,
  locale,
  alt,
  priority = false,
  className = "",
}: {
  name: string;
  locale: Locale;
  alt: string;
  priority?: boolean;
  className?: string;
}) {
  const base = `/screens/${name}-${locale}`;
  return (
    <figure className={`overflow-hidden rounded-xl bg-panel shadow-frame ${className}`}>
      <div
        className="flex h-8 items-center gap-1.5 border-b border-line bg-canvas px-3"
        aria-hidden
      >
        <span className="size-2.5 rounded-full bg-line-strong" />
        <span className="size-2.5 rounded-full bg-line-strong" />
        <span className="size-2.5 rounded-full bg-line-strong" />
      </div>
      {/* Both themes, the one the page shows displayed (an image display:none is not fetched). */}
      {(["light", "dark"] as const).map((theme) => (
        // biome-ignore lint/performance/noImgElement: a static export serves these WebP files as is.
        <img
          key={theme}
          src={`${base}-${theme}.webp`}
          alt={alt}
          width={2000}
          height={1250}
          loading={priority ? "eager" : "lazy"}
          fetchPriority={priority ? "high" : "auto"}
          decoding="async"
          className={`h-auto w-full ${theme === "dark" ? "hidden dark:block" : "block dark:hidden"}`}
        />
      ))}
    </figure>
  );
}
