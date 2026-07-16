/**
 * Local, zero-latency autocomplete over the verbs and directions the parser understands.
 * The engine remains the source of truth; this is purely a typing convenience.
 */

const VOCABULARY = [
  "look", "examine", "inventory", "wait",
  "go", "walk", "north", "south", "east", "west", "up", "down",
  "take", "get", "drop",
  "equip", "wield", "unequip",
  "attack", "hit",
];

/** Return the completions whose leading characters match the current word. */
export function complete(partial: string): string[] {
  const word = partial.trimStart().split(/\s+/).pop() ?? "";
  if (!word) return [];
  return VOCABULARY.filter((v) => v.startsWith(word.toLowerCase()) && v !== word).slice(0, 10);
}
