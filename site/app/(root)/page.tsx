import type { Metadata } from "next";
import Link from "next/link";
import { SITE } from "@/lib/site";

export const metadata: Metadata = {
  title: SITE.name,
  alternates: { canonical: `${SITE.url}/fr/` },
  robots: { index: false, follow: true },
};

/** repody.com/ → /fr/ (the CDN redirects first; this page covers a plain static host). */
export default function Root() {
  return (
    <p style={{ fontFamily: "system-ui", padding: 24 }}>
      <meta httpEquiv="refresh" content="0;url=/fr/" />
      <Link href="/fr/">Repody (français)</Link> · <Link href="/en/">Repody (English)</Link>
    </p>
  );
}
