import { readdirSync, readFileSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const STORIES_DIR = resolve(__dirname, "../../stories");

export interface StorySource {
  /** Three-digit id parsed from filename, e.g. "078". */
  id: string;
  /** Persian title from line 1 of the source file (may carry OCR artifacts). */
  rawTitle: string;
  /** Verse text (line 2 onward), suitable for parseVerses(). May be empty for section-heading entries. */
  versesFa: string;
}

let cache: StorySource[] | null = null;

export function loadAllSources(): StorySource[] {
  if (cache) return cache;
  const files = readdirSync(STORIES_DIR)
    .filter((f) => f.endsWith(".txt"))
    .sort();
  cache = files.map((filename) => {
    const match = filename.match(/^(\d+)-(.+?)\.txt$/);
    if (!match) throw new Error(`Unexpected filename: ${filename}`);
    const id = match[1];
    const raw = readFileSync(join(STORIES_DIR, filename), "utf-8");
    const lines = raw.split(/\r?\n/);
    const rawTitle = (lines[0] ?? "").trim();
    const versesFa = lines.slice(1).join("\n").trim();
    return { id, rawTitle, versesFa };
  });
  return cache;
}

export function loadSource(id: string): StorySource | null {
  return loadAllSources().find((s) => s.id === id) ?? null;
}
