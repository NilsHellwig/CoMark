import "server-only";

import { cookies } from "next/headers";

export const SESSION_COOKIE = "comark_session";
export const GUEST_COOKIE = "comark_guest";

/** Cheap presence check for route guards — does NOT validate the token. */
export async function hasSessionCookie(): Promise<boolean> {
  const jar = await cookies();
  return jar.has(SESSION_COOKIE);
}

export async function hasAnyAccessCookie(): Promise<boolean> {
  const jar = await cookies();
  return jar.has(SESSION_COOKIE) || jar.has(GUEST_COOKIE);
}
