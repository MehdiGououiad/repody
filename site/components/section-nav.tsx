"use client";

import { useEffect, useState } from "react";

/** The page's sections as a sticky row of anchors; the one being read is marked. */
export function SectionNav({
  label,
  items,
}: {
  label: string;
  items: { id: string; title: string }[];
}) {
  const [active, setActive] = useState(items[0]?.id);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActive(visible[0].target.id);
      },
      { rootMargin: "-120px 0px -60% 0px" },
    );
    for (const item of items) {
      const el = document.getElementById(item.id);
      if (el) observer.observe(el);
    }
    return () => observer.disconnect();
  }, [items]);

  return (
    <nav
      aria-label={label}
      className="sticky top-14 z-30 border-b border-line bg-panel/90 backdrop-blur-md"
    >
      <ul className="mx-auto flex w-full max-w-[1180px] gap-1 overflow-x-auto px-5 py-2 [scrollbar-width:none] md:px-8">
        {items.map((item) => (
          <li key={item.id} className="shrink-0">
            <a
              href={`#${item.id}`}
              aria-current={active === item.id ? "true" : undefined}
              className="block rounded-md px-3 py-1.5 text-sm text-ink-3 transition-colors duration-150 hover:bg-hover hover:text-ink aria-[current=true]:bg-selected aria-[current=true]:text-ink"
            >
              {item.title}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
