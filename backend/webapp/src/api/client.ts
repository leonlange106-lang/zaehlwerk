// 1:1-Port des fetch-Wrappers aus dem bisherigen Vue-Frontend.
// - Relative URLs (führenden Slash entfernen) -> funktioniert direkt UND hinter
//   dem dynamischen Home-Assistant-Ingress-Basispfad.
// - Sitzungscookie (HttpOnly) via credentials mitsenden.
// - Aktive Mandanten-DB als Header X-Zaehlwerk-Database (Multi-DB-Kontext).
// - 401 zentral behandeln (zurück zur Anmeldung).

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export const ACTIVE_DB_KEY = 'active_database_id';

let unauthorizedHandler: (() => void) | null = null;
export function setUnauthorizedHandler(fn: () => void) {
  unauthorizedHandler = fn;
}

export async function api<T = unknown>(path: string, opts: RequestInit = {}): Promise<T> {
  const url = path.replace(/^\//, '');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((opts.headers as Record<string, string>) || {}),
  };
  const db = localStorage.getItem(ACTIVE_DB_KEY);
  if (db) headers['X-Zaehlwerk-Database'] = db;

  const res = await fetch(url, { credentials: 'same-origin', ...opts, headers });

  if (res.status === 401) {
    unauthorizedHandler?.();
    throw new ApiError('Sitzung abgelaufen – bitte neu anmelden', 401);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* kein JSON-Body */
    }
    throw new ApiError(detail || 'Fehler', res.status);
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

export const apiGet = <T>(path: string) => api<T>(path);
export const apiPost = <T>(path: string, body?: unknown) =>
  api<T>(path, { method: 'POST', body: body != null ? JSON.stringify(body) : undefined });
export const apiPatch = <T>(path: string, body: unknown) =>
  api<T>(path, { method: 'PATCH', body: JSON.stringify(body) });
export const apiDelete = <T>(path: string) => api<T>(path, { method: 'DELETE' });
