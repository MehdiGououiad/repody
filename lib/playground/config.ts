import "server-only";

import { demoMode } from "@/lib/auth/visitor";

/** How the playground asks for credits: its contact page and, when set, a WhatsApp number. */
export type PlaygroundContact = { contactUrl: string; whatsapp: string | null };

/** The playground's contact details (runtime environment, like the rest of the deployment),
 * or null outside demo mode. */
export function playgroundContact(): PlaygroundContact | null {
  if (!demoMode) return null;
  const whatsapp = (process.env.REPODY_CONTACT_WHATSAPP ?? "").replace(/\D/g, "");
  return {
    contactUrl: process.env.REPODY_CONTACT_URL || "https://repody.com/fr/contact",
    whatsapp: whatsapp || null,
  };
}
