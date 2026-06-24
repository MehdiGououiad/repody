"use client";

import { LoaderCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { IamCatalog, IamUser } from "@/lib/api/iam";
import { displayName, RolePicker } from "./user-access-shared";

export type InviteUserForm = {
  email: string;
  firstName: string;
  lastName: string;
  password: string;
  roles: string[];
};

export type ManageUserForm = {
  firstName: string;
  lastName: string;
  enabled: boolean;
  roles: string[];
  password: string;
};

export const DEFAULT_INVITE_FORM: InviteUserForm = {
  email: "",
  firstName: "",
  lastName: "",
  password: "",
  roles: ["viewer"],
};

export function InviteUserDialog({
  open,
  appRoles,
  catalog,
  form,
  saving,
  onOpenChange,
  onFormChange,
  onSubmit,
}: {
  open: boolean;
  appRoles: string[];
  catalog: IamCatalog | null;
  form: InviteUserForm;
  saving: boolean;
  onOpenChange: (open: boolean) => void;
  onFormChange: (form: InviteUserForm) => void;
  onSubmit: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Invite user</DialogTitle>
          <DialogDescription>Creates a Keycloak account with the selected platform roles.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="invite-email">Email</Label>
              <Input
                id="invite-email"
                type="email"
                value={form.email}
                onChange={(event) => onFormChange({ ...form, email: event.target.value })}
                placeholder="name@company.com"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="invite-first">First name</Label>
              <Input
                id="invite-first"
                value={form.firstName}
                onChange={(event) => onFormChange({ ...form, firstName: event.target.value })}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="invite-last">Last name</Label>
              <Input
                id="invite-last"
                value={form.lastName}
                onChange={(event) => onFormChange({ ...form, lastName: event.target.value })}
              />
            </div>
            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="invite-password">Temporary password</Label>
              <Input
                id="invite-password"
                type="password"
                value={form.password}
                onChange={(event) => onFormChange({ ...form, password: event.target.value })}
                placeholder="Minimum 8 characters"
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label>Platform roles</Label>
            <RolePicker
              appRoles={appRoles}
              catalog={catalog}
              value={form.roles}
              onChange={(roles) => onFormChange({ ...form, roles })}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={onSubmit} disabled={saving || form.email.trim().length < 3 || form.password.length < 8}>
            {saving ? <LoaderCircle className="h-4 w-4 animate-spin" /> : "Create user"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function ManageUserDialog({
  user,
  appRoles,
  catalog,
  form,
  saving,
  onUserChange,
  onFormChange,
  onSubmit,
}: {
  user: IamUser | null;
  appRoles: string[];
  catalog: IamCatalog | null;
  form: ManageUserForm;
  saving: boolean;
  onUserChange: (user: IamUser | null) => void;
  onFormChange: (form: ManageUserForm) => void;
  onSubmit: () => void;
}) {
  return (
    <Dialog open={!!user} onOpenChange={(open) => !open && onUserChange(null)}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Manage user</DialogTitle>
          <DialogDescription>{user ? displayName(user) : ""} - update roles, status, or password.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="edit-first">First name</Label>
              <Input
                id="edit-first"
                value={form.firstName}
                onChange={(event) => onFormChange({ ...form, firstName: event.target.value })}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="edit-last">Last name</Label>
              <Input
                id="edit-last"
                value={form.lastName}
                onChange={(event) => onFormChange({ ...form, lastName: event.target.value })}
              />
            </div>
            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="edit-password">New password (optional)</Label>
              <Input
                id="edit-password"
                type="password"
                value={form.password}
                onChange={(event) => onFormChange({ ...form, password: event.target.value })}
                placeholder="Leave blank to keep current password"
              />
            </div>
          </div>
          <div className="flex items-center justify-between rounded-xl border border-border px-3 py-2.5">
            <div>
              <p className="text-sm font-medium">Account active</p>
              <p className="text-xs text-on-surface-variant">Disabled users cannot sign in.</p>
            </div>
            <Button
              type="button"
              size="sm"
              variant={form.enabled ? "default" : "outline"}
              onClick={() => onFormChange({ ...form, enabled: !form.enabled })}
            >
              {form.enabled ? "Enabled" : "Disabled"}
            </Button>
          </div>
          <div className="space-y-2">
            <Label>Platform roles</Label>
            <RolePicker
              appRoles={appRoles}
              catalog={catalog}
              value={form.roles}
              onChange={(roles) => onFormChange({ ...form, roles })}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onUserChange(null)} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={onSubmit} disabled={saving}>
            {saving ? <LoaderCircle className="h-4 w-4 animate-spin" /> : "Save changes"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
