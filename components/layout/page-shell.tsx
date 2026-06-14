import { cn } from "@/lib/utils";

type PageShellProps = {
  children: React.ReactNode;
  className?: string;
};

function PageShellRoot({ children, className }: PageShellProps) {
  return (
    <div
      className={cn(
        "page-enter w-full min-w-0 p-4 sm:p-6 md:p-8 max-w-[1440px] mx-auto flex flex-col gap-6 md:gap-8",
        className
      )}
    >
      {children}
    </div>
  );
}

function PageShellStagger({ children, className }: PageShellProps) {
  return (
    <PageShellRoot className={cn("page-enter-stagger", className)}>
      {children}
    </PageShellRoot>
  );
}

export const PageShell = Object.assign(PageShellRoot, {
  Stagger: PageShellStagger,
});
