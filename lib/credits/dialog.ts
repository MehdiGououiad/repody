import { createDialogController } from "@ui-sdk/react/dialog";

/** "Contact us for credits", opened by the API client when the API answers 402. */
export const creditsDialog = createDialogController();

export function openCredits(): void {
  void creditsDialog.open();
}
