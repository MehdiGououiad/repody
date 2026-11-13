import type { Locale } from "@/lib/site";

/**
 * A real screen of the product in a quiet window frame, in the reader's language and colour
 * scheme. The images are captured from the running product (1440 × 900 at 2×, WebP).
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
      <picture>
        <source srcSet={`${base}-dark.webp`} media="(prefers-color-scheme: dark)" />
        <img
          src={`${base}-light.webp`}
          alt={alt}
          width={2000}
          height={1250}
          loading={priority ? "eager" : "lazy"}
          fetchPriority={priority ? "high" : "auto"}
          decoding="async"
          className="block h-auto w-full"
        />
      </picture>
    </figure>
  );
}
