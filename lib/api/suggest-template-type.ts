export async function fetchSuggestedTemplateType(
  name: string,
  description: string
): Promise<string | null> {
  const trimmedName = name.trim();
  const trimmedDescription = description.trim();
  if (!trimmedName && !trimmedDescription) return null;

  const params = new URLSearchParams({
    name: trimmedName,
    description: trimmedDescription,
  });
  const res = await fetch(`/api/v1/schema/suggest-type?${params.toString()}`, {
    credentials: "include",
  });
  if (!res.ok) return null;
  const data = (await res.json()) as { templateType?: string };
  return data.templateType?.trim() || null;
}
