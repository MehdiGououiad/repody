"use client";

import { ToggleGroup } from "radix-ui";
import { cn } from "@/lib/utils";

/** A small set of mutually exclusive choices, the chosen one on a raised step. Instant.
 * Radix ToggleGroup: arrow keys move between options, one is always chosen. */
export function Segmented<T extends string>({
  value,
  options,
  onChange,
  label,
  className,
}: {
  value: T;
  options: { value: T; label: React.ReactNode; disabled?: boolean; title?: string }[];
  onChange: (value: T) => void;
  label: string;
  className?: string;
}) {
  return (
    <ToggleGroup.Root
      type="single"
      value={value}
      onValueChange={(next) => {
        if (next) onChange(next as T);
      }}
      aria-label={label}
      className={cn("inline-flex h-7 items-center gap-0.5 rounded-md bg-selected p-0.5", className)}
    >
      {options.map((option) => (
        <ToggleGroup.Item
          key={option.value}
          value={option.value}
          disabled={option.disabled}
          title={option.title}
          className="flex h-6 cursor-pointer items-center gap-1.5 rounded-[5px] px-2 text-xs font-medium text-ink-3 transition-colors duration-100 hover:text-ink disabled:cursor-not-allowed disabled:opacity-45 data-[state=on]:bg-overlay data-[state=on]:text-ink data-[state=on]:shadow-[0_0_0_1px_var(--line),0_1px_2px_var(--shadow-color)] [&_svg]:size-3.5"
        >
          {option.label}
        </ToggleGroup.Item>
      ))}
    </ToggleGroup.Root>
  );
}
