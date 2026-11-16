import { notFound } from "next/navigation";
import { ClientPage } from "@/components/admin/client-page";
import { requirePermission } from "@/lib/api/server";

const ACCOUNT = /^client-[a-z0-9][a-z0-9-]*$/;

export async function generateMetadata({ params }: { params: Promise<{ account: string }> }) {
  return { title: (await params).account };
}

export default async function AdminClientPage({
  params,
}: {
  params: Promise<{ account: string }>;
}) {
  await requirePermission("clients:manage");
  const { account } = await params;
  if (!ACCOUNT.test(account)) notFound();
  return <ClientPage account={account} />;
}
