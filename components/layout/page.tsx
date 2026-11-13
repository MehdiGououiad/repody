import { cn } from "@/lib/utils";

/**
 * Every page: a 40px header bar (trail, title, status, actions), an optional toolbar row
 * (filters, view options), then the body. Lists bleed edge to edge; reading pages are capped.
 */
export function Page({
  title,
  trail,
  status,
  actions,
  toolbar,
  bleed = false,
  className,
  children,
}: {
  title: React.ReactNode;
  trail?: React.ReactNode;
  status?: React.ReactNode;
  actions?: React.ReactNode;
  toolbar?: React.ReactNode;
  bleed?: boolean;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-full flex-col">
      <header className="sticky top-0 z-20 shrink-0 border-b border-line bg-panel/90 backdrop-blur-md">
        <div className="flex h-10 items-center gap-2 px-4 md:px-5">
          <h1 className="flex min-w-0 items-center gap-1.5 truncate text-[13px] font-semibold text-ink">
            {trail}
            {title}
          </h1>
          {status}
          {actions ? (
            <div className="ms-auto flex shrink-0 items-center gap-1">{actions}</div>
          ) : null}
        </div>
        {toolbar ? (
          <div className="flex h-10 items-center gap-1.5 border-t border-line px-3 md:px-4">
            {toolbar}
          </div>
        ) : null}
      </header>
      <div
        className={cn(
          "flex-1",
          !bleed && "mx-auto w-full max-w-[1080px] px-4 py-6 md:px-8",
          className
        )}
      >
        {children}
      </div>
    </div>
  );
}

/** A trail entry: a parent page, then a slash. */
export function Crumb({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <>
      <a href={href} className="truncate font-medium text-ink-3 transition-colors hover:text-ink">
        {children}
      </a>
      <span className="text-ink-4" aria-hidden>
        /
      </span>
    </>
  );
}

/** A group inside a page: a title with an optional count and hint, its actions, its content. */
export function Section({
  title,
  count,
  hint,
  actions,
  className,
  children,
}: {
  title: string;
  count?: number;
  hint?: string;
  actions?: React.ReactNode;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <section className={cn("flex flex-col gap-2.5", className)}>
      <div className="flex items-end justify-between gap-3">
        <div className="min-w-0">
          <h2 className="flex items-center gap-2 text-[13px] font-semibold text-ink">
            {title}
            {count != null ? (
              <span className="font-normal tabular-nums text-ink-4">{count}</span>
            ) : null}
          </h2>
          {hint ? <p className="mt-0.5 text-xs text-ink-3">{hint}</p> : null}
        </div>
        {actions ? <div className="flex shrink-0 items-center gap-1">{actions}</div> : null}
      </div>
      {children}
    </section>
  );
}
