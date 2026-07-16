/**
 * Small hand-authored ASCII portraits for NPCs and creatures. Same reasoning as scenes.ts:
 * plain authored character grids stay legible at a glance; pixel-sampling a painted face
 * down to characters produced blurry, unrecognizable blobs.
 */

export interface Portrait {
  rows: string[];
  tint: [number, number, number];
}

const GHOUL: Portrait = {
  tint: [110, 30, 40],
  rows: [
    "   .-\"\"\"-.   ",
    "  /  o o  \\  ",
    " |    ^    | ",
    " |  \\___/  | ",
    "  \\_______/  ",
  ],
};

const CORPSE: Portrait = {
  tint: [30, 15, 35],
  rows: [
    "   .-----.   ",
    "  /  x x  \\  ",
    " |    -    | ",
    " |  .....  | ",
    "  \\_______/  ",
  ],
};

const XENO: Portrait = {
  tint: [175, 45, 40],
  rows: [
    "  \\  .-.  /  ",
    "   \\/o o\\/   ",
    "   |  ^  |   ",
    "   | \\_/ |   ",
    "  /|_____|\\  ",
  ],
};

const GATEKEEPER: Portrait = {
  tint: [40, 30, 45],
  rows: [
    "   _.--.._   ",
    "  /  o o  \\  ",
    " |    -    | ",
    " |  \\___/  | ",
    "  \\_[___]_/  ",
  ],
};

const HEIR: Portrait = {
  tint: [270, 25, 45],
  rows: [
    "   .-'''-.   ",
    "  /  ~ ~  \\  ",
    " |    o    | ",
    " |  `---'  | ",
    "  \\_______/  ",
  ],
};

const STRANGER: Portrait = {
  tint: [0, 0, 42],
  rows: [
    "   .-----.   ",
    "  /  ? ?  \\  ",
    " |    ?    | ",
    " |  `---'  | ",
    "  \\_______/  ",
  ],
};

const PORTRAITS: Record<string, Portrait> = {
  ghoul: GHOUL, corpse: CORPSE, xeno: XENO,
  gatekeeper: GATEKEEPER, heir: HEIR, stranger: STRANGER,
};

/** Pick a portrait key from a free-text entity name. */
export function portraitFor(name: string): string {
  const n = name.toLowerCase();
  if (n.includes("ghoul")) return "ghoul";
  if (n.includes("corpse") || n.includes("walker") || n.includes("zombie")) return "corpse";
  if (n.includes("void") || n.includes("xeno") || n.includes("alien")) return "xeno";
  if (n.includes("gatekeeper") || n.includes("watchman")) return "gatekeeper";
  if (n.includes("heir") || n.includes("noble")) return "heir";
  return "stranger";
}

export function getPortrait(key: string): Portrait {
  return PORTRAITS[key] ?? STRANGER;
}
