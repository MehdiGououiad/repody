import { afterEach, describe, expect, it, vi } from "vitest";

const openCredits = vi.fn();
vi.mock("@/lib/credits/dialog", () => ({ openCredits }));
vi.mock("@/lib/api/browser", () => ({ $api: {} }));

const { resetWakeCooldownForTests, startRun, wakeModel } = await import("./runs");

function answer(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(body), { status }))
  );
}

const run = {
  workflowId: "wf-1",
  documents: [{ id: "doc-1" }] as never,
  files: { "doc-1": new File(["%PDF"], "a.pdf") },
};

afterEach(() => {
  vi.unstubAllGlobals();
  openCredits.mockClear();
});

describe("startRun", () => {
  it("opens the credits dialog when the account cannot pay (402)", async () => {
    answer(402, { detail: "Not enough credits." });
    await expect(startRun(run)).rejects.toMatchObject({ status: 402 });
    expect(openCredits).toHaveBeenCalledOnce();
  });

  it("only reports other refusals", async () => {
    answer(403, { detail: "Examples are shared: duplicate this workflow to edit or run it." });
    await expect(startRun(run)).rejects.toThrow(/Examples are shared/);
    expect(openCredits).not.toHaveBeenCalled();
  });

  it("returns the run it started", async () => {
    answer(202, { runId: "run-1" });
    await expect(startRun(run)).resolves.toEqual({ runId: "run-1" });
  });
});

describe("wakeModel", () => {
  it("posts at most once per minute and ignores errors", () => {
    resetWakeCooldownForTests();
    const fetchMock = vi.fn(async () => {
      throw new Error("offline");
    });
    vi.stubGlobal("fetch", fetchMock);
    wakeModel();
    wakeModel();
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/model/wake", { method: "POST" });
  });
});
