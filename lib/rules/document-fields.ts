import { fieldKey } from "@/lib/rules/field-key";
import type { Catalog, DocumentDef } from "@/lib/types";

/** A field a rule can read: its name as rules write it, and its template type. */
export type FieldOption = { name: string; type: string };

/** An object-array field, with its columns named as the schema writes them. */
export type TableOption = { name: string; columns: FieldOption[] };

/** The documents a rule applies to (all of them when it names none). */
function ruleDocuments(documents: DocumentDef[], appliesTo: string[]): DocumentDef[] {
  return appliesTo.length ? documents.filter((doc) => appliesTo.includes(doc.id)) : documents;
}

/** With several documents, fields are named `<document type>.<field>` (as the API resolves them). */
function qualified(doc: DocumentDef, name: string, multi: boolean): string {
  return multi ? `${doc.documentType}.${name}` : name;
}

/** Fields a rule can compare: top-level fields and the children of object fields. */
export function fieldOptions(documents: DocumentDef[], appliesTo: string[]): FieldOption[] {
  const multi = documents.length > 1;
  return ruleDocuments(documents, appliesTo).flatMap((doc) =>
    doc.schema
      .filter((field) => field.name.trim())
      .flatMap((field) =>
        field.templateType === "object"
          ? field.children
              .filter((child) => child.name.trim())
              .map((child) => ({
                name: qualified(doc, `${field.name}.${child.name}`, multi),
                type: child.templateType,
              }))
          : [{ name: qualified(doc, field.name, multi), type: field.templateType }],
      ),
  );
}

/** Object-array fields a rule can sum or count. */
export function tableOptions(
  documents: DocumentDef[],
  appliesTo: string[],
  catalog: Catalog,
): TableOption[] {
  const multi = documents.length > 1;
  return ruleDocuments(documents, appliesTo).flatMap((doc) =>
    doc.schema
      .filter((field) => field.name.trim() && field.templateType === catalog.tableType)
      .map((field) => ({
        name: qualified(doc, field.name, multi),
        columns: field.children
          .filter((child) => child.name.trim())
          .map((child) => ({ name: child.name, type: child.templateType })),
      })),
  );
}

/** The type of the field `name` refers to, matched as the API matches names. */
export function typeOf(name: string, fields: FieldOption[]): string | undefined {
  const key = fieldKey(name);
  return key ? fields.find((field) => fieldKey(field.name) === key)?.type : undefined;
}
