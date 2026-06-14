import type { RuleTemplate } from "@/lib/types";
import { browserApi, throwOnApiError } from "@/lib/api/openapi-client";

export async function fetchRulesLibraryClient(): Promise<RuleTemplate[]> {
  const { data, error, response } = await browserApi.GET("/v1/rules/library");
  if (error || !response.ok || !data) throwOnApiError(error, response);
  const body = data as { rules: RuleTemplate[] };
  return body.rules;
}
