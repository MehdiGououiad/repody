import { Skeleton } from "@/components/ui/skeleton";

export function RunAuditReportLoader() {
  return (
    <div className="mx-auto w-full max-w-[1200px] px-4 py-14 md:px-8">
      <Skeleton className="mb-8 h-7 w-64" />
      <Skeleton.Lines count={8} />
    </div>
  );
}
