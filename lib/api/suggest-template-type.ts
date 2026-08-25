import { browserApi } from "@/lib/api/openapi-client";

export async function fetchSuggestedTemplateType(
  name: string,
  description: string
): Promise<string | null> {
  const trimmedName = name.trim();
  const trimmedDescription = description.trim();
  if (!trimmedName && !trimmedDescription) return null;

  const { data, response } = await browserApi.GET("/v1/schema/suggest-type", {
    params: {
      query: {
        name: trimmedName,
        description: trimmedDescription,
      },
    },
  });
  if (!response.ok || !data) return null;
  return data.templateType?.trim() || null;
}
