import "server-only";

import { cache } from "react";
import { unwrap } from "@/lib/api/openapi-client";
import { serverApi } from "@/lib/api/openapi-server";

/** Server Components - per-request cached platform config. */
export const fetchPlatformConfigServer = cache(() => unwrap(serverApi.GET("/v1/platform/config")));
