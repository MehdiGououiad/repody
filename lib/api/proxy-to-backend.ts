import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { backendOrigin } from "@/lib/api/backend-origin";

/** Headers that must not be forwarded hop-to-hop. */
const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
  "host",
  "content-length",
]);

function filterRequestHeaders(source: Headers): Headers {
  const headers = new Headers();
  source.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) {
      headers.set(key, value);
    }
  });
  return headers;
}

function filterResponseHeaders(source: Headers): Headers {
  const headers = new Headers();
  source.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (HOP_BY_HOP.has(lower)) return;
    // Let the edge set its own encoding / length for the proxied body.
    if (lower === "content-encoding") return;
    headers.set(key, value);
  });
  return headers;
}

/**
 * Runtime reverse-proxy to FastAPI. Uses INTERNAL_API_URL / BACKEND_URL at
 * request time so the same web image works on Compose (`http://api:8000`) and
 * Kubernetes (`http://repody-api:8000`) without baked next.config rewrites.
 */
export async function proxyToBackend(
  req: NextRequest,
  pathSegments: string[]
): Promise<NextResponse> {
  const origin = backendOrigin();
  const suffix = pathSegments.join("/");
  const target = new URL(`${origin}/v1/${suffix}`);
  target.search = req.nextUrl.search;

  const headers = filterRequestHeaders(req.headers);
  const method = req.method.toUpperCase();
  const hasBody = method !== "GET" && method !== "HEAD";

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method,
      headers,
      body: hasBody ? req.body : undefined,
      // Required by undici when streaming a request body.
      ...(hasBody ? ({ duplex: "half" } as RequestInit) : {}),
      cache: "no-store",
      redirect: "manual",
    });
  } catch (err) {
    const detail = err instanceof Error ? err.message : "upstream fetch failed";
    return NextResponse.json(
      {
        detail: `API unreachable at ${origin}: ${detail}`,
      },
      { status: 502 }
    );
  }

  return new NextResponse(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: filterResponseHeaders(upstream.headers),
  });
}
