import type { CreateClientConfig } from "./generated/client.gen";

/**
 * Runtime config applied to the generated Hey API client.
 *
 * The OpenAPI paths already include the `/api/v1` prefix, so `baseUrl` is just an
 * origin: empty in the browser (same-origin; Next rewrites proxy `/api/v1` to the
 * backend), or the backend origin when rendered on the server.
 */
const baseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  (typeof window === "undefined" ? (process.env.API_URL ?? "http://localhost:8897") : "");

export const createClientConfig: CreateClientConfig = (config) => ({
  ...config,
  baseUrl,
  credentials: "include",
});
