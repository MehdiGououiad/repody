import { CircleAlert } from "lucide-react";
import { getTranslations } from "next-intl/server";
import type { Access } from "@/lib/types";

/** A client's users see this before their runs are refused: few credits are left. */
export async function CreditsBanner({ access }: { access: Access }) {
  const credits = access.credits;
  if (!credits?.low) return null;
  const t = await getTranslations("credits");
  return (
    <div
      // oxlint-disable-next-line jsx-a11y/prefer-tag-over-role -- a live region (ARIA status), not the result of a calculation (<output>).
      role="status"
      className="flex h-9 shrink-0 items-center gap-2 border-b border-line bg-warn-wash px-4 text-[13px] text-warn-ink"
    >
      <CircleAlert className="size-3.5 shrink-0" aria-hidden />
      <span className="min-w-0 truncate">
        {credits.balance > 0 ? t("low", { balance: credits.balance }) : t("none")}
      </span>
    </div>
  );
}
