import { fieldTypeGroups } from "@/content";
import type { Locale } from "@/lib/site";

/** Every field type of the builder, by group, with the product's own names and descriptions. */
export function FieldTypes({ locale }: { locale: Locale }) {
  return (
    <div className="grid gap-10 lg:grid-cols-3">
      {fieldTypeGroups(locale).map((group) => (
        <section key={group.group} aria-labelledby={`types-${group.group}`}>
          <h3
            id={`types-${group.group}`}
            className="flex items-baseline gap-2 text-sm font-semibold text-ink"
          >
            {group.title}
            <span className="font-normal tabular-nums text-ink-4">{group.types.length}</span>
          </h3>
          <ul className="mt-3 flex flex-col">
            {group.types.map((type) => (
              <li key={type.value} className="flex flex-col gap-0.5 border-t border-line py-2.5">
                <span className="flex items-baseline justify-between gap-3">
                  <span className="text-[0.9375rem] text-ink">{type.label}</span>
                  <code className="font-mono text-xs text-ink-4">{type.value}</code>
                </span>
                <span className="text-sm text-ink-3">{type.description}</span>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
