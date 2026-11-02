"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { toast } from "sonner";
import {
  ACTIVE_JOB_STATUSES,
  fetchOperatorJobs,
  fetchOperatorStatus,
  type OperatorJob,
} from "@/lib/api/operator";
import { queryKeys } from "@/lib/hooks/query-keys";

const ACTIVE_JOB_POLL_MS = 5_000;

/** Operator status and jobs; jobs poll while any job is queued or running. */
export function useOperatorState() {
  const queryClient = useQueryClient();
  const status = useQuery({
    queryKey: queryKeys.operator.status,
    queryFn: fetchOperatorStatus,
  });
  const jobs = useQuery({
    queryKey: queryKeys.operator.jobs,
    queryFn: fetchOperatorJobs,
    refetchInterval: (query) =>
      query.state.data?.some((job) => ACTIVE_JOB_STATUSES.has(job.status))
        ? ACTIVE_JOB_POLL_MS
        : false,
  });

  const errorMessage = (status.error ?? jobs.error)?.message;
  useEffect(() => {
    if (errorMessage !== undefined) toast.error(errorMessage || "Operator API unavailable");
  }, [errorMessage]);

  const addJob = (job: OperatorJob) => {
    queryClient.setQueryData<OperatorJob[]>(queryKeys.operator.jobs, (current = []) => [
      job,
      ...current.filter((item) => item.id !== job.id),
    ]);
  };

  const refresh = () => {
    void status.refetch();
    void jobs.refetch();
  };

  return { operator: status.data ?? null, jobs: jobs.data ?? [], addJob, refresh };
}
