import { ArchitectureDiagram } from "@/components/architecture-diagram";
import { JsonLd } from "@/components/json-ld";
import { RunFlow } from "@/components/run-flow";
import { SectionNav } from "@/components/section-nav";
import { CallToAction, Container, PageHero, PointGrid, SectionTitle } from "@/components/ui";
import { dict } from "@/content";
import { breadcrumb, pageMetadata } from "@/lib/meta";
import { href, type Locale } from "@/lib/site";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props) {
  const { locale } = await params;
  return pageMetadata(locale, "architecture", dict(locale).architecture.meta);
}

export default async function Architecture({ params }: Props) {
  const { locale } = await params;
  const t = dict(locale);
  const a = t.architecture;

  return (
    <>
      <JsonLd
        data={breadcrumb(locale, [
          { name: t.common.breadcrumbHome, page: "home" },
          { name: t.common.nav.architecture, page: "architecture" },
        ])}
      />
      <PageHero title={a.hero.title} lead={a.hero.lead} />

      <section className="py-16 md:py-20">
        <Container>
          <ArchitectureDiagram t={a.diagram} className="reveal" />
        </Container>
      </section>

      <section className="border-y border-line bg-canvas py-20 md:py-24">
        <Container className="grid gap-12 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
          <div className="lg:sticky lg:top-24 lg:self-start">
            <SectionTitle title={a.flow.title} lead={a.flow.lead} />
          </div>
          <RunFlow steps={a.flow.steps} />
        </Container>
      </section>

      <SectionNav
        label={t.common.onThisPage}
        items={a.groups.map(({ id, title }) => ({ id, title }))}
      />

      {a.groups.map((group, i) => (
        <section
          key={group.id}
          id={group.id}
          aria-labelledby={`${group.id}-title`}
          className={`scroll-mt-28 py-20 md:py-24 ${i % 2 ? "border-y border-line bg-canvas" : ""}`}
        >
          <Container className="flex flex-col gap-10">
            <SectionTitle id={`${group.id}-title`} title={group.title} />
            <PointGrid points={group.points} />
          </Container>
        </section>
      ))}

      <section className="border-t border-line py-20 md:py-24">
        <Container className="flex flex-col gap-10">
          <SectionTitle title={a.decisions.title} lead={a.decisions.lead} />
          <ol className="flex flex-col">
            {a.decisions.items.map((item) => (
              <li
                key={item.title}
                className="grid gap-1 border-t border-line py-4 sm:grid-cols-[4rem_minmax(0,1fr)_minmax(0,1.4fr)] sm:gap-6"
              >
                <span className="font-mono text-xs leading-6 tabular-nums text-ink-4">
                  ADR {item.adr}
                </span>
                <span className="text-[0.9375rem] font-semibold text-ink">{item.title}</span>
                <span className="text-[0.9375rem] text-ink-3">{item.body}</span>
              </li>
            ))}
          </ol>
        </Container>
      </section>

      <CallToAction
        title={t.home.cta.title}
        lead={t.home.cta.lead}
        href={href(locale, "contact")}
        label={t.common.demo}
      />
    </>
  );
}
