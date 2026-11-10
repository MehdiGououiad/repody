import type { Locale } from "@/i18n/config";
import type messages from "@/messages/en.json";

// Every `t("…")` key is checked against the English messages (French must have the same keys).
declare module "next-intl" {
  interface AppConfig {
    Locale: Locale;
    Messages: typeof messages;
  }
}
