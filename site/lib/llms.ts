import { dict, fieldTypeGroups } from "@/content";
import { absolute, type Locale, SITE } from "@/lib/site";

type Point = { title: string; body: string };

const points = (items: Point[]) => items.map((p) => `- **${p.title}**: ${p.body}`).join("\n");

/** llms.txt: what Repody is, and where each topic is explained (https://llmstxt.org). */
export function llmsIndex(): string {
  const en = dict("en");
  const fr = dict("fr");
  const link = (
    locale: Locale,
    page: Parameters<typeof absolute>[1],
    title: string,
    description: string
  ) => `- [${title}](${absolute(locale, page)}): ${description}`;
  return [
    `# ${SITE.name}`,
    "",
    `> ${en.home.meta.description}`,
    "",
    en.home.hero.lead,
    "",
    "## Pages (English)",
    "",
    link("en", "platform", en.platform.meta.title, en.platform.meta.description),
    link("en", "security", en.security.meta.title, en.security.meta.description),
    link("en", "architecture", en.architecture.meta.title, en.architecture.meta.description),
    link("en", "deployment", en.deployment.meta.title, en.deployment.meta.description),
    link("en", "engineering", en.engineering.meta.title, en.engineering.meta.description),
    link("en", "banks", en.solutions.banks.meta.title, en.solutions.banks.meta.description),
    link(
      "en",
      "insurance",
      en.solutions.insurance.meta.title,
      en.solutions.insurance.meta.description
    ),
    link("en", "telecom", en.solutions.telecom.meta.title, en.solutions.telecom.meta.description),
    link("en", "contact", en.contact.meta.title, en.contact.meta.description),
    "",
    "## Pages (français)",
    "",
    link("fr", "home", fr.home.meta.title, fr.home.meta.description),
    link("fr", "platform", fr.platform.meta.title, fr.platform.meta.description),
    link("fr", "security", fr.security.meta.title, fr.security.meta.description),
    link("fr", "deployment", fr.deployment.meta.title, fr.deployment.meta.description),
    "",
    "## Optional",
    "",
    `- [Full text of the site](${SITE.url}/llms-full.txt): every page in English, as Markdown`,
    "",
  ].join("\n");
}

/** llms-full.txt: the whole English site as one Markdown document. */
export function llmsFull(): string {
  const t = dict("en");
  const sections: string[] = [
    `# ${SITE.name}`,
    `> ${t.home.meta.description}`,
    t.home.hero.lead,
    t.home.hero.note,
    `## ${t.home.how.title}`,
    t.home.how.lead,
    points(t.home.how.steps),
    `## ${t.home.compare.title}`,
    t.home.compare.lead,
    t.home.compare.newPoints.map((p) => `- ${p}`).join("\n"),
    `# ${t.platform.hero.title}`,
    t.platform.hero.lead,
    ...t.platform.sections.flatMap((s) => [`## ${s.title}`, s.lead, points(s.points)]),
    `## ${t.platform.typesTitle}`,
    t.platform.listNote,
    ...fieldTypeGroups("en").map(
      (g) =>
        `### ${g.title}\n${g.types.map((ty) => `- \`${ty.value}\` ${ty.label}: ${ty.description}`).join("\n")}`
    ),
    `## ${t.platform.operatorsTitle}`,
    [...t.platform.operators, ...t.platform.compute]
      .map((o) => `- \`${o.symbol}\` ${o.label}`)
      .join("\n"),
    `# ${t.security.hero.title}`,
    t.security.hero.lead,
    t.security.posture,
    ...t.security.groups.flatMap((g) => [`## ${g.title}`, points(g.points)]),
    `# ${t.architecture.hero.title}`,
    t.architecture.hero.lead,
    `## ${t.architecture.flow.title}`,
    t.architecture.flow.steps.map((s, i) => `${i + 1}. **${s.title}**: ${s.body}`).join("\n"),
    ...t.architecture.groups.flatMap((g) => [`## ${g.title}`, points(g.points)]),
    `## ${t.architecture.decisions.title}`,
    t.architecture.decisions.items
      .map((d) => `- **ADR ${d.adr}, ${d.title}**: ${d.body}`)
      .join("\n"),
    `# ${t.deployment.hero.title}`,
    t.deployment.hero.lead,
    ...t.deployment.options.flatMap((o) => [
      `## ${o.title}`,
      o.body,
      o.points.map((p) => `- ${p}`).join("\n"),
    ]),
    `## ${t.deployment.brand.title}`,
    t.deployment.brand.lead,
    t.deployment.brand.vars.map((v) => `- \`${v.name}\`: ${v.body}`).join("\n"),
    t.deployment.brand.guarantee,
    `## ${t.deployment.box.title}`,
    t.deployment.box.items.map((i) => `- ${i}`).join("\n"),
    `# ${t.engineering.hero.title}`,
    t.engineering.hero.lead,
    ...t.engineering.stages.flatMap((s) => [
      `## ${s.title}`,
      s.lead,
      s.gates.map((g) => `- **${g.name}**: ${g.detail}`).join("\n"),
    ]),
    `## ${t.engineering.practices.title}`,
    points(t.engineering.practices.items),
    ...(["banks", "insurance", "telecom"] as const).flatMap((key) => {
      const s = t.solutions[key];
      return [
        `# ${s.hero.title}`,
        s.hero.lead,
        `${t.solutions.labels.docs}: ${s.docs.join(", ")}.`,
        points(s.cases),
        `${t.solutions.labels.rules}:\n${s.rules.map((r) => `- ${r}`).join("\n")}`,
        s.posture,
      ];
    }),
    `# ${t.home.faq.title}`,
    t.home.faq.items.map((f) => `**${f.q}**\n${f.a}`).join("\n\n"),
    `# ${t.contact.title}`,
    `${t.contact.lead} ${SITE.contactEmail}`,
  ];
  return `${sections.join("\n\n")}\n`;
}
