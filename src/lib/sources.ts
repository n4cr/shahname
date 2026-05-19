import { readdirSync, readFileSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const STORIES_DIR = resolve(__dirname, "../../stories");
const TOC_TXT = resolve(__dirname, "../../tools/pdf-extraction/toc.txt");

export interface StorySource {
  /** Three-digit id parsed from filename, e.g. "078". */
  id: string;
  /** Persian title from line 1 of the source file (may carry OCR artifacts). */
  rawTitle: string;
  /** Verse text (line 2 onward), suitable for parseVerses(). May be empty for section-heading entries. */
  versesFa: string;
  /** Number of dots in the printed TOC trailing this entry. Used as a level signal: ≥110 ≈ kingdom-level. */
  tocDots: number;
}

/**
 * Read the printed TOC to get per-entry dot counts. The PDF justifies
 * each TOC line to a column that differs by hierarchy level, so the
 * dot run is a fairly reliable level signal.
 */
function loadTocDots(): number[] {
  // Strip RTL/BiDi formatting marks before regex matching.
  const RTL = /[‎‏‪-‮⁦-⁩]/g;
  const raw = readFileSync(TOC_TXT, "utf-8");
  const out: number[] = [];
  for (const rawLine of raw.split(/\r?\n/)) {
    const line = rawLine.replace(RTL, "").trim();
    // <title> <pageNumber> <dots>
    const m = line.match(/^(.+?)(\d+)([.․]+)$/);
    if (m) out.push(m[3].length);
  }
  return out;
}

let cache: StorySource[] | null = null;

export function loadAllSources(): StorySource[] {
  if (cache) return cache;
  const dots = loadTocDots();
  const files = readdirSync(STORIES_DIR)
    .filter((f) => f.endsWith(".txt"))
    .sort();
  cache = files.map((filename, idx) => {
    const match = filename.match(/^(\d+)-(.+?)\.txt$/);
    if (!match) throw new Error(`Unexpected filename: ${filename}`);
    const id = match[1];
    const raw = readFileSync(join(STORIES_DIR, filename), "utf-8");
    const lines = raw.split(/\r?\n/);
    const rawTitle = (lines[0] ?? "").trim();
    const versesFa = lines.slice(1).join("\n").trim();
    return { id, rawTitle, versesFa, tocDots: dots[idx] ?? 0 };
  });
  return cache;
}

export function loadSource(id: string): StorySource | null {
  return loadAllSources().find((s) => s.id === id) ?? null;
}
