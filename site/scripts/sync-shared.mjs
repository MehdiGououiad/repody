// Copies what the site shares with the product into lib/shared/ (git-ignored), before dev and
// build: the theme engine, and the field types (the backend's catalog, named as the product
// names them). One source of truth, and the site's bundler never reaches outside its own folder.
import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..", "..");
const out = path.resolve(import.meta.dirname, "..", "lib", "shared");
mkdirSync(out, { recursive: true });

copyFileSync(path.join(root, "lib/theme/generate.ts"), path.join(out, "theme-generate.ts"));

// backend/src/repody/schemas/catalog.py: LEAF_TYPES = {"type": "group", ...}; STRUCTURE_TYPES = ("type", ...)
const catalog = readFileSync(path.join(root, "backend/src/repody/schemas/catalog.py"), "utf8");
const leafBlock = catalog.match(/LEAF_TYPES[^{]*\{([^}]*)\}/)?.[1] ?? "";
const structureBlock = catalog.match(/STRUCTURE_TYPES = \(([^)]*)\)/)?.[1] ?? "";
const types = [
  ...[...leafBlock.matchAll(/"([a-z-]+)":\s*"([a-z]+)"/g)].map(([, value, group]) => ({
    value,
    group,
  })),
  ...[...structureBlock.matchAll(/"([a-z-]+)"/g)].map(([, value]) => ({
    value,
    group: "structure",
  })),
];
if (types.length < 20)
  throw new Error(`sync-shared: read only ${types.length} field types from catalog.py`);

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
