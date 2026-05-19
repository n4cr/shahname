import { defineConfig } from "astro/config";

// Hosted on GitHub Pages at n4cr.github.io/shahname for now.
// When the custom domain is ready: set `site` to that URL, set `base: "/"`,
// and add a `public/CNAME` file containing the bare domain.
export default defineConfig({
  site: "https://n4cr.github.io",
  base: "/shahname",
  trailingSlash: "never",
  i18n: {
    locales: ["fa", "en"],
    defaultLocale: "fa",
    routing: {
      prefixDefaultLocale: false,
    },
  },
  build: {
    format: "directory",
  },
});
