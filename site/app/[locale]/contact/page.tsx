import { ContactForm } from "@/components/contact-form";
import { JsonLd } from "@/components/json-ld";
import { Container } from "@/components/ui";
import { dict } from "@/content";
import { breadcrumb, pageMetadata } from "@/lib/meta";
import { type Locale, SITE } from "@/lib/site";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props) {
  const { locale } = await params;
  return pageMetadata(locale, "contact", dict(locale).contact.meta);
}

export default async function Contact({ params }: Props) {
  const { locale } = await params;
  const t = dict(locale);
  const c = t.contact;

  return (
    <section className="py-16 md:py-24">
      <JsonLd
        data={breadcrumb(locale, [
          { name: t.common.breadcrumbHome, page: "home" },
          { name: c.meta.title, page: "contact" },
        ])}
      />
      <Container className="grid gap-14 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
        <div className="flex flex-col gap-10">
          <div>
            <h1 className="text-display font-semibold text-ink max-md:text-[2.375rem]">
              {c.title}
            </h1>
            <p className="mt-6 max-w-[520px] text-lead text-ink-2">{c.lead}</p>
          </div>
          <div>
            <h2 className="text-sm font-semibold text-ink-3">{c.next.title}</h2>
            <ol className="mt-4 flex flex-col">
              {c.next.items.map((item, i) => (
                <li
                  key={item}
                  className="flex gap-4 border-t border-line py-3.5 text-[0.9375rem] text-ink-2"
                >
                  <span className="font-mono text-xs leading-6 tabular-nums text-ink-4">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  {item}
                </li>
              ))}
            </ol>
          </div>
          <p className="text-[0.9375rem] text-ink-3">
            {c.direct}{" "}
            <a className="text-accent-ink hover:underline" href={`mailto:${SITE.contactEmail}`}>
              {SITE.contactEmail}
            </a>
          </p>
        </div>
        <div className="rounded-xl bg-panel p-6 shadow-[0_0_0_1px_var(--line)] md:p-8 lg:self-start">
          <ContactForm t={c.form} />
        </div>
      </Container>
    </section>
  );
}
