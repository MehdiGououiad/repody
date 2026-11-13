import { Glyph } from "@/components/glyph";
import { JsonLd } from "@/components/json-ld";
import { Screenshot } from "@/components/screenshot";
import {
  ButtonLink,
  CallToAction,
  Container,
  PageHero,
  PointGrid,
  SectionTitle,
} from "@/components/ui";
import { dict } from "@/content";
import { breadcrumb, pageMetadata } from "@/lib/meta";
import { href, LOCALES, type Locale } from "@/lib/site";

const SECTORS = ["banks", "insurance", "telecom"] as const;
type Sector = (typeof SECTORS)[number];
type Props = { params: Promise<{ locale: Locale; sector: Sector }> };

export const dynamicParams = false;

export function generateStaticParams() {
  return LOCALES.flatMap((locale) => SECTORS.map((sector) => ({ locale, sector })));
}

export async function generateMetadata({ params }: Props) {
  const { locale, sector } = await params;
  return pageMetadata(locale, sector, dict(locale).solutions[sector].meta);
}

export default async function Solution({ params }: Props) {
  const { locale, sector } = await params;
  const t = dict(locale);
  const s = t.solutions[sector];
  const labels = t.solutions.labels;

  return (
    <>
      <JsonLd
        data={breadcrumb(locale, [
          { name: t.common.breadcrumbHome, page: "home" },
          { name: t.common.nav[sector], page: sector },
        ])}
      />
      <PageHero title={s.hero.title} lead={s.hero.lead}>
        <ButtonLink href={href(locale, "contact")}>{t.common.demo}</ButtonLink>
        <ButtonLink href={href(locale, "platform")} variant="secondary">
          {t.common.seePlatform}
        </ButtonLink>
      </PageHero>

      <section className="py-16 md:py-20">
        <Container className="flex flex-col gap-5">
          <h2 className="text-sm font-semibold text-ink-3">{labels.docs}</h2>
          <ul className="flex flex-wrap gap-2">
            {s.docs.map((doc) => (
              <li
                key={doc}
                className="rounded-md bg-panel px-3 py-1.5 text-[0.9375rem] text-ink-2 shadow-[0_0_0_1px_var(--line)]"
              >
                {doc}
              </li>
            ))}
          </ul>
        </Container>
      </section>

      <section className="border-y border-line bg-canvas py-20 md:py-24">
        <Container className="flex flex-col gap-10">
          <SectionTitle title={labels.cases} />
          <PointGrid points={s.cases} />
        </Container>
      </section>

      <section className="py-20 md:py-24">
        <Container className="grid gap-12 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)] lg:items-center">
          <div className="flex flex-col gap-8">
            <SectionTitle title={labels.rules} />
            <ul className="flex flex-col gap-px overflow-hidden rounded-xl bg-line shadow-[0_0_0_1px_var(--line)]">
              {s.rules.map((rule) => (
                <li
                  key={rule}
                  className="flex items-center gap-3 bg-panel px-4 py-3 text-[0.9375rem] text-ink"
                >
                  <Glyph status="passed" />
                  {rule}
                </li>
              ))}
            </ul>
          </div>
          <Screenshot name="builder-rules" locale={locale} alt={labels.rules} className="reveal" />
        </Container>
      </section>

      <section className="border-t border-line bg-canvas py-16 md:py-20">
        <Container className="flex flex-col gap-3">
          <h2 className="text-sm font-semibold text-ink-3">{labels.posture}</h2>
          <p className="max-w-[760px] text-title font-medium text-ink">{s.posture}</p>
          <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-[0.9375rem]">
            <a className="text-accent-ink hover:underline" href={href(locale, "security")}>
              {t.common.nav.security}
            </a>
            <a className="text-accent-ink hover:underline" href={href(locale, "deployment")}>
              {t.common.nav.deployment}
            </a>
          </div>
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
