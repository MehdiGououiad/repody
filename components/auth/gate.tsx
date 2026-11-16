"use client";

import { useTranslations } from "next-intl";
import { cloneElement } from "react";
import { useCan } from "@/components/auth/access-context";
import { Tooltip } from "@/components/ui/tooltip";
import type { Permission } from "@/lib/types";

/** An action the caller's role may not allow stays visible, dimmed and focusable, and its
 * tooltip says why (ui-sdk: a natively disabled button gets no tooltip). */
export function Gate({
  permission,
  children,
}: {
  permission: Permission;
  children: React.ReactElement<{ disabled?: boolean; focusableWhenDisabled?: boolean }>;
}) {
  const allowed = useCan(permission);
  const t = useTranslations("common");
  if (allowed) return children;
  return (
    <Tooltip label={t("notAllowed")}>
      {cloneElement(children, { disabled: true, focusableWhenDisabled: true })}
    </Tooltip>
  );
}
