import { afterEach, describe, expect, it, mock, setSystemTime } from "bun:test";

const openCredits = mock();
mock.module("@/lib/credits/dialog", () => ({ openCredits }));
mock.module("@/lib/api/browser", () => ({ $api: {} }));

const { startRun, wakeModel } = await import("./runs");

const realFetch = globalThis.fetch;

function stubFetch(fake: (...args: unknown[]) => Promise<Response>) {
  const fetchMock = mock(fake);
  globalThis.fetch = fetchMock as unknown as typeof fetch;
  return fetchMock;
}

function answer(status: number, body: unknown) {
  stubFetch(async () => new Response(JSON.stringify(body), { status }));
}

const run = {
  workflowId: "wf-1",
  documents: [{ id: "doc-1" }] as never,
  files: { "doc-1": new File(["%PDF"], "a.pdf") },
};

afterEach(() => {
  globalThis.fetch = realFetch;
  openCredits.mockClear();
});

describe("startRun", () => {
  it("opens the credits dialog when the account cannot pay (402)", async () => {
    answer(402, { detail: "Not enough credits." });
    await expect(startRun(run)).rejects.toMatchObject({ status: 402 });
    expect(openCredits).toHaveBeenCalledTimes(1);
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
    // The cooldown reads the clock (Date.now): set it rather than waiting a minute.
    const start = new Date("2026-01-01T00:00:00Z");
    setSystemTime(start);
    const fetchMock = stubFetch(async () => {
      throw new Error("offline");
    });
    wakeModel();
    wakeModel();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/model/wake", { method: "POST" });
    setSystemTime(new Date(start.getTime() + 60_000));
    wakeModel();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    setSystemTime();
  });
});
