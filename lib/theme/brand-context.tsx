"use client";

import { createContext, type ReactNode, useContext } from "react";

type PublicBrand = { name: string; logoUrl: string | null };

const BrandContext = createContext<PublicBrand>({ name: "Repody", logoUrl: null });

export function BrandProvider({ brand, children }: { brand: PublicBrand; children: ReactNode }) {
  return <BrandContext.Provider value={brand}>{children}</BrandContext.Provider>;
}

/** The product name and logo of this deployment's brand. */
export function useBrand(): PublicBrand {
  return useContext(BrandContext);
}
