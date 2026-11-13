import Link from "next/link";

export function Container({
  className = "",
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={`mx-auto w-full max-w-[1180px] px-5 md:px-8 ${className}`}>{children}</div>
  );
}

/** A section's title and lead: left-aligned, one idea each. */
export function SectionTitle({
  id,
  title,
  lead,
  className = "",
}: {
  id?: string;
  title: string;
  lead?: string;
  className?: string;
}) {
  return (
    <div className={`max-w-[720px] ${className}`}>
      <h2 id={id} className="text-headline font-semibold text-ink max-md:text-[1.875rem]">
        {title}
      </h2>
      {lead ? <p className="mt-4 text-lead text-ink-2">{lead}</p> : null}
    </div>
  );
}

const BUTTON =
  "inline-flex h-10 items-center justify-center gap-2 rounded-md px-4 text-[0.9375rem] font-medium transition-[background-color,color,box-shadow,scale] duration-150 ease-out active:scale-[0.97] [&_svg]:size-4";

export function ButtonLink({
  href,
  variant = "primary",
  children,
  className = "",
}: {
  href: string;
  variant?: "primary" | "secondary" | "ghost";
  children: React.ReactNode;
  className?: string;
}) {
  const tone =
    variant === "primary"
      ? "bg-accent text-on-accent hover:bg-accent-hover"
      : variant === "secondary"
        ? "bg-raised text-ink shadow-[0_0_0_1px_var(--line-strong)] hover:bg-hover"
        : "text-ink-2 hover:bg-hover hover:text-ink";
  const external = href.startsWith("http") || href.startsWith("mailto:");
  return external ? (
    <a href={href} className={`${BUTTON} ${tone} ${className}`}>
      {children}
    </a>
  ) : (
    <Link href={href} className={`${BUTTON} ${tone} ${className}`}>
      {children}
    </Link>
  );
}

/** Title and body pairs in a calm grid: the evidence under a claim. */
export function PointGrid({
  points,
  columns = 3,
}: {
  points: { title: string; body: string }[];
  columns?: 2 | 3;
}) {
  return (
    <ul className={`grid gap-x-10 gap-y-8 sm:grid-cols-2 ${columns === 3 ? "lg:grid-cols-3" : ""}`}>
      {points.map((point) => (
        <li key={point.title} className="flex flex-col gap-1.5 border-t border-line pt-5">
          <h3 className="text-[0.9375rem] font-semibold text-ink">{point.title}</h3>
          <p className="text-[0.9375rem] leading-relaxed text-ink-3">{point.body}</p>
        </li>
      ))}
    </ul>
  );
}

/** The opening of an inner page: what it is about, said in a quotable paragraph. */
export function PageHero({
  title,
  lead,
  children,
}: {
  title: string;
  lead: string;
  children?: React.ReactNode;
}) {
  return (
    <header className="border-b border-line bg-canvas">
      <Container className="py-16 md:py-24">
        <h1 className="max-w-[860px] text-display font-semibold text-ink max-md:text-[2.375rem]">
          {title}
        </h1>
        <p className="mt-6 max-w-[720px] text-lead text-ink-2">{lead}</p>
        {children ? <div className="mt-8 flex flex-wrap gap-3">{children}</div> : null}
      </Container>
    </header>
  );
}

/** The closing band of every page: one sentence and the demo button. */
export function CallToAction({
  title,
  lead,
  href,
  label,
}: {
  title: string;
  lead: string;
  href: string;
  label: string;
}) {
  return (
    <section className="border-t border-line bg-canvas py-20 md:py-24">
      <Container className="flex flex-col items-start gap-6">
        <SectionTitle title={title} lead={lead} />
        <ButtonLink href={href}>{label}</ButtonLink>
      </Container>
    </section>
  );
}

/** A heading for a block inside a page section. */
export function BlockTitle({ id, title, lead }: { id?: string; title: string; lead?: string }) {
  return (
    <div className="max-w-[640px]">
      <h3 id={id} className="text-title font-semibold text-ink">
        {title}
      </h3>
      {lead ? <p className="mt-2 text-[1.0625rem] leading-relaxed text-ink-2">{lead}</p> : null}
    </div>
  );
}
