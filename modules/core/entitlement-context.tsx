"use client";

import { createContext, use } from "react";
import {
  hasModule,
  showModuleSwitcher,
  type EntitlementState,
  type ModuleId,
} from "./entitlements";

const DEFAULT_ENTITLEMENTS: EntitlementState = {
  status: "active",
  modules: ["idp"],
  warning: null,
};

const EntitlementContext = createContext<EntitlementState>(DEFAULT_ENTITLEMENTS);

export const EntitlementProvider = EntitlementContext;

export function useEntitlements(): EntitlementState {
  return use(EntitlementContext);
}

export function useHasModule(module: ModuleId): boolean {
  return hasModule(use(EntitlementContext), module);
}

export function useShowModuleSwitcher(): boolean {
  return showModuleSwitcher(use(EntitlementContext));
}
