import generated from "@/lib/api/catalog.json";
import type { Catalog } from "@/lib/types";

/** The builder's field types and the rules' comparisons: the API's catalog
 * (`repody/schemas/catalog.py`), generated with the OpenAPI schema (`pnpm codegen:api:export`). */
export const catalog = generated as Catalog;
