import { getPortrait, portraitFor } from "../scenes/portraits";

/** A small, hand-authored ASCII face — talking to someone has a face, cheaply. */
export function NpcPortrait({ name }: { name: string }) {
  const portrait = getPortrait(portraitFor(name));
  const [h, s, l] = portrait.tint;
  return (
    <pre
      className="npc-portrait"
      style={{ color: `hsl(${h} ${s}% ${l}%)` }}
      title={name}
    >
      {portrait.rows.join("\n")}
    </pre>
  );
}
