import { describe, expect, test } from "bun:test";
import { evaluateFourEyesGuard } from "./helpers";

describe("four-eyes guard", () => {
  test("blocks Checker approval when actor equals Maker", () => {
    expect(evaluateFourEyesGuard({ status: "waiting_maker", maker_sub: null }, "alice")).toEqual({
      canMake: true,
      canCheck: false,
      selfApprovalBlocked: false,
    });

    expect(
      evaluateFourEyesGuard({ status: "waiting_checker", maker_sub: "alice" }, "alice"),
    ).toEqual({
      canMake: false,
      canCheck: false,
      selfApprovalBlocked: true,
    });

    expect(evaluateFourEyesGuard({ status: "waiting_checker", maker_sub: "alice" }, "bob")).toEqual(
      {
        canMake: false,
        canCheck: true,
        selfApprovalBlocked: false,
      },
    );

    expect(evaluateFourEyesGuard({ status: "approved", maker_sub: "alice" }, "bob")).toEqual({
      canMake: false,
      canCheck: false,
      selfApprovalBlocked: false,
    });
  });
});
