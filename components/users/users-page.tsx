"use client";

import { useCallback, useEffect, useState } from "react";
import {
  LoaderCircle,
  ShieldCheck,
  SlidersHorizontal,
  Users,
} from "lucide-react";
import { toast } from "sonner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  createIamUser,
  fetchIamCatalog,
  fetchIamMe,
  fetchIamUsers,
  updateIamUser,
  type IamCatalog,
  type IamMe,
  type IamUser,
} from "@/lib/api/iam";
import { fetchPlatformConfig, type PlatformConfig } from "@/lib/api/platform-config";
import { AccessPanel } from "./access-panel";
import { SettingsPanel } from "./settings-panel";
import { TeamPanel, type UsersState } from "./team-panel";
import {
  DEFAULT_INVITE_FORM,
  InviteUserDialog,
  ManageUserDialog,
  type InviteUserForm,
  type ManageUserForm,
} from "./user-dialogs";
import { displayName } from "./user-access-shared";

const DEFAULT_APP_ROLES = ["platform_admin", "admin", "operator", "viewer"];

export function UsersPage() {
  const [me, setMe] = useState<IamMe | null>(null);
  const [catalog, setCatalog] = useState<IamCatalog | null>(null);
  const [platform, setPlatform] = useState<PlatformConfig | null>(null);
  const [platformError, setPlatformError] = useState<string | null>(null);
  const [usersState, setUsersState] = useState<UsersState | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [settingsRefreshing, setSettingsRefreshing] = useState(false);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [editUser, setEditUser] = useState<IamUser | null>(null);
  const [saving, setSaving] = useState(false);
  const [inviteForm, setInviteForm] = useState<InviteUserForm>(DEFAULT_INVITE_FORM);
  const [editForm, setEditForm] = useState<ManageUserForm>({
    firstName: "",
    lastName: "",
    enabled: true,
    roles: [],
    password: "",
  });

  const load = useCallback(async (query?: string) => {
    const [nextMe, nextCatalog, nextUsers, nextPlatform] = await Promise.all([
      fetchIamMe(),
      fetchIamCatalog().catch(() => null),
      fetchIamUsers(query).catch((error) => ({
        users: [],
        managementAvailable: false,
        managementError: error instanceof Error ? error.message : "Could not list users.",
      })),
      fetchPlatformConfig()
        .then((data) => ({ data, error: null }))
        .catch((error) => ({
          data: null,
          error: error instanceof Error ? error.message : "Could not load platform settings.",
        })),
    ]);
    setMe(nextMe);
    setCatalog(nextCatalog);
    setUsersState(nextUsers);
    setPlatform(nextPlatform.data);
    setPlatformError(nextPlatform.error);
  }, []);

  useEffect(() => {
    let active = true;

    void Promise.resolve()
      .then(() => load())
      .catch((error) => {
        toast.error(error instanceof Error ? error.message : "IAM API unavailable");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [load]);

  const refresh = async () => {
    setRefreshing(true);
    try {
      await load(search);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Refresh failed");
    } finally {
      setRefreshing(false);
    }
  };

  const refreshSettings = async () => {
    setSettingsRefreshing(true);
    try {
      await load(search);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Settings refresh failed");
    } finally {
      setSettingsRefreshing(false);
    }
  };

  const openEdit = (user: IamUser) => {
    setEditUser(user);
    setEditForm({
      firstName: user.firstName ?? "",
      lastName: user.lastName ?? "",
      enabled: user.enabled,
      roles: [...user.roles],
      password: "",
    });
  };

  const submitInvite = async () => {
    setSaving(true);
    try {
      const created = await createIamUser({
        email: inviteForm.email.trim(),
        firstName: inviteForm.firstName.trim(),
        lastName: inviteForm.lastName.trim(),
        password: inviteForm.password,
        roles: inviteForm.roles,
      });
      toast.success(`Invited ${created.email ?? created.username}`);
      setInviteOpen(false);
      setInviteForm(DEFAULT_INVITE_FORM);
      await load(search);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not create user");
    } finally {
      setSaving(false);
    }
  };

  const submitEdit = async () => {
    if (!editUser) return;
    setSaving(true);
    try {
      await updateIamUser(editUser.id, {
        firstName: editForm.firstName.trim(),
        lastName: editForm.lastName.trim(),
        enabled: editForm.enabled,
        roles: editForm.roles,
        password: editForm.password.trim() || undefined,
      });
      toast.success(`Updated ${displayName(editUser)}`);
      setEditUser(null);
      await load(search);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not update user");
    } finally {
      setSaving(false);
    }
  };

  const appRoles = catalog?.appRoles ?? DEFAULT_APP_ROLES;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-on-surface-variant">
        <LoaderCircle className="h-6 w-6 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Tabs defaultValue="team" className="space-y-6">
        <TabsList className="flex h-auto flex-wrap justify-start gap-1 p-1">
          <TabsTrigger value="team" className="gap-2">
            <Users className="h-4 w-4" />
            Team members
          </TabsTrigger>
          <TabsTrigger value="access" className="gap-2">
            <ShieldCheck className="h-4 w-4" />
            Access policy
          </TabsTrigger>
          <TabsTrigger value="settings" className="gap-2">
            <SlidersHorizontal className="h-4 w-4" />
            Settings
          </TabsTrigger>
        </TabsList>

        <TabsContent value="team" className="space-y-6">
          <TeamPanel
            me={me}
            usersState={usersState}
            search={search}
            refreshing={refreshing}
            onSearchChange={setSearch}
            onSearchSubmit={() => void load(search)}
            onRefresh={() => void refresh()}
            onInvite={() => setInviteOpen(true)}
            onEdit={openEdit}
          />
        </TabsContent>

        <TabsContent value="access" className="space-y-6">
          <AccessPanel me={me} catalog={catalog} />
        </TabsContent>

        <TabsContent value="settings">
          <SettingsPanel
            me={me}
            catalog={catalog}
            platform={platform}
            platformError={platformError}
            onRefresh={() => void refreshSettings()}
            refreshing={settingsRefreshing}
          />
        </TabsContent>
      </Tabs>

      <InviteUserDialog
        open={inviteOpen}
        appRoles={appRoles}
        catalog={catalog}
        form={inviteForm}
        saving={saving}
        onOpenChange={setInviteOpen}
        onFormChange={setInviteForm}
        onSubmit={() => void submitInvite()}
      />

      <ManageUserDialog
        user={editUser}
        appRoles={appRoles}
        catalog={catalog}
        form={editForm}
        saving={saving}
        onUserChange={setEditUser}
        onFormChange={setEditForm}
        onSubmit={() => void submitEdit()}
      />
    </div>
  );
}
