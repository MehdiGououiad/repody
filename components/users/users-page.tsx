"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LoaderCircle, ShieldCheck, SlidersHorizontal, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  createIamUser,
  fetchIamCatalog,
  fetchIamMe,
  fetchIamUsers,
  type IamUser,
  type UpdateIamUserInput,
  updateIamUser,
} from "@/lib/api/iam";
import { fetchPlatformConfig } from "@/lib/api/platform-config";
import { queryKeys } from "@/lib/hooks/query-keys";
import { AccessPanel } from "./access-panel";
import { SettingsPanel } from "./settings-panel";
import { TeamPanel } from "./team-panel";
import { displayName } from "./user-access-shared";
import {
  DEFAULT_INVITE_FORM,
  InviteUserDialog,
  type InviteUserForm,
  ManageUserDialog,
  type ManageUserForm,
} from "./user-dialogs";

const DEFAULT_APP_ROLES = ["platform_admin", "admin", "operator", "viewer"];

export function UsersPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [inviteOpen, setInviteOpen] = useState(false);
  const [editUser, setEditUser] = useState<IamUser | null>(null);
  const [inviteForm, setInviteForm] = useState<InviteUserForm>(DEFAULT_INVITE_FORM);
  const [editForm, setEditForm] = useState<ManageUserForm>({
    firstName: "",
    lastName: "",
    enabled: true,
    roles: [],
    password: "",
  });

  const meQuery = useQuery({
    queryKey: queryKeys.iam.me(),
    queryFn: fetchIamMe,
  });

  const catalogQuery = useQuery({
    queryKey: queryKeys.iam.catalog(),
    queryFn: fetchIamCatalog,
    retry: false,
  });

  const usersQuery = useQuery({
    queryKey: queryKeys.iam.users(appliedSearch),
    queryFn: () =>
      fetchIamUsers(appliedSearch).catch((error) => ({
        users: [] as IamUser[],
        managementAvailable: false,
        managementError: error instanceof Error ? error.message : "Could not list users.",
      })),
  });

  const platformQuery = useQuery({
    queryKey: queryKeys.catalog.platformConfig,
    queryFn: fetchPlatformConfig,
    retry: false,
  });

  useEffect(() => {
    if (!meQuery.isError) return;
    toast.error(meQuery.error instanceof Error ? meQuery.error.message : "IAM API unavailable");
  }, [meQuery.isError, meQuery.error]);

  const createMutation = useMutation({
    mutationFn: createIamUser,
    onSuccess: async (created) => {
      toast.success(`Invited ${created.email ?? created.username}`);
      setInviteOpen(false);
      setInviteForm(DEFAULT_INVITE_FORM);
      await queryClient.invalidateQueries({ queryKey: queryKeys.iam.all });
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "Could not create user");
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ userId, body }: { userId: string; body: UpdateIamUserInput }) =>
      updateIamUser(userId, body),
    onSuccess: async (updated) => {
      toast.success(`Updated ${displayName(updated)}`);
      setEditUser(null);
      await queryClient.invalidateQueries({ queryKey: queryKeys.iam.all });
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "Could not update user");
    },
  });

  const me = meQuery.data ?? null;
  const catalog = catalogQuery.data ?? null;
  const usersState = usersQuery.data ?? null;
  const platform = platformQuery.data ?? null;
  const platformError =
    platformQuery.error instanceof Error
      ? platformQuery.error.message
      : platformQuery.isError
        ? "Could not load platform settings."
        : null;

  const loading =
    meQuery.isPending || catalogQuery.isPending || usersQuery.isPending || platformQuery.isPending;

  const refreshing =
    (meQuery.isFetching ||
      catalogQuery.isFetching ||
      usersQuery.isFetching ||
      platformQuery.isFetching) &&
    !loading;

  const saving = createMutation.isPending || updateMutation.isPending;
  const appRoles = catalog?.appRoles ?? DEFAULT_APP_ROLES;

  const refreshAll = async () => {
    try {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.iam.all }),
        queryClient.invalidateQueries({ queryKey: queryKeys.catalog.platformConfig }),
      ]);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Refresh failed");
    }
  };

  const submitSearch = () => {
    if (search === appliedSearch) {
      void usersQuery.refetch();
      return;
    }
    setAppliedSearch(search);
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

  const submitInvite = () => {
    createMutation.mutate({
      email: inviteForm.email.trim(),
      firstName: inviteForm.firstName.trim(),
      lastName: inviteForm.lastName.trim(),
      password: inviteForm.password,
      roles: inviteForm.roles,
    });
  };

  const submitEdit = () => {
    if (!editUser) return;
    updateMutation.mutate({
      userId: editUser.id,
      body: {
        firstName: editForm.firstName.trim(),
        lastName: editForm.lastName.trim(),
        enabled: editForm.enabled,
        roles: editForm.roles,
        password: editForm.password.trim() || undefined,
      },
    });
  };

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
            onSearchSubmit={submitSearch}
            onRefresh={() => void refreshAll()}
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
            onRefresh={() => void refreshAll()}
            refreshing={refreshing}
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
        onSubmit={submitInvite}
      />

      <ManageUserDialog
        user={editUser}
        appRoles={appRoles}
        catalog={catalog}
        form={editForm}
        saving={saving}
        onUserChange={setEditUser}
        onFormChange={setEditForm}
        onSubmit={submitEdit}
      />
    </div>
  );
}
