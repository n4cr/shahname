/**
 * Prepend Astro's configured `base` to an absolute path.
 * Use everywhere we render an internal link or static asset URL,
 * so the site works at any base (e.g. `/shahname` on GH Pages,
 * `/` on the custom domain).
 */
export function u(path: string): string {
  const base = import.meta.env.BASE_URL.replace(/\/+$/, "");
  const tail = path.startsWith("/") ? path : `/${path}`;
  return `${base}${tail}` || "/";
}
