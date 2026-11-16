import { getTranslations } from "next-intl/server";
import { Section } from "@/components/layout/page";
import { Rows } from "@/components/settings/platform-overview";
import { StatusGlyph } from "@/components/ui/status-glyph";
import type { Access, Permission } from "@/lib/types";

const PERMISSIONS: Permission[] = [
  "workflow:read",
  "workflow:write",
  "workflow:deploy",
  "workflow:delete",
  "run:read",
  "run:execute",
  "metrics:read",
  "credits:grant",
];

const ROLES = ["viewer", "operator", "admin", "platform_admin", "demo_visitor"] as const;
const isRole = (role: string): role is (typeof ROLES)[number] =>
  (ROLES as readonly string[]).includes(role);

export async function AccessOverview({ access }: { access: Access }) {
  const t = await getTranslations("settings.access");
  const roles = access.roles.map((role) => (isRole(role) ? t(`roles.${role}`) : role));
  const state = (permission: Permission) =>
    access.permissions.includes(permission)
      ? ({ glyph: "passed", label: t("allowed") } as const)
      : access.withCredits.includes(permission)
        ? ({ glyph: "warning", label: t("withCredits") } as const)
        : ({ glyph: "failed", label: t("notAllowed") } as const);

  return (
    <Section title={t("title")} hint={t("hint")}>
      <Rows
        rows={[
          [t("role"), roles.join(", ") || t("noRole")],
          ...(access.credits?.account
            ? ([
                [t("account"), access.credits.account],
                [t("credits"), t("creditsLeft", { balance: access.credits.balance })],
              ] as [string, React.ReactNode][])
            : []),
          ...PERMISSIONS.map((permission): [string, React.ReactNode] => {
            const { glyph, label } = state(permission);
            return [
              t(`permissions.${permission}`),
              <span key={permission} className="inline-flex items-center gap-1.5 text-ink-2">
                <StatusGlyph status={glyph} className="size-3.5" />
                {label}
              </span>,
            ];
          }),
        ]}
      />
    </Section>
  );
}
