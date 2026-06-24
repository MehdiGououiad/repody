"use client";

import { Database, Gauge, Shield } from "lucide-react";
import { PermissionMatrix } from "./permission-matrix";
import { SettingMetric } from "./user-access-shared";
import type { IamCatalog, IamMe } from "@/lib/api/iam";

export function AccessPanel({ me, catalog }: { me: IamMe | null; catalog: IamCatalog | null }) {
  return (
    <>
      <section className="grid gap-4 lg:grid-cols-3">
        <SettingMetric
          label="Current role"
          value={me?.roles[0] ?? "-"}
          detail={me?.email ?? me?.subject ?? "Signed in"}
          icon={Shield}
          tone="success"
        />
        <SettingMetric
          label="Permissions"
          value={`${me?.permissions.length ?? 0}`}
          detail={me?.permissions.some((grant) => grant.resource === "*") ? "Full access principal" : "Scoped access"}
          icon={Gauge}
        />
        <SettingMetric
          label="Policy roles"
          value={`${catalog?.appRoles.length ?? 0}`}
          detail="Keycloak realm roles mapped to backend RBAC"
          icon={Database}
        />
      </section>
      <PermissionMatrix catalog={catalog} />
    </>
  );
}
