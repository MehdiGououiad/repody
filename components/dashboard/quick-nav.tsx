import Link from "next/link";
import { getTranslations } from "next-intl/server";
import {
  FileCheck2,
  GitBranch,
  SlidersHorizontal,
  ArrowUpRight,
} from "lucide-react";

const LINKS = [
  { href: "/workflows/new", icon: GitBranch, labelKey: "newWorkflow" as const },
  { href: "/workflows", icon: GitBranch, labelKey: "workflows" as const },
  { href: "/audits", icon: FileCheck2, labelKey: "audits" as const },
  { href: "/settings?tab=diagnostics", icon: SlidersHorizontal, labelKey: "console" as const },
] as const;

export async function DashboardQuickNav() {
  const t = await getTranslations("dashboard.quickNav");

  return (
    <section className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {LINKS.map(({ href, icon: Icon, labelKey }) => (
        <Link
          key={href}
          href={href}
          className="panel-elevated rounded-xl px-4 py-3 flex items-center justify-between gap-2 hover:border-primary/30 transition-colors group"
        >
          <div className="flex items-center gap-2 min-w-0">
            <Icon className="h-4 w-4 text-primary shrink-0" aria-hidden="true" />
            <span className="text-sm font-medium text-on-surface truncate">{t(labelKey)}</span>
          </div>
          <ArrowUpRight className="h-3.5 w-3.5 text-on-surface-variant group-hover:text-primary shrink-0" />
        </Link>
      ))}
    </section>
  );
}
