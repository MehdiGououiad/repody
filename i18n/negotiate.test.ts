import { describe, expect, it } from "bun:test";
import { negotiateLocale, validTimeZone } from "./negotiate";

describe("locale negotiation", () => {
  it("picks the best supported language", () => {
    expect(negotiateLocale("fr-FR,fr;q=0.9,en;q=0.8")).toBe("fr");
    expect(negotiateLocale("de-DE,en-GB;q=0.5")).toBe("en");
  });

  it("falls back to the default without a usable header", () => {
    expect(negotiateLocale(null)).toBe("en");
    expect(negotiateLocale("*")).toBe("en");
    expect(negotiateLocale("not a language tag!!")).toBe("en");
  });
});

describe("time zones", () => {
  it("keep known zones and replace the rest with UTC", () => {
    expect(validTimeZone("Europe/Paris")).toBe("Europe/Paris");
    expect(validTimeZone("Mars/Olympus")).toBe("UTC");
    expect(validTimeZone(undefined)).toBe("UTC");
  });
});
