import type { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/api/proxy-to-backend";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
/** Long OCR / upload streams through the edge proxy. */
export const maxDuration = 600;

type RouteContext = { params: Promise<{ path: string[] }> };

async function handle(req: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxyToBackend(req, path ?? []);
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const PATCH = handle;
export const DELETE = handle;
export const HEAD = handle;
export const OPTIONS = handle;
