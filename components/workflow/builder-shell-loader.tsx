import { Skeleton } from "@/components/ui/skeleton";

export function BuilderShellLoader() {
  return (
    <div className="flex h-full flex-col">
      <div className="h-11 border-b border-line" />
      <div className="h-10 border-b border-line" />
      <div className="mx-auto w-full max-w-[1100px] px-4 py-8 md:px-8">
        <Skeleton className="mb-6 h-6 w-56" />
        <Skeleton.Lines count={7} />
      </div>
    </div>
  );
}
