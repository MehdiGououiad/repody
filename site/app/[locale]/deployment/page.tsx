import { BrandSwitcher } from "@/components/brand-switcher";
import { Glyph } from "@/components/glyph";
import { HowSteps } from "@/components/how-steps";
import { JsonLd } from "@/components/json-ld";
import { CallToAction, Container, PageHero, SectionTitle } from "@/components/ui";
import { dict } from "@/content";
import { breadcrumb, pageMetadata } from "@/lib/meta";
import { href, type Locale } from "@/lib/site";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props) {
  const { locale } = await params;
  return pageMetadata(locale, "deployment", dict(locale).deployment.meta);
}

export default async function Deployment({ params }: Props) {
  const { locale } = await params;
  const t = dict(locale);
  const d = t.deployment;

  return (
    <>
      <JsonLd
        data={breadcrumb(locale, [
          { name: t.common.breadcrumbHome, page: "home" },
          { name: t.common.nav.deployment, page: "deployment" },
        ])}
      />
      <PageHero title={d.hero.title} lead={d.hero.lead} />

      <section className="py-16 md:py-20">
        <Container>
          <div className="grid gap-4 md:grid-cols-3">
            {d.options.map((option) => (
              <article
                key={option.id}
                id={option.id}
                className="flex scroll-mt-24 flex-col gap-5 rounded-xl bg-panel p-6 shadow-[0_0_0_1px_var(--line)]"
              >
                <div>
                  <h2 className="text-title font-semibold text-ink">{option.title}</h2>
                  <p className="mt-1.5 text-[0.9375rem] text-ink-3">{option.body}</p>
                </div>
                <ul className="flex flex-col gap-3 border-t border-line pt-5">
                  {option.points.map((point) => (
                    <li
                      key={point}
                      className="flex gap-3 text-[0.9375rem] leading-relaxed text-ink-2"
                    >
                      <Glyph status="passed" className="mt-1" />
                      {point}
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </Container>
      </section>

      <section id="brand" className="scroll-mt-20 border-y border-line bg-canvas py-20 md:py-24">
        <Container className="flex flex-col gap-12">
          <SectionTitle title={d.brand.title} lead={d.brand.lead} />
          <BrandSwitcher t={t.home.brand} />
          <dl className="grid gap-px overflow-hidden rounded-xl bg-line shadow-[0_0_0_1px_var(--line)] md:grid-cols-2">
            {d.brand.vars.map((v) => (
              <div key={v.name} className="flex flex-col gap-1 bg-panel px-5 py-4">
                <dt className="font-mono text-[0.8125rem] text-accent-ink">{v.name}</dt>
                <dd className="text-[0.9375rem] text-ink-2">{v.body}</dd>
              </div>
            ))}
          </dl>
          <p className="max-w-[760px] text-[0.9375rem] leading-relaxed text-ink-3">
            {d.brand.guarantee}
          </p>
        </Container>
      </section>

      <section className="py-20 md:py-24">
        <Container className="flex flex-col gap-14">
          <SectionTitle title={d.steps.title} />
          <HowSteps steps={d.steps.items} />
        </Container>
      </section>

      <section className="border-t border-line bg-canvas py-20 md:py-24">
        <Container className="grid gap-10 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
          <SectionTitle title={d.box.title} />
          <ul className="grid gap-x-8 sm:grid-cols-2">
            {d.box.items.map((item) => (
              <li
                key={item}
                className="flex gap-3 border-t border-line py-4 text-[0.9375rem] text-ink-2"
              >
                <Glyph status="passed" className="mt-1" />
                {item}
              </li>
            ))}
          </ul>
        </Container>
      </section>

      <CallToAction
        playground={t.common.playground}
        title={t.home.cta.title}
        lead={t.home.cta.lead}
        href={href(locale, "contact")}
        label={t.common.demo}
      />
    </>
  );
}
