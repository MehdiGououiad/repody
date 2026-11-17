// Copies what the site shares with the product into lib/shared/ (git-ignored), before dev and
// build: the theme engine, and the field types (the backend's catalog, named as the product
// names them). One source of truth, and the site's bundler never reaches outside its own folder.
import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..", "..");
const out = path.resolve(import.meta.dirname, "..", "lib", "shared");
mkdirSync(out, { recursive: true });

copyFileSync(path.join(root, "lib/theme/generate.ts"), path.join(out, "theme-generate.ts"));

// The backend's catalog, as the product reads it (lib/api/catalog.json, generated from
// backend/src/repody/schemas/catalog.py with the OpenAPI schema).
const catalog = JSON.parse(readFileSync(path.join(root, "lib/api/catalog.json"), "utf8"));
const types = catalog.templateTypes.map(({ value, group }) => ({ value, group }));

const fieldTypes = { types };
for (const locale of ["fr", "en"]) {
  const schema = JSON.parse(readFileSync(path.join(root, `messages/${locale}.json`), "utf8"))
    .workflows.builder.schema;
  fieldTypes[locale] = {
    groups: schema.typeGroups,
    names: Object.fromEntries(types.map(({ value }) => [value, schema.templateTypes[value]])),
  };
}
writeFileSync(path.join(out, "field-types.json"), `${JSON.stringify(fieldTypes, null, 2)}\n`);
process.stdout.write(`site: shared theme engine and ${types.length} field types synced
`);
