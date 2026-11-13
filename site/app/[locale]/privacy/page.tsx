import { ProsePage } from "@/components/prose-page";
import { dict } from "@/content";
import { pageMetadata } from "@/lib/meta";
import type { Locale } from "@/lib/site";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props) {
  const { locale } = await params;
  return pageMetadata(locale, "privacy", dict(locale).privacy.meta);
}

export default async function Privacy({ params }: Props) {
  const { locale } = await params;
  const { title, body } = dict(locale).privacy;
  return <ProsePage title={title} body={body} />;
}
