/**
 * A minimal ANSI SGR parser: turns a string containing escape sequences into styled
 * segments the log can render as spans. We support the small palette the backend emits.
 */

export interface Segment {
  text: string;
  classes: string[];
}

const CODE_CLASS: Record<string, string> = {
  "1": "b",
  "2": "dim",
  "31": "c-red",
  "32": "c-green",
  "33": "c-yellow",
  "35": "c-magenta",
  "36": "c-cyan",
  "37": "c-white",
  "92": "c-bright-green",
};

const ANSI_RE = /\x1b\[([0-9;]*)m/g;

export function parseAnsi(input: string): Segment[] {
  const segments: Segment[] = [];
  let active: string[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  const push = (text: string) => {
    if (text) segments.push({ text, classes: [...active] });
  };

  ANSI_RE.lastIndex = 0;
  while ((match = ANSI_RE.exec(input)) !== null) {
    push(input.slice(lastIndex, match.index));
    const codes = match[1].split(";").filter(Boolean);
    if (codes.length === 0 || codes.includes("0")) active = [];
    for (const code of codes) {
      const cls = CODE_CLASS[code];
      if (cls && !active.includes(cls)) active.push(cls);
    }
    lastIndex = ANSI_RE.lastIndex;
  }
  push(input.slice(lastIndex));
  return segments;
}

/** Strip all ANSI codes, e.g. for measuring plain-text length. */
export function stripAnsi(input: string): string {
  return input.replace(ANSI_RE, "");
}
