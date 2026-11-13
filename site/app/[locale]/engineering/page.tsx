import { GatePipeline } from "@/components/gate-pipeline";
import { JsonLd } from "@/components/json-ld";
import { SectionNav } from "@/components/section-nav";
import { CallToAction, Container, PageHero, PointGrid, SectionTitle } from "@/components/ui";
import { dict } from "@/content";
import { breadcrumb, pageMetadata } from "@/lib/meta";
import { href, type Locale } from "@/lib/site";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props) {
  const { locale } = await params;
  return pageMetadata(locale, "engineering", dict(locale).engineering.meta);
}

export default async function Engineering({ params }: Props) {
  const { locale } = await params;
  const t = dict(locale);
  const e = t.engineering;

  return (
    <>
      <JsonLd
        data={breadcrumb(locale, [
          { name: t.common.breadcrumbHome, page: "home" },
          { name: t.common.nav.engineering, page: "engineering" },
        ])}
      />
      <PageHero title={e.hero.title} lead={e.hero.lead} />

      {/* The whole path of a change, stage by stage, before the detail. */}
      <section className="py-16 md:py-20">
        <Container>
          <GatePipeline gates={e.stages.map((stage) => stage.title)} />
        </Container>
      </section>

      <SectionNav
        label={t.common.onThisPage}
        items={e.stages.map(({ id, title }) => ({ id, title }))}
      />

      {e.stages.map((stage, i) => (
        <section
          key={stage.id}
          id={stage.id}
          aria-labelledby={`${stage.id}-title`}
          className={`scroll-mt-28 py-20 md:py-24 ${i % 2 ? "" : "border-y border-line bg-canvas"}`}
        >
          <Container className="grid gap-10 lg:grid-cols-[minmax(0,0.7fr)_minmax(0,1.3fr)]">
            <div className="lg:sticky lg:top-32 lg:self-start">
              <span className="font-mono text-xs tabular-nums text-ink-4">
                {String(i + 1).padStart(2, "0")}
              </span>
              <SectionTitle
                id={`${stage.id}-title`}
                title={stage.title}
                lead={stage.lead}
                className="mt-2"
              />
            </div>
            <ol className="flex flex-col">
              {stage.gates.map((gate, n) => (
                <li
                  key={gate.name}
                  className="grid grid-cols-[2rem_minmax(0,1fr)] gap-x-3 border-t border-line py-4 first:border-t-0 first:pt-0 sm:grid-cols-[2rem_12rem_minmax(0,1fr)]"
                >
                  <span className="font-mono text-xs leading-6 tabular-nums text-ink-4">
                    {String(n + 1).padStart(2, "0")}
                  </span>
                  <span className="text-[0.9375rem] font-semibold text-ink">{gate.name}</span>
                  <span className="col-start-2 text-[0.9375rem] text-ink-3 sm:col-start-3">
                    {gate.detail}
                  </span>
                </li>
              ))}
            </ol>
          </Container>
        </section>
      ))}

      <section className="py-20 md:py-24">
        <Container className="flex flex-col gap-10">
          <SectionTitle title={e.practices.title} />
          <PointGrid points={e.practices.items} />
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
