import { raiseRunError } from "@/lib/api/api-error";
import { browserFetch } from "@/lib/api/http";
import type { ClientProgressStepId, ClientStepLabels } from "@/lib/api/client-run-progress";
import {
  buildClientProgress,
  buildClientProgressThrough,
} from "@/lib/api/client-run-progress";
import type { RunProgress } from "@/lib/api/run-poll";

type UploadCapabilities = {
  directUploadEnabled?: boolean;
  uploadMode?: "presigned" | "api";
};

type PresignedUpload = {
  id: string;
  storageKey: string;
  fileName: string;
  mimeType: string;
  size: number;
  documentId?: string | null;
  uploadUrl?: string | null;
  method?: string;
  headers?: Record<string, string>;
};

export type StoredUploadBinding = {
  documentId: string;
  storageKey: string;
  mimeType: string;
  fileName: string;
};

type CachedUpload = StoredUploadBinding & {
  file: File;
  fingerprint: string;
};

const uploadCache = new Map<string, CachedUpload>();

export type ProgressReporter = {
  clientLabels?: ClientStepLabels;
  onProgress?: (progress: RunProgress) => void;
};

function fileFingerprint(file: File): string {
  return `${file.name}:${file.size}:${file.lastModified}`;
}

export async function fetchWithTimeout(
  input: string,
  init: RequestInit & { timeoutMs?: number } = {}
): Promise<Response> {
  const { timeoutMs = 120_000, ...rest } = init;
  if (input.startsWith("/api")) {
    return browserFetch(input.slice(4) || "/", { timeoutMs, ...rest });
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(input, { ...rest, signal: controller.signal });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error(`Request timed out after ${Math.round(timeoutMs / 1000)}s`);
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

export function raiseStepError(step: string, raw: string, status?: number): never {
  raiseRunError(raw, { step, status });
}

export function reportClientStep(
  reporter: ProgressReporter | undefined,
  stepId: ClientProgressStepId,
  detail?: string
) {
  if (!reporter?.clientLabels || !reporter.onProgress) return;
  reporter.onProgress(buildClientProgress(reporter.clientLabels, stepId, detail));
}

function cachedBindingsForRun(
  docOrder: string[],
  filesByDocId: Record<string, File>
): StoredUploadBinding[] | null {
  const bindings: StoredUploadBinding[] = [];
  for (const docId of docOrder) {
    const file = filesByDocId[docId];
    const cached = uploadCache.get(docId);
    if (
      !file ||
      !cached ||
      cached.file !== file ||
      cached.fingerprint !== fileFingerprint(file)
    ) {
      return null;
    }
    bindings.push({
      documentId: cached.documentId,
      storageKey: cached.storageKey,
      mimeType: cached.mimeType,
      fileName: cached.fileName,
    });
  }
  return bindings;
}

function rememberUploads(
  docOrder: string[],
  filesByDocId: Record<string, File>,
  bindings: StoredUploadBinding[]
) {
  for (const binding of bindings) {
    const file = filesByDocId[binding.documentId];
    if (!file) continue;
    uploadCache.set(binding.documentId, {
      ...binding,
      file,
      fingerprint: fileFingerprint(file),
    });
  }
  for (const docId of Object.keys(uploadCache)) {
    if (!docOrder.includes(docId) || !(docId in filesByDocId)) {
      uploadCache.delete(docId);
    }
  }
}

export async function getUploadCapabilities(): Promise<UploadCapabilities> {
  try {
    const res = await fetchWithTimeout("/api/uploads/capabilities", { timeoutMs: 15_000 });
    if (!res.ok) return { uploadMode: "api" };
    return (await res.json()) as UploadCapabilities;
  } catch {
    return { uploadMode: "api" };
  }
}

export async function uploadViaPresign(
  docOrder: string[],
  filesByDocId: Record<string, File>,
  reporter?: ProgressReporter
): Promise<StoredUploadBinding[]> {
  reportClientStep(reporter, "upload-check", reporter?.clientLabels?.["upload-check"].pendingDetail);

  const cached = cachedBindingsForRun(docOrder, filesByDocId);
  if (cached) {
    const names = cached.map((b) => b.fileName).join(", ");
    const reuseDetail =
      reporter?.clientLabels?.["upload-reuse"].pendingDetail?.replace("{files}", names) ??
      `Reusing storage for: ${names}`;
    if (reporter?.clientLabels && reporter.onProgress) {
      reporter.onProgress(
        buildClientProgressThrough(
          reporter.clientLabels,
          "upload-confirm",
          reuseDetail,
          "start-run"
        )
      );
    }
    return cached;
  }

  reportClientStep(reporter, "upload-presign");

  const presignRes = await fetchWithTimeout("/api/uploads/presign", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      files: docOrder.map((docId) => {
        const file = filesByDocId[docId];
        return {
          fileName: file.name,
          mimeType: file.type || "application/octet-stream",
          size: file.size,
          documentId: docId,
        };
      }),
    }),
    timeoutMs: 30_000,
  });
  if (!presignRes.ok) {
    const text = await presignRes.text();
    raiseStepError("Prepare upload", text || `HTTP ${presignRes.status}`, presignRes.status);
  }

  const { uploadMode, uploads } = (await presignRes.json()) as {
    uploadMode: "presigned" | "api";
    uploads: PresignedUpload[];
  };
  if (uploadMode !== "presigned") {
    throw new Error("presign_unavailable");
  }

  reportClientStep(
    reporter,
    "upload-transfer",
    uploads.map((u) => u.fileName).join(", ")
  );

  for (const item of uploads) {
    const docId = item.documentId ?? "";
    const file = filesByDocId[docId];
    if (!file || !item.uploadUrl) {
      raiseStepError("Upload file", `Missing upload URL for document ${docId}`);
    }
    reportClientStep(reporter, "upload-transfer", file.name);
    const putRes = await fetchWithTimeout(item.uploadUrl, {
      method: item.method ?? "PUT",
      headers: item.headers ?? { "Content-Type": item.mimeType },
      body: file,
      timeoutMs: Math.max(120_000, Math.ceil(file.size / 40_000)),
    });
    if (!putRes.ok) {
      raiseStepError(
        "Upload to storage",
        `Direct upload failed for ${file.name}: HTTP ${putRes.status}`,
        putRes.status
      );
    }
  }

  reportClientStep(reporter, "upload-confirm");

  const confirmRes = await fetchWithTimeout("/api/uploads/confirm", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      storageKeys: uploads.map((u) => u.storageKey),
    }),
    timeoutMs: 60_000,
  });
  if (!confirmRes.ok) {
    const text = await confirmRes.text();
    raiseStepError("Confirm upload", text || `HTTP ${confirmRes.status}`, confirmRes.status);
  }

  const bindings = uploads.map((item) => ({
    documentId: item.documentId ?? "",
    storageKey: item.storageKey,
    mimeType: item.mimeType,
    fileName: item.fileName,
  }));
  rememberUploads(docOrder, filesByDocId, bindings);
  return bindings;
}
