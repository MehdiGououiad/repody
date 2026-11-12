"use client";

import { useTranslations } from "next-intl";
import { CopyIconButton } from "@/components/shared/copyable-output-panel";

export function CopyButton({ text, className }: { text: string; className?: string }) {
  const t = useTranslations("common");
  return (
    <CopyIconButton
      text={text}
      label={t("copy")}
      copiedLabel={t("copied")}
      failedLabel={t("copyFailed")}
      className={className}
    />
  );
}
