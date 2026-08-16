// Shared fetch helpers for the Feyti API. Calls are same-origin relative
// paths, proxied server-side by Next.js rewrites to the internal backend
// (see next.config.ts). Set NEXT_PUBLIC_API_URL only to bypass the proxy.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL?.trim().replace(/\/$/, "") ?? "";

export function getApiUrl(path: string) {
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

export async function readErrorMessage(response: Response) {
  try {
    const payload = (await response.json()) as { detail?: string };
    if (payload.detail) return payload.detail;
  } catch {
    // Fall back to a generic error when the proxy returns a non-JSON response.
  }
  return `Request failed with status ${response.status}.`;
}

/** JSON GET/POST/PUT with a typed result; throws the backend's detail message on failure. */
export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(getApiUrl(path), init);
  if (!res.ok) throw new Error(await readErrorMessage(res));
  return (await res.json()) as T;
}

export function apiJson(path: string, method: "POST" | "PUT", body: unknown) {
  return apiFetch(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

export async function downloadFromApi(path: string, filename: string) {
  const res = await fetch(getApiUrl(path));
  if (!res.ok) throw new Error(await readErrorMessage(res));
  downloadBlob(await res.blob(), filename);
}

/** Build a dossier-scoped API path: /api/v1/dossiers/{dossierId}/... */
export function dossierApi(dossierId: string, path: string) {
  return `/api/v1/dossiers/${encodeURIComponent(dossierId)}${path.startsWith("/") ? path : `/${path}`}`;
}

/** Build a /d/[dossierId]/structure/[...path] link for a document. */
export function workspaceHref(dossierId: string, sectionPath: string, stem: string) {
  const encoded = sectionPath.split("/").map(encodeURIComponent).join("/");
  return `/d/${encodeURIComponent(dossierId)}/structure/${encoded}?stem=${encodeURIComponent(stem)}`;
}

/** Reverse of workspaceHref's path part: catch-all route segments → section_path. */
export function sectionPathFromSegments(segments: string[]) {
  return segments.map((s) => decodeURIComponent(s)).join("/");
}
