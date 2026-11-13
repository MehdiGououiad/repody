import { createDialogController } from "@ui-sdk/react/dialog";

/** "Contact us for credits": the playground's answer when a visitor runs or publishes. Opened by
 * the gated buttons, and by the API client when the API answers 402 (repody `api/deps.py`). */
export const creditsDialog = createDialogController();

export function openCredits(): void {
  void creditsDialog.open();
}
