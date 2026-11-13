import { ApiExample } from "@/components/api-example";
import { FieldTypes } from "@/components/field-types";
import { JsonLd } from "@/components/json-ld";
import { Screenshot } from "@/components/screenshot";
import { SectionNav } from "@/components/section-nav";
import {
  BlockTitle,
  ButtonLink,
  CallToAction,
  Container,
  PageHero,
  PointGrid,
  SectionTitle,
} from "@/components/ui";
import { dict } from "@/content";
import { breadcrumb, pageMetadata } from "@/lib/meta";
import { href, type Locale } from "@/lib/site";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props) {
  const { locale } = await params;
  return pageMetadata(locale, "platform", dict(locale).platform.meta);
}

function Symbols({ items }: { items: { symbol: string; label: string }[] }) {
  return (
    <ul className="grid gap-px overflow-hidden rounded-xl bg-line shadow-[0_0_0_1px_var(--line)] sm:grid-cols-2">
      {items.map((item) => (
        <li key={item.symbol} className="flex items-center gap-4 bg-panel px-4 py-3">
          <code className="min-w-[7.5rem] font-mono text-sm text-accent-ink">{item.symbol}</code>
          <span className="text-[0.9375rem] text-ink-2">{item.label}</span>
        </li>
      ))}
    </ul>
  );
}

export default async function Platform({ params }: Props) {
  const { locale } = await params;
  const t = dict(locale);
  const p = t.platform;

  return (
    <>
      <JsonLd
        data={breadcrumb(locale, [
          { name: t.common.breadcrumbHome, page: "home" },
          { name: t.common.nav.platform, page: "platform" },
        ])}
      />
      <PageHero title={p.hero.title} lead={p.hero.lead}>
        <ButtonLink href={href(locale, "contact")}>{t.common.demo}</ButtonLink>
      </PageHero>
      <SectionNav
        label={t.common.onThisPage}
        items={p.sections.map(({ id, title }) => ({ id, title }))}
      />

      {p.sections.map((section, i) => (
        <section
          key={section.id}
          id={section.id}
          aria-labelledby={`${section.id}-title`}
          className={`scroll-mt-28 py-20 md:py-24 ${i % 2 ? "border-y border-line bg-canvas" : ""}`}
        >
          <Container className="flex flex-col gap-12">
            <SectionTitle id={`${section.id}-title`} title={section.title} lead={section.lead} />
            {section.shot ? (
              <Screenshot
                name={section.shot}
                locale={locale}
                alt={section.title}
                className="reveal"
              />
            ) : null}
            {section.id === "api" ? <ApiExample t={p.apiExample} /> : null}
            <PointGrid points={section.points} />

            {section.id === "builder" ? (
              <div className="flex flex-col gap-8 border-t border-line pt-12">
                <BlockTitle id="types" title={p.typesTitle} lead={p.listNote} />
                <FieldTypes locale={locale} />
              </div>
            ) : null}

            {section.id === "rules" ? (
              <div className="flex flex-col gap-8 border-t border-line pt-12">
                <BlockTitle id="operators" title={p.operatorsTitle} lead={p.operatorsLead} />
                <Symbols items={p.operators} />
                <h4 className="text-[0.9375rem] font-semibold text-ink">{p.computeTitle}</h4>
                <Symbols items={p.compute} />
              </div>
            ) : null}
          </Container>
        </section>
      ))}

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
