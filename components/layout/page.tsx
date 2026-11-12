import { cn } from "@/lib/utils";

/**
 * Every page: a 44px header bar with its title (and a breadcrumb trail) and its actions, then the
 * body. Lists run edge to edge (`bleed`); other pages get a padded, width-capped body.
 */
export function Page({
  title,
  trail,
  actions,
  bleed = false,
  className,
  children,
}: {
  title: React.ReactNode;
  /** Parent pages, left of the title: `[{ href, label }]`. */
  trail?: React.ReactNode;
  actions?: React.ReactNode;
  bleed?: boolean;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-full flex-col">
      <header className="sticky top-0 z-20 flex h-11 shrink-0 items-center gap-3 border-b border-line bg-panel px-4 md:px-5">
        <h1 className="flex min-w-0 flex-1 items-center gap-1.5 truncate text-sm font-medium text-ink">
          {trail}
          {title}
        </h1>
        {actions ? <div className="flex shrink-0 items-center gap-1.5">{actions}</div> : null}
      </header>
      <div
        className={cn(
          "flex-1",
          !bleed && "mx-auto w-full max-w-[1200px] px-4 py-6 md:px-8 md:py-8",
          className
        )}
      >
        {children}
      </div>
    </div>
  );
}

/** A section inside a page: a quiet title, an optional one-line hint, and its content. */
export function Section({
  title,
  hint,
  actions,
  className,
  children,
}: {
  title: string;
  hint?: string;
  actions?: React.ReactNode;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <section className={cn("flex flex-col gap-3", className)}>
      <div className="flex items-end justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-ink">{title}</h2>
          {hint ? <p className="mt-0.5 text-sm text-ink-3">{hint}</p> : null}
        </div>
        {actions ? <div className="flex shrink-0 items-center gap-1.5">{actions}</div> : null}
      </div>
      {children}
    </section>
  );
}
