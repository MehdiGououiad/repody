import "server-only";

/** Where a client asks for more credits: the contact page and, when set, a WhatsApp number. */
export type CreditsContact = { contactUrl: string; whatsapp: string | null };

/** From the runtime environment, like the rest of the deployment. */
export function creditsContact(): CreditsContact {
  const whatsapp = (process.env.REPODY_CONTACT_WHATSAPP ?? "").replace(/\D/g, "");
  return {
    contactUrl: process.env.REPODY_CONTACT_URL || "https://repody.com/fr/contact/",
    whatsapp: whatsapp || null,
  };
}
