import { Glyph } from "@/components/glyph";
import { JsonLd } from "@/components/json-ld";
import { SectionNav } from "@/components/section-nav";
import { CallToAction, Container, PageHero, SectionTitle } from "@/components/ui";
import { dict } from "@/content";
import { breadcrumb, pageMetadata } from "@/lib/meta";
import { href, type Locale } from "@/lib/site";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props) {
  const { locale } = await params;
  return pageMetadata(locale, "security", dict(locale).security.meta);
}

export default async function Security({ params }: Props) {
  const { locale } = await params;
  const t = dict(locale);
  const s = t.security;

  return (
    <>
      <JsonLd
        data={breadcrumb(locale, [
          { name: t.common.breadcrumbHome, page: "home" },
          { name: t.common.nav.security, page: "security" },
        ])}
      />
      <PageHero title={s.hero.title} lead={s.hero.lead} />

      {/* The four layers at a glance, each a door into its section. */}
      <section className="py-16 md:py-20">
        <Container className="flex flex-col gap-8">
          <ol className="grid gap-px overflow-hidden rounded-xl bg-line shadow-[0_0_0_1px_var(--line)] sm:grid-cols-2 lg:grid-cols-4">
            {s.groups.map((group, i) => (
              <li key={group.id} className="bg-panel">
                <a
                  href={`#${group.id}`}
                  className="flex h-full flex-col gap-3 p-5 transition-colors duration-150 hover:bg-hover"
                >
                  <span className="font-mono text-xs tabular-nums text-ink-4">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span className="text-[1.0625rem] font-semibold text-ink">{group.title}</span>
                  <span className="flex items-center gap-2 text-sm text-ink-3">
                    <Glyph status="passed" />
                    {group.points.length}
                  </span>
                </a>
              </li>
            ))}
          </ol>
          <p className="max-w-[820px] rounded-lg bg-canvas px-5 py-4 text-[0.9375rem] leading-relaxed text-ink-2 shadow-[0_0_0_1px_var(--line)]">
            {s.posture}
          </p>
        </Container>
      </section>

      <SectionNav
        label={t.common.onThisPage}
        items={s.groups.map(({ id, title }) => ({ id, title }))}
      />

      {s.groups.map((group, i) => (
        <section
          key={group.id}
          id={group.id}
          aria-labelledby={`${group.id}-title`}
          className={`scroll-mt-28 py-20 md:py-24 ${i % 2 ? "" : "border-y border-line bg-canvas"}`}
        >
          <Container className="grid gap-10 lg:grid-cols-[minmax(0,0.6fr)_minmax(0,1.4fr)]">
            <div className="lg:sticky lg:top-32 lg:self-start">
              <span className="font-mono text-xs tabular-nums text-ink-4">
                {String(i + 1).padStart(2, "0")}
              </span>
              <SectionTitle id={`${group.id}-title`} title={group.title} className="mt-2" />
            </div>
            <ul className="flex flex-col">
              {group.points.map((point) => (
                <li
                  key={point.title}
                  className="flex gap-4 border-t border-line py-5 first:border-t-0 first:pt-0"
                >
                  <Glyph status="passed" className="mt-1" />
                  <div>
                    <h3 className="text-[0.9375rem] font-semibold text-ink">{point.title}</h3>
                    <p className="mt-1 text-[0.9375rem] leading-relaxed text-ink-3">{point.body}</p>
                  </div>
                </li>
              ))}
            </ul>
          </Container>
        </section>
      ))}

      <CallToAction
        title={t.home.cta.title}
        lead={t.home.cta.lead}
        href={href(locale, "contact")}
        label={t.common.demo}
      />
    </>
  );
}
