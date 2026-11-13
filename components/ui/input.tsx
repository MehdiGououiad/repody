"use client";

import { InputClear, InputGroup, Input as InputPrimitive } from "@ui-sdk/react/input";
import { Textarea as TextareaPrimitive } from "@ui-sdk/react/textarea";
import { Search, X } from "lucide-react";
import type * as React from "react";
import { partClass } from "@/lib/utils";

export const fieldClass =
  "w-full min-w-0 rounded-md bg-field px-2.5 text-[13px] text-ink shadow-[inset_0_0_0_1px_var(--line-strong)] outline-none transition-[box-shadow,background-color] duration-150 placeholder:text-ink-4 hover:shadow-[inset_0_0_0_1px_var(--ink-4)] focus:bg-panel focus:shadow-[inset_0_0_0_1px_var(--accent),0_0_0_3px_var(--accent-wash)] data-disabled:opacity-45 data-invalid:shadow-[inset_0_0_0_1px_var(--fail)]";

/** Text that looks like text until hovered or focused: for names and cells edited in place. */
export const inlineFieldClass =
  "w-full min-w-0 rounded-md bg-transparent px-1.5 text-[13px] text-ink outline-none transition-[box-shadow,background-color] duration-150 placeholder:text-ink-4 hover:bg-hover focus:bg-field focus:shadow-[inset_0_0_0_1px_var(--accent),0_0_0_3px_var(--accent-wash)]";

function Input({
  className,
  compact = false,
  ...props
}: React.ComponentProps<typeof InputPrimitive> & { compact?: boolean }) {
  return (
    <InputPrimitive
      className={partClass(`${fieldClass} ${compact ? "h-7" : "h-8"}`, className)}
      {...props}
    />
  );
}

function Textarea({ className, ...props }: React.ComponentProps<typeof TextareaPrimitive>) {
  return (
    <TextareaPrimitive
      className={partClass(`${fieldClass} min-h-20 resize-y py-2 leading-relaxed`, className)}
      {...props}
    />
  );
}

/** A quiet search field with its clear button. */
function SearchInput({
  label,
  clearLabel,
  className,
  ...props
}: Omit<React.ComponentProps<typeof InputPrimitive>, "type"> & {
  label: string;
  clearLabel: string;
}) {
  return (
    <InputGroup className="group/search flex h-7 w-full max-w-60 items-center gap-2 rounded-md px-2 text-ink-3 transition-colors duration-100 focus-within:bg-field focus-within:shadow-[inset_0_0_0_1px_var(--line-strong)] hover:bg-hover">
      <Search className="size-3.5 shrink-0" aria-hidden />
      <InputPrimitive
        type="search"
        aria-label={label}
        placeholder={label}
        autoComplete="off"
        className={partClass(
          "h-full min-w-0 flex-1 bg-transparent text-[13px] text-ink outline-none placeholder:text-ink-4 [&::-webkit-search-cancel-button]:hidden",
          className
        )}
        {...props}
      />
      <InputClear
        aria-label={clearLabel}
        className="flex size-5 cursor-pointer items-center justify-center rounded-sm text-ink-4 hover:bg-selected hover:text-ink"
      >
        <X className="size-3" aria-hidden />
      </InputClear>
    </InputGroup>
  );
}

/** ui-sdk's input with no look of its own, for cells that bring their classes. */
const BareInput = InputPrimitive;

export { BareInput, Input, SearchInput, Textarea };
