import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";

import { GLOSSARY, GLOSSARY_KEYS } from "@/lib/glossary";

const ROOT = resolve(__dirname, "..");
const SEARCHED = ["app", "components"];

/** Every `.ts`/`.tsx` file under the searched directories, concatenated. */
function sources(): { path: string; text: string }[] {
  const found: { path: string; text: string }[] = [];

  const walk = (dir: string) => {
    for (const entry of readdirSync(dir)) {
      const path = join(dir, entry);
      if (statSync(path).isDirectory()) walk(path);
      else if (/\.tsx?$/.test(entry)) found.push({ path, text: readFileSync(path, "utf8") });
    }
  };

  for (const dir of SEARCHED) walk(join(ROOT, dir));
  return found;
}

/**
 * Which glossary keys a body of source refers to.
 *
 * Matches the JSX prop (`term="aal"`), the caption and hint variants, and the
 * object-literal form the funnel and normalization report use.
 */
function referencedKeys(text: string): string[] {
  // exec in a loop rather than matchAll: the app targets ES5, where iterating a
  // match iterator needs downlevelIteration, and the tests share its config.
  const pattern = /\b(?:term|captionTerm|hintTerm)\s*[=:]\s*"([a-z0-9_]+)"/g;
  const keys: string[] = [];
  let match = pattern.exec(text);
  while (match) {
    keys.push(match[1]!);
    match = pattern.exec(text);
  }
  return keys;
}

describe("glossary coverage", () => {
  const files = sources();
  const referenced = new Set(files.flatMap((file) => referencedKeys(file.text)));

  /**
   * The drift guard.
   *
   * An entry nothing renders is copy that will silently rot: it is never seen,
   * so it is never corrected when the model behind it changes. Either wire it
   * to the concept it explains, or delete it.
   */
  it("renders every glossary entry somewhere in the UI", () => {
    const orphans = GLOSSARY_KEYS.filter((key) => !referenced.has(key));

    expect(orphans, `glossary entries no page uses: ${orphans.join(", ")}`).toEqual([]);
  });

  it("never points a hint at a key the glossary does not define", () => {
    const unknown = Array.from(referenced).filter((key) => !(key in GLOSSARY));

    expect(unknown, `hints referencing undefined terms: ${unknown.join(", ")}`).toEqual([]);
  });

  /** Copy lives in the glossary or it does not exist. */
  it("keeps every hint string out of the components", () => {
    const hints = GLOSSARY_KEYS.map((key) => GLOSSARY[key].hint);
    const leaked = files.filter((file) => hints.some((hint) => file.text.includes(hint)));

    expect(leaked.map((file) => file.path)).toEqual([]);
  });

  it("gives every entry a term and a hint that read as prose", () => {
    for (const key of GLOSSARY_KEYS) {
      const { term, hint } = GLOSSARY[key];
      expect(term.length, `${key} term`).toBeGreaterThan(2);
      // Long enough to explain, short enough to read in a 280px card.
      expect(hint.length, `${key} hint`).toBeGreaterThan(40);
      expect(hint.length, `${key} hint`).toBeLessThan(260);
      expect(hint.trimEnd(), `${key} hint ends in a full stop`).toMatch(/[.?]$/);
    }
  });
});
