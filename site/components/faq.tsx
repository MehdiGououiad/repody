import { Plus } from "lucide-react";

/** Questions as native disclosures: keyboard and screen readers for free, no script. */
export function Faq({ items }: { items: { q: string; a: string }[] }) {
  return (
    <div className="divide-y divide-line border-y border-line">
      {items.map((item) => (
        <details key={item.q} className="group">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-6 py-5 text-[1.0625rem] font-medium text-ink [&::-webkit-details-marker]:hidden">
            {item.q}
            <Plus
              className="size-4 shrink-0 text-ink-3 transition-transform duration-200 group-open:rotate-45"
              aria-hidden
            />
          </summary>
          <p className="max-w-[760px] pb-6 text-[0.9375rem] leading-relaxed text-ink-3">{item.a}</p>
        </details>
      ))}
    </div>
  );
}
