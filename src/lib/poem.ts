export interface Couplet {
  first: string;
  second: string;
}

export interface Stanza {
  couplets: Couplet[];
}

/**
 * Parse a Persian poem block where each line is one couplet, the two
 * hemistichs separated by `||`, and stanza breaks are blank lines.
 */
export function parseVerses(text: string): Stanza[] {
  const stanzas: Stanza[] = [];
  let current: Couplet[] = [];

  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line) {
      if (current.length) {
        stanzas.push({ couplets: current });
        current = [];
      }
      continue;
    }
    const idx = line.indexOf("||");
    if (idx < 0) continue;
    const first = line.slice(0, idx).trim();
    const second = line.slice(idx + 2).trim();
    if (first && second) current.push({ first, second });
  }
  if (current.length) stanzas.push({ couplets: current });
  return stanzas;
}
