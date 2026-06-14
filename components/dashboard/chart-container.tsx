"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";

/** Defers Recharts mount until layout is ready (avoids width/height -1 warnings). */
export function ChartContainer({
  className,
  children,
  ...props
}: {
  className?: string;
  children: ReactNode;
} & React.HTMLAttributes<HTMLDivElement>) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;
    let frame = 0;

    const observer = new ResizeObserver(([entry]) => {
      if (entry.contentRect.width > 0 && entry.contentRect.height > 0) {
        observer.disconnect();
        frame = window.requestAnimationFrame(() => setReady(true));
      }
    });
    observer.observe(element);
    return () => {
      observer.disconnect();
      window.cancelAnimationFrame(frame);
    };
  }, []);

  return (
    <div ref={containerRef} className={cn("min-h-0 min-w-0", className)} {...props}>
      {ready ? children : null}
    </div>
  );
}
