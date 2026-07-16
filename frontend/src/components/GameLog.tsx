import { useEffect, useMemo, useRef } from "react";

import { useTypewriter } from "../hooks/useTypewriter";
import { parseAnsi, stripAnsi, type Segment } from "../lib/ansi";

export interface LogEntry {
  id: number;
  echo: string;
  narration: string;
  success: boolean;
}

function renderSegments(segments: Segment[], limit: number) {
  let remaining = limit;
  const out: JSX.Element[] = [];
  segments.forEach((seg, i) => {
    if (remaining <= 0) return;
    const text = seg.text.slice(0, remaining);
    remaining -= text.length;
    out.push(
      <span key={i} className={seg.classes.join(" ")}>
        {text}
      </span>,
    );
  });
  return out;
}

/** The scrolling narration transcript beneath the scene. */
export function GameLog({
  entries,
  reducedMotion,
}: {
  entries: LogEntry[];
  reducedMotion: boolean;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const last = entries[entries.length - 1];

  const lastSegments = useMemo(
    () => (last ? parseAnsi(last.narration) : []),
    [last],
  );
  const lastPlainLength = useMemo(
    () => (last ? stripAnsi(last.narration).length : 0),
    [last],
  );
  const revealed = useTypewriter(lastPlainLength, last?.id, !reducedMotion);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [entries, revealed]);

  return (
    <div className="scene">
      <div className="log" ref={scrollRef}>
        {entries.map((entry, index) => {
          const isLast = index === entries.length - 1;
          const segments = isLast ? lastSegments : parseAnsi(entry.narration);
          const limit = isLast ? revealed : Infinity;
          return (
            <div className="log-entry" key={entry.id}>
              {entry.echo && (
                <div className="log-echo">
                  <span className="prompt-mark">&gt;</span> {entry.echo}
                </div>
              )}
              <div className="log-narration">
                {renderSegments(segments, limit)}
                {isLast && !reducedMotion && revealed < lastPlainLength && (
                  <span className="caret">▋</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
