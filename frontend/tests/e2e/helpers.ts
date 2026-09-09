import type { APIRequestContext, BrowserContext } from "@playwright/test";

const API = "/api/v1";

export function uniqueEmail(): string {
  return `e2e-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
}

/** Authenticate a browser context by driving the API through its cookie jar. */
export async function authenticateContext(
  context: BrowserContext,
  baseURL: string,
  displayName = "Jordan Lee",
): Promise<{ email: string; displayName: string }> {
  const email = uniqueEmail();
  const password = "supersecret123";
  const req = context.request;
  await req.post(`${baseURL}${API}/auth/register`, {
    data: { email, password, display_name: displayName },
  });
  await req.post(`${baseURL}${API}/auth/cookie/login`, {
    form: { username: email, password },
  });
  return { email, displayName };
}

export async function createDocument(
  request: APIRequestContext,
  baseURL: string,
  title = "E2E Doc",
): Promise<{ id: string; slug: string }> {
  const res = await request.post(`${baseURL}${API}/documents`, { data: { title } });
  if (!res.ok()) throw new Error(`createDocument failed: ${res.status()}`);
  return res.json();
}

export async function createShareLink(
  request: APIRequestContext,
  baseURL: string,
  documentId: string,
  role: "editor" | "viewer" = "editor",
): Promise<{ token: string; url: string }> {
  const res = await request.post(`${baseURL}${API}/documents/${documentId}/share-links`, {
    data: { role },
  });
  if (!res.ok()) throw new Error(`createShareLink failed: ${res.status()}`);
  return res.json();
}
