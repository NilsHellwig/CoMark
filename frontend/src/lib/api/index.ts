export * from "./generated";
export * from "./generated/@tanstack/react-query.gen";
export { client } from "./generated/client.gen";

/** True when a Hey API result carries a non-2xx response. */
export function failed(result: { error?: unknown; response?: Response }): boolean {
  return !result.response || !result.response.ok || result.error != null;
}

export function errorMessage(
  result: { error?: unknown } | { detail?: unknown } | unknown,
  fallback = "Something went wrong",
): string {
  const err = (result as { error?: { detail?: unknown }; detail?: unknown }) ?? {};
  const detail =
    err.error && typeof err.error === "object"
      ? (err.error as { detail?: unknown }).detail
      : err.detail;
  if (typeof detail === "string") return detail;
  if (
    Array.isArray(detail) &&
    detail[0] &&
    typeof detail[0] === "object" &&
    "msg" in detail[0]
  ) {
    return String((detail[0] as { msg: unknown }).msg);
  }
  return fallback;
}
