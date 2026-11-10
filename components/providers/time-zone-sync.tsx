"use client";

import { useTimeZone } from "next-intl";
import { useEffect } from "react";
import { setTimeZone } from "@/app/actions/preferences";

/** Tells the server the browser's time zone once, when it differs from the one in use. */
export function TimeZoneSync() {
  const serverZone = useTimeZone();
  useEffect(() => {
    const zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (zone && zone !== serverZone) void setTimeZone(zone);
  }, [serverZone]);
  return null;
}
