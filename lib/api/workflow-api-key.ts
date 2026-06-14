/** Deploy-time workflow keys: `wbk_live_` + 32 hex chars from secrets.token_hex(16). */
const FULL_WORKFLOW_API_KEY = /^wbk_live_[a-f0-9]{32}$/;

export function isFullWorkflowApiKey(key: string | null | undefined): key is string {
  return Boolean(key && FULL_WORKFLOW_API_KEY.test(key));
}
