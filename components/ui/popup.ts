/** The surface every popup shares (menus, selects, comboboxes, popovers), opening from its trigger. */
export const popupSurface =
  "z-50 min-w-44 origin-(--transform-origin) overflow-y-auto overscroll-contain rounded-lg bg-overlay p-1 text-ink shadow-pop outline-none max-h-(--available-height) transition-[opacity,scale] duration-150 ease-out data-starting-style:scale-[0.97] data-starting-style:opacity-0 data-ending-style:scale-[0.97] data-ending-style:opacity-0 data-ending-style:duration-100 motion-reduce:transition-none";

/** A row inside a popup. */
export const popupItem =
  "relative flex h-7 cursor-pointer select-none items-center gap-2 rounded-md px-2 text-[13px] text-ink-2 outline-none data-highlighted:bg-hover data-highlighted:text-ink data-disabled:pointer-events-none data-disabled:opacity-45 data-checked:text-ink [&_svg]:size-3.5 [&_svg]:shrink-0 [&_svg]:text-ink-3";

export const popupLabel = "px-2 pb-1 pt-1.5 text-xs font-medium text-ink-3";

export const popupSeparator = "-mx-1 my-1 h-px bg-line";
