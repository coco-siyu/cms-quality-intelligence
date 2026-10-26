export type AdminSearch = { q?: string };

export function parseAdminSearch(search: Record<string, unknown>): AdminSearch {
  return typeof search.q === "string" && search.q.trim() ? { q: search.q } : {};
}
