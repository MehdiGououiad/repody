import { getTranslations } from "next-intl/server";
import { PageHeader } from "@/components/layout/page-header";
import { PageShell } from "@/components/layout/page-shell";
import { UsersPage } from "@/components/users/users-page";

export default async function UsersRoutePage() {
  const t = await getTranslations("users");

  return (
    <PageShell>
      <PageHeader
        title={t("title")}
        description={t("description")}
        eyebrow={t("eyebrow")}
      />
      <UsersPage />
    </PageShell>
  );
}
