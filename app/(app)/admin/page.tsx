import { getTranslations } from "next-intl/server";
import { AdminArea } from "@/components/admin/admin-area";
import { Page } from "@/components/layout/page";
import { requirePermission } from "@/lib/api/server";

export async function generateMetadata() {
  return { title: (await getTranslations("admin"))("title") };
}

export default async function AdminPage() {
  await requirePermission("clients:manage");
  const t = await getTranslations("admin");
  return (
    <Page description={(await getTranslations("pageHints"))("admin")} title={t("title")}>
      <AdminArea />
    </Page>
  );
}
