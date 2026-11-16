"use client";

import { useEffect, useRef, useState } from "react";
import type { Dict } from "@/content";
import { type Locale, SITE } from "@/lib/site";

const FIELD =
  "w-full rounded-md bg-field px-3 text-[0.9375rem] text-ink shadow-[inset_0_0_0_1px_var(--line-strong)] outline-none placeholder:text-ink-4 focus-visible:shadow-[inset_0_0_0_1px_var(--accent),0_0_0_3px_var(--accent-wash)] focus-visible:outline-none";
const TURNSTILE = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";

type Turnstile = {
  render: (element: HTMLElement, options: Record<string, unknown>) => string;
  reset: (id: string) => void;
  remove: (id: string) => void;
};
declare global {
  interface Window {
    turnstile?: Turnstile;
  }
}

type State = "idle" | "sending" | "sent" | "failed" | "tooMany" | "robot";
const FAILURES: Record<number, State> = { 429: "tooMany", 400: "robot" };

/** Loads Turnstile once and renders its widget; the token comes back through `onToken`. */
function useTurnstile(container: React.RefObject<HTMLDivElement | null>, locale: Locale) {
  const [token, setToken] = useState("");
  const widget = useRef<string | null>(null);
  useEffect(() => {
    const element = container.current;
    if (!element) return;
    const render = () => {
      if (!window.turnstile || widget.current) return;
      widget.current = window.turnstile.render(element, {
        sitekey: SITE.turnstileSiteKey,
        language: locale,
        callback: setToken,
        "expired-callback": () => setToken(""),
        "error-callback": () => setToken(""),
      });
    };
    let script = document.querySelector<HTMLScriptElement>(`script[src="${TURNSTILE}"]`);
    if (!script) {
      script = document.createElement("script");
      script.src = TURNSTILE;
      script.async = true;
      document.head.append(script);
    }
    if (window.turnstile) render();
    else script.addEventListener("load", render, { once: true });
    return () => {
      if (widget.current && window.turnstile) window.turnstile.remove(widget.current);
      widget.current = null;
    };
  }, [container, locale]);
  const reset = () => {
    setToken("");
    if (widget.current && window.turnstile) window.turnstile.reset(widget.current);
  };
  return { token, reset };
}

/** The access request: sent to Repody's API, which a platform admin approves in the app. */
export function ContactForm({
  t,
  locale,
}: Readonly<{ t: Dict["contact"]["form"]; locale: Locale }>) {
  const [state, setState] = useState<State>("idle");
  const box = useRef<HTMLDivElement>(null);
  const turnstile = useTurnstile(box, locale);

  if (state === "sent") {
    return <output className="block text-[0.9375rem] text-ink">{t.sent}</output>;
  }
  const problem = state === "failed" || state === "tooMany" || state === "robot";
  return (
    <form
      className="flex flex-col gap-5"
      onSubmit={async (event) => {
        event.preventDefault();
        if (!turnstile.token) {
          setState("robot");
          return;
        }
        const data = new FormData(event.currentTarget);
        setState("sending");
        try {
          const response = await fetch(SITE.accessRequestsUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              name: data.get("name"),
              email: data.get("email"),
              company: data.get("company"),
              sector: data.get("sector"),
              message: data.get("message") ?? "",
              locale,
              consent: data.get("consent") === "on",
              turnstileToken: turnstile.token,
            }),
          });
          if (response.ok) {
            setState("sent");
            return;
          }
          setState(FAILURES[response.status] ?? "failed");
        } catch {
          setState("failed");
        }
        turnstile.reset(); // a token is good for one request
      }}
    >
      <div className="grid gap-5 sm:grid-cols-2">
        <label className="flex flex-col gap-1.5 text-sm font-medium text-ink-2">
          {t.name}
          <input
            name="name"
            required
            maxLength={200}
            autoComplete="name"
            className={`${FIELD} h-10`}
          />
        </label>
        <label className="flex flex-col gap-1.5 text-sm font-medium text-ink-2">
          {t.email}
          <input
            name="email"
            type="email"
            required
            maxLength={254}
            autoComplete="email"
            className={`${FIELD} h-10`}
          />
        </label>
        <label className="flex flex-col gap-1.5 text-sm font-medium text-ink-2">
          {t.company}
          <input
            name="company"
            required
            maxLength={200}
            autoComplete="organization"
            className={`${FIELD} h-10`}
          />
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
          maxLength={4000}
          placeholder={t.placeholder}
          className={`${FIELD} resize-y py-2.5`}
        />
      </label>
      <label className="flex items-start gap-2.5 text-sm text-ink-2">
        <input name="consent" type="checkbox" required className="mt-0.5 size-4 accent-accent" />
        {t.consent}
      </label>
      <div ref={box} className="min-h-[65px]" />
      {problem ? (
        <p role="alert" className="text-sm text-fail-ink">
          {t[state]}{" "}
          {state !== "robot" ? (
            <a
              className="underline"
              href={`mailto:${SITE.contactEmail}?subject=${encodeURIComponent(t.subject)}`}
            >
              {SITE.contactEmail}
            </a>
          ) : null}
        </p>
      ) : null}
      <div className="flex flex-wrap items-center gap-4">
        <button
          type="submit"
          disabled={state === "sending"}
          className="inline-flex h-10 items-center rounded-md bg-accent px-5 text-[0.9375rem] font-medium text-on-accent transition-colors duration-100 hover:bg-accent-hover disabled:opacity-60"
        >
          {state === "sending" ? t.sending : t.submit}
        </button>
        <span className="text-sm text-ink-3">{t.note}</span>
      </div>
    </form>
  );
}
