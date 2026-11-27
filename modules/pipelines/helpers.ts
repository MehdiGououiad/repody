import type { ApprovalTask } from "./types";

export type FourEyesGuard = {
  canMake: boolean;
  canCheck: boolean;
  selfApprovalBlocked: boolean;
};

export function evaluateFourEyesGuard(
  approval: Pick<ApprovalTask, "status" | "maker_sub">,
  currentActorSub: string | null | undefined,
): FourEyesGuard {
  const canMake = approval.status === "waiting_maker" || approval.status === "returned_to_maker";
  const isWaitingChecker = approval.status === "waiting_checker";
  const actor = currentActorSub?.trim() || "";
  const selfApprovalBlocked = Boolean(
    isWaitingChecker && approval.maker_sub && actor && approval.maker_sub === actor,
  );
  const canCheck = isWaitingChecker && !selfApprovalBlocked;
  return { canMake, canCheck, selfApprovalBlocked };
}
