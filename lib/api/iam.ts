import type { components } from "@/lib/api/generated/schema";
import { browserApi, throwOnApiError } from "@/lib/api/openapi-client";

export type IamMe = components["schemas"]["IamMeResponse"];
export type IamCatalog = components["schemas"]["IamCatalogResponse"];

/** Schema marks roles optional; UI always treats it as a list. */
export type IamUser = Omit<components["schemas"]["IamUser"], "roles"> & {
  roles: string[];
};

export type IamUsersResponse = Omit<components["schemas"]["IamUsersResponse"], "users"> & {
  users: IamUser[];
};

export type CreateIamUserInput = {
  email: string;
  firstName?: string;
  lastName?: string;
  password: string;
  roles: string[];
  enabled?: boolean;
};

export type UpdateIamUserInput = {
  firstName?: string;
  lastName?: string;
  enabled?: boolean;
  roles?: string[];
  password?: string;
};

function normalizeUser(user: components["schemas"]["IamUser"]): IamUser {
  return { ...user, roles: user.roles ?? [] };
}

export async function fetchIamMe(): Promise<IamMe> {
  const { data, error, response } = await browserApi.GET("/v1/iam/me");
  if (error || !response.ok || !data) throwOnApiError(error, response);
  return data;
}

export async function fetchIamCatalog(): Promise<IamCatalog> {
  const { data, error, response } = await browserApi.GET("/v1/iam/catalog");
  if (error || !response.ok || !data) throwOnApiError(error, response);
  return data;
}

export async function fetchIamUsers(search?: string): Promise<IamUsersResponse> {
  const trimmed = search?.trim() || undefined;
  const { data, error, response } = await browserApi.GET("/v1/iam/users", {
    params: { query: { search: trimmed } },
  });
  if (error || !response.ok || !data) throwOnApiError(error, response);
  return {
    ...data,
    users: data.users.map(normalizeUser),
  };
}

export async function createIamUser(body: CreateIamUserInput): Promise<IamUser> {
  const { data, error, response } = await browserApi.POST("/v1/iam/users", {
    body: {
      email: body.email,
      firstName: body.firstName ?? "",
      lastName: body.lastName ?? "",
      password: body.password,
      roles: body.roles,
      enabled: body.enabled ?? true,
    },
  });
  if (error || !response.ok || !data) throwOnApiError(error, response);
  return normalizeUser(data);
}

export async function updateIamUser(userId: string, body: UpdateIamUserInput): Promise<IamUser> {
  const { data, error, response } = await browserApi.PATCH("/v1/iam/users/{user_id}", {
    params: { path: { user_id: userId } },
    body: {
      firstName: body.firstName,
      lastName: body.lastName,
      enabled: body.enabled,
      roles: body.roles,
      password: body.password,
    },
  });
  if (error || !response.ok || !data) throwOnApiError(error, response);
  return normalizeUser(data);
}
