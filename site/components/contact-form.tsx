"use client";

import type { Dict } from "@/content";
import { SITE } from "@/lib/site";

const FIELD =
  "w-full rounded-md bg-field px-3 text-[0.9375rem] text-ink shadow-[inset_0_0_0_1px_var(--line-strong)] outline-none placeholder:text-ink-4 focus-visible:shadow-[inset_0_0_0_1px_var(--accent),0_0_0_3px_var(--accent-wash)] focus-visible:outline-none";

/** A static site has no server: the form prepares the email in the reader's mail app. */
export function ContactForm({ t }: { t: Dict["contact"]["form"] }) {
  return (
    <form
      className="flex flex-col gap-5"
      onSubmit={(event) => {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        const body = [
          `${t.name}: ${data.get("name")}`,
          `${t.email}: ${data.get("email")}`,
          `${t.company}: ${data.get("company")}`,
          `${t.sector}: ${data.get("sector")}`,
          "",
          String(data.get("message") ?? ""),
        ].join("\n");
        window.location.href = `mailto:${SITE.contactEmail}?subject=${encodeURIComponent(t.subject)}&body=${encodeURIComponent(body)}`;
      }}
    >
      <div className="grid gap-5 sm:grid-cols-2">
        <label className="flex flex-col gap-1.5 text-sm font-medium text-ink-2">
          {t.name}
          <input name="name" required autoComplete="name" className={`${FIELD} h-10`} />
        </label>
        <label className="flex flex-col gap-1.5 text-sm font-medium text-ink-2">
          {t.email}
          <input
            name="email"
            type="email"
            required
            autoComplete="email"
            className={`${FIELD} h-10`}
          />
        </label>
        <label className="flex flex-col gap-1.5 text-sm font-medium text-ink-2">
          {t.company}
          <input name="company" required autoComplete="organization" className={`${FIELD} h-10`} />
        </label>
        <label className="flex flex-col gap-1.5 text-sm font-medium text-ink-2">
          {t.sector}
          <select name="sector" className={`${FIELD} h-10`}>
            {t.sectors.map((sector) => (
              <option key={sector}>{sector}</option>
            ))}
          </select>
        </label>
      </div>
      <label className="flex flex-col gap-1.5 text-sm font-medium text-ink-2">
        {t.message}
        <textarea
          name="message"
          rows={5}
          placeholder={t.placeholder}
          className={`${FIELD} resize-y py-2.5`}
        />
      </label>
      <div className="flex flex-wrap items-center gap-4">
        <button
          type="submit"
          className="inline-flex h-10 items-center rounded-md bg-accent px-5 text-[0.9375rem] font-medium text-on-accent transition-colors duration-100 hover:bg-accent-hover"
        >
          {t.submit}
        </button>
        <span className="text-sm text-ink-3">{t.note}</span>
      </div>
    </form>
  );
}
