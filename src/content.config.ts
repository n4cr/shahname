import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

const bilingual = z.object({ fa: z.string(), en: z.string() });

/**
 * Bilingual highlight metadata. Only `id`, `chapter`, `title.fa`,
 * `prose.fa`, and `versesFa` are required — everything else (image,
 * cast, pull quote, English content) is optional and unlocks features
 * incrementally.
 */
const stories = defineCollection({
  loader: glob({ pattern: "**/*.yaml", base: "./src/content/stories" }),
  schema: z.object({
    id: z.string(),
    order: z.number(),
    chapter: z.object({
      num: z.number(),
      fa: z.string(),
      en: z.string().optional(),
    }),
    title: z.object({
      fa: z.string(),
      en: z.string().optional(),
    }),
    subtitle: z
      .object({
        fa: z.string(),
        en: z.string().optional(),
      })
      .optional(),
    hero: z
      .object({
        src: z.string(),
        alt: bilingual.partial({ en: true }),
        caption: bilingual.partial({ en: true }),
      })
      .optional(),
    cast: z
      .array(
        z.object({
          fa: z.string(),
          en: z.string().optional(),
          roleFa: z.string(),
          roleEn: z.string().optional(),
        }),
      )
      .default([]),
    prose: z.object({
      fa: z.array(z.string()),
      en: z.array(z.string()).optional(),
    }),
    pullQuote: z
      .object({
        fa: z.string(),
        en: z.string().optional(),
      })
      .optional(),
    versesFa: z.string(),
  }),
});

export const collections = { stories };
