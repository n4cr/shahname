import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

const bilingual = z.object({ fa: z.string(), en: z.string() });

const stories = defineCollection({
  loader: glob({ pattern: "**/*.yaml", base: "./src/content/stories" }),
  schema: z.object({
    id: z.string(),
    slug: z.string(),
    order: z.number(),
    chapter: z.object({
      num: z.number(),
      fa: z.string(),
      en: z.string(),
    }),
    title: bilingual,
    subtitle: bilingual,
    hero: z
      .object({
        src: z.string(),
        alt: bilingual,
        caption: bilingual,
      })
      .optional(),
    cast: z
      .array(
        z.object({
          fa: z.string(),
          en: z.string(),
          roleFa: z.string(),
          roleEn: z.string(),
        }),
      )
      .default([]),
    prose: z.object({
      fa: z.array(z.string()),
      en: z.array(z.string()),
    }),
    pullQuote: bilingual.optional(),
    versesFa: z.string(),
  }),
});

export const collections = { stories };
