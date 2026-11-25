import Link from "next/link";
import type { Dict } from "@/content";
import { href, type Locale, type PageKey, SITE } from "@/lib/site";
import { Logo } from "./site-header";
import { Container } from "./ui";

/** The year the static site was built. */
const YEAR = new Date().getFullYear();

export function SiteFooter({ locale, t }: { locale: Locale; t: Dict["common"] }) {
  const columns: { title: string; links: { key: PageKey; label: string }[] }[] = [
    {
      title: t.footer.product,
      links: (["platform", "security", "architecture", "deployment", "engineering"] as const).map(
        (key) => ({
          key,
          label: t.nav[key],
        }),
      ),
    },
    {
      title: t.nav.solutions,
      links: (["banks", "insurance", "telecom"] as const).map((key) => ({
        key,
        label: t.nav[key],
      })),
    },
    {
      title: t.footer.company,
      links: [
        { key: "contact", label: t.footer.contact },
        { key: "legal", label: t.footer.legal },
        { key: "privacy", label: t.footer.privacy },
      ],
    },
  ];
  return (
    <footer className="border-t border-line bg-canvas">
      <Container className="grid gap-10 py-14 md:grid-cols-[1.4fr_repeat(3,1fr)]">
        <div className="flex max-w-xs flex-col gap-4">
          <Logo locale={locale} />
          <p className="text-sm text-ink-3">{t.footer.tagline}</p>
          <a
            href={`mailto:${SITE.contactEmail}`}
            className="text-sm text-accent-ink hover:underline"
          >
            {SITE.contactEmail}
          </a>
        </div>
        {columns.map((column) => (
          <div key={column.title}>
            <h2 className="text-sm font-semibold text-ink">{column.title}</h2>
            <ul className="mt-3 flex flex-col gap-2">
              {column.links.map((link) => (
                <li key={link.key}>
                  <Link href={href(locale, link.key)} className="text-sm text-ink-3 hover:text-ink">
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </Container>
      <Container className="flex flex-wrap justify-between gap-2 border-t border-line py-6 text-xs text-ink-4">
        <span>
          © {YEAR} Repody. {t.footer.rights}
        </span>
        <span>{t.footer.madeIn}</span>
      </Container>
    </footer>
  );
}
