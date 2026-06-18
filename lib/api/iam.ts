import { browserJson } from "@/lib/api/http";

export type PermissionGrant = {
  resource: string;
  action: string;
};

export type RoleDefinition = {
  id: string;
  label: string;
  description: string;
  permissions: PermissionGrant[];
};

export type IamUser = {
  id: string;
  username: string;
  email?: string | null;
  firstName?: string | null;
  lastName?: string | null;
  enabled: boolean;
  roles: string[];
};

export type IamMe = {
  subject: string;
  email?: string | null;
  roles: string[];
  permissions: PermissionGrant[];
  canManageUsers: boolean;
  oidcEnabled: boolean;
  keycloakAdminUrl?: string | null;
};

export type IamCatalog = {
  roles: RoleDefinition[];
  appRoles: string[];
};

export type IamUsersResponse = {
  users: IamUser[];
  managementAvailable: boolean;
  managementError?: string | null;
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

export async function fetchIamMe(): Promise<IamMe> {
  return browserJson<IamMe>("/iam/me");
}

export async function fetchIamCatalog(): Promise<IamCatalog> {
  return browserJson<IamCatalog>("/iam/catalog");
}

export async function fetchIamUsers(search?: string): Promise<IamUsersResponse> {
  const query = search?.trim() ? `?search=${encodeURIComponent(search.trim())}` : "";
  return browserJson<IamUsersResponse>(`/iam/users${query}`);
}

export async function createIamUser(body: CreateIamUserInput): Promise<IamUser> {
  return browserJson<IamUser>("/iam/users", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function updateIamUser(userId: string, body: UpdateIamUserInput): Promise<IamUser> {
  return browserJson<IamUser>(`/iam/users/${encodeURIComponent(userId)}`, {
    method: "PATCH",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}
