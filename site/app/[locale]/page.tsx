import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { BrandSwitcher } from "@/components/brand-switcher";
import { Faq } from "@/components/faq";
import { GatePipeline } from "@/components/gate-pipeline";
import { Glyph } from "@/components/glyph";
import { HowSteps } from "@/components/how-steps";
import { JsonLd } from "@/components/json-ld";
import { RunReplay } from "@/components/run-replay";
import { Screenshot } from "@/components/screenshot";
import { ButtonLink, CallToAction, Container, SectionTitle } from "@/components/ui";
import { VideoFrame } from "@/components/video-frame";
import { dict } from "@/content";
import { pageMetadata } from "@/lib/meta";
import { href, type Locale, type PageKey, SITE } from "@/lib/site";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props) {
  const { locale } = await params;
  return pageMetadata(locale, "home", dict(locale).home.meta);
}

function MoreLink({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <Link
      href={to}
      className="group inline-flex items-center gap-1.5 text-[0.9375rem] font-medium text-accent-ink"
    >
      {children}
      <ArrowRight
        className="size-4 transition-transform duration-150 group-hover:translate-x-0.5"
        aria-hidden
      />
    </Link>
  );
}

export default async function Home({ params }: Props) {
  const { locale } = await params;
  const t = dict(locale);
  const h = t.home;

  return (
    <>
      <JsonLd
        data={[
          {
            "@context": "https://schema.org",
            "@type": "SoftwareApplication",
            name: "Repody",
            applicationCategory: "BusinessApplication",
            operatingSystem: "Linux, Kubernetes, OpenShift",
            description: h.meta.description,
            url: `${SITE.url}/${locale}/`,
            inLanguage: ["fr", "en"],
            featureList: [
              ...h.security.items.map((i) => i.title),
              ...h.deploy.options.map((o) => o.title),
              ...h.how.steps.map((s) => s.title),
            ],
            offers: { "@type": "Offer", description: h.hero.note },
          },
          {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            mainEntity: h.faq.items.map((item) => ({
              "@type": "Question",
              name: item.q,
              acceptedAnswer: { "@type": "Answer", text: item.a },
            })),
          },
        ]}
      />

      {/* Hero */}
      <section className="border-b border-line bg-canvas bg-ruled">
        <Container className="grid gap-12 py-16 md:py-24 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)] lg:items-center">
          <div>
            <h1 className="text-display font-semibold text-ink max-md:text-[2.5rem]">
              {h.hero.title}
            </h1>
            <p className="mt-6 max-w-[560px] text-lead text-ink-2">{h.hero.lead}</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <ButtonLink href={href(locale, "contact")}>{t.common.demo} →</ButtonLink>
              <ButtonLink href={SITE.playgroundUrl} variant="secondary">
                {t.common.playground} →
              </ButtonLink>
            </div>
            <p className="mt-6 text-sm text-ink-3">{h.hero.note}</p>
          </div>
          <RunReplay t={h.replay} />
        </Container>
      </section>

      {/* Proof */}
      <section aria-label="Repody">
        <Container>
          <dl className="grid grid-cols-2 border-b border-line lg:grid-cols-4">
            {h.proof.map((item) => (
              <div
                key={item.label}
                className="flex flex-col gap-1 border-line py-8 pe-6 max-lg:even:ps-6 max-lg:even:border-s lg:border-s lg:ps-6 lg:first:border-s-0 lg:first:ps-0"
              >
                <dt className="order-2 text-sm text-ink-3">{item.label}</dt>
                <dd className="order-1 font-mono text-[2.5rem] font-medium leading-none tracking-[-0.03em] tabular-nums text-ink">
                  {item.value}
                </dd>
              </div>
            ))}
          </dl>
        </Container>
      </section>

      {/* How it works */}
      <section className="py-20 md:py-28">
        <Container className="flex flex-col gap-14">
          <SectionTitle index={1} title={h.how.title} lead={h.how.lead} />
          <HowSteps steps={h.how.steps} />
        </Container>
      </section>

      {/* Video */}
      <section className="pb-20 md:pb-28">
        <Container className="flex flex-col gap-8">
          <SectionTitle index={2} title={h.video.title} />
          <VideoFrame locale={locale} t={h.video} />
        </Container>
      </section>

      {/* One pass instead of three */}
      <section className="border-y border-line bg-canvas py-20 md:py-28">
        <Container className="flex flex-col gap-12">
          <SectionTitle index={3} title={h.compare.title} lead={h.compare.lead} />
          <div className="grid gap-6 md:grid-cols-2">
            {[
              {
                title: h.compare.oldTitle,
                steps: h.compare.oldSteps,
                points: h.compare.oldPoints,
                good: false,
              },
              {
                title: h.compare.newTitle,
                steps: h.compare.newSteps,
                points: h.compare.newPoints,
                good: true,
              },
            ].map((col) => (
              <div
                key={col.title}
                className={`flex flex-col gap-6 rounded-xl p-6 md:p-8 ${col.good ? "bg-panel shadow-[0_0_0_1px_var(--accent)]" : "bg-panel shadow-[0_0_0_1px_var(--line)]"}`}
              >
                <h3 className="text-title font-semibold text-ink">{col.title}</h3>
                <ol className="flex flex-wrap items-center gap-2 text-sm">
                  {col.steps.map((step, i) => (
                    <li key={step} className="flex items-center gap-2">
                      <span
                        className={`rounded-md px-2.5 py-1 ${col.good ? "bg-accent-wash text-accent-ink" : "bg-selected text-ink-2"}`}
                      >
                        {step}
                      </span>
                      {i < col.steps.length - 1 ? (
                        <span className="text-ink-4" aria-hidden>
                          →
                        </span>
                      ) : null}
                    </li>
                  ))}
                </ol>
                <ul className="flex flex-col gap-3">
                  {col.points.map((point) => (
                    <li key={point} className="flex gap-3 text-[0.9375rem] text-ink-2">
                      <Glyph status={col.good ? "passed" : "failed"} className="mt-1" />
                      {point}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </Container>
      </section>

      {/* Platform tour */}
      <section className="py-20 md:py-28">
        <Container className="flex flex-col gap-16">
          <SectionTitle index={4} title={h.tour.title} lead={h.tour.lead} />
          {h.tour.items.map((item, i) => (
            <div
              key={item.title}
              className="grid gap-8 lg:grid-cols-[minmax(0,0.75fr)_minmax(0,1.25fr)] lg:items-center"
            >
              <div className={`flex flex-col gap-4 ${i % 2 ? "lg:order-2" : ""}`}>
                <h3 className="text-title font-semibold text-ink">{item.title}</h3>
                <p className="text-[1.0625rem] leading-relaxed text-ink-2">{item.body}</p>
                <MoreLink to={href(locale, item.page as PageKey, item.hash)}>
                  {t.common.learnMore}
                </MoreLink>
              </div>
              <Screenshot name={item.shot} locale={locale} alt={item.title} className="reveal" />
            </div>
          ))}
        </Container>
      </section>

      {/* White label */}
      <section className="border-y border-line bg-canvas py-20 md:py-28">
        <Container className="flex flex-col gap-12">
          <SectionTitle index={5} title={h.brand.title} lead={h.brand.lead} />
          <BrandSwitcher t={h.brand} />
        </Container>
      </section>

      {/* Security */}
      <section className="py-20 md:py-28">
        <Container className="flex flex-col gap-12">
          <SectionTitle index={6} title={h.security.title} lead={h.security.lead} />
          <ul className="grid gap-x-10 gap-y-8 sm:grid-cols-2 lg:grid-cols-3">
            {h.security.items.map((item) => (
              <li key={item.title} className="flex gap-3 border-t border-line pt-5">
                <Glyph status="passed" className="mt-1" />
                <div>
                  <h3 className="text-[0.9375rem] font-semibold text-ink">{item.title}</h3>
                  <p className="mt-1.5 text-[0.9375rem] leading-relaxed text-ink-3">{item.body}</p>
                </div>
              </li>
            ))}
          </ul>
          <MoreLink to={href(locale, "security")}>{t.common.nav.security}</MoreLink>
        </Container>
      </section>

      {/* Deployment */}
      <section className="border-y border-line bg-canvas py-20 md:py-28">
        <Container className="flex flex-col gap-12">
          <SectionTitle index={7} title={h.deploy.title} lead={h.deploy.lead} />
          <div className="grid gap-4 md:grid-cols-3">
            {h.deploy.options.map((option) => (
              <div
                key={option.title}
                className="flex flex-col gap-2 rounded-xl bg-panel p-6 shadow-[0_0_0_1px_var(--line)]"
              >
                <h3 className="text-[1.0625rem] font-semibold text-ink">{option.title}</h3>
                <p className="text-[0.9375rem] leading-relaxed text-ink-3">{option.body}</p>
              </div>
            ))}
          </div>
          <MoreLink to={href(locale, "deployment")}>{t.common.nav.deployment}</MoreLink>
        </Container>
      </section>

      {/* Engineering */}
      <section className="py-20 md:py-28">
        <Container className="flex flex-col gap-12">
          <SectionTitle index={8} title={h.engineering.title} lead={h.engineering.lead} />
          <GatePipeline gates={h.engineering.gates} />
          <MoreLink to={href(locale, "engineering")}>{t.common.nav.engineering}</MoreLink>
        </Container>
      </section>

      {/* Industries */}
      <section className="border-y border-line bg-canvas py-20 md:py-28">
        <Container className="flex flex-col gap-12">
          <SectionTitle index={9} title={h.industries.title} />
          <div className="grid gap-4 md:grid-cols-3">
            {h.industries.items.map((item) => (
              <Link
                key={item.title}
                href={href(locale, item.page as PageKey)}
                className="group flex flex-col gap-4 rounded-xl bg-panel p-6 shadow-[0_0_0_1px_var(--line)] transition-shadow duration-150 hover:shadow-[0_0_0_1px_var(--line-strong)]"
              >
                <div>
                  <h3 className="flex items-center justify-between text-[1.0625rem] font-semibold text-ink">
                    {item.title}
                    <ArrowRight
                      className="size-4 text-ink-4 transition-transform duration-150 group-hover:translate-x-0.5"
                      aria-hidden
                    />
                  </h3>
                  <p className="mt-1 text-[0.9375rem] text-ink-3">{item.body}</p>
                </div>
                <ul className="flex flex-wrap gap-1.5">
                  {item.docs.map((doc) => (
                    <li key={doc} className="rounded-md bg-selected px-2 py-1 text-xs text-ink-2">
                      {doc}
                    </li>
                  ))}
                </ul>
              </Link>
            ))}
          </div>
        </Container>
      </section>

      {/* FAQ */}
      <section className="py-20 md:py-28">
        <Container className="flex flex-col gap-10">
          <SectionTitle index={10} title={h.faq.title} />
          <Faq items={h.faq.items} />
        </Container>
      </section>

      {/* Call */}
      <CallToAction
        playground={t.common.playground}
        title={h.cta.title}
        lead={h.cta.lead}
        href={href(locale, "contact")}
        label={t.common.demo}
      />
    </>
  );
}
