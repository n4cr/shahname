import { defineConfig } from "astro/config";

// When you buy the domain, update `site` to your final URL.
// If you ever host at username.github.io/shahnameh instead of a custom
// domain, also set `base: "/shahnameh"`.
export default defineConfig({
  site: "https://shahnameh.example.com",
  base: "/",
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
