import { useEffect, useRef, useState } from "react";

import type { ExitView } from "../api/client";

const ANGLES: Record<string, number> = {
  north: 0, east: 90, south: 180, west: 270,
};

/**
 * A living compass: a real needle that idly drifts like an uncalibrated instrument, then
 * settles pointing toward an available exit when you hover it. Locked ways glow red;
 * discovered destinations are named beneath. Up/down surface as separate glyphs since a
 * flat compass can't show them.
 */
export function Compass({ exits }: { exits: ExitView[] }) {
  const [angle, setAngle] = useState(37);
  const [target, setTarget] = useState<number | null>(null);
  const raf = useRef<number>();

  const horizontal = exits.filter((e) => e.direction in ANGLES);
  const vertical = exits.filter((e) => e.direction === "up" || e.direction === "down");
  const named = exits.filter((e) => e.to !== "unknown");

  // Idle drift when nothing is targeted; otherwise ease toward the target angle.
  useEffect(() => {
    let t = 0;
    const step = () => {
      t += 1;
      setAngle((prev) => {
        if (target === null) {
          return prev + Math.sin(t * 0.01) * 0.15;
        }
        let delta = target - prev;
        while (delta > 180) delta -= 360;
        while (delta < -180) delta += 360;
        return prev + delta * 0.08;
      });
      raf.current = requestAnimationFrame(step);
    };
    raf.current = requestAnimationFrame(step);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
    };
  }, [target]);

  return (
    <div className="compass">
      <div className="cmp-dial-wrap">
        <svg viewBox="0 0 100 100" className="cmp-dial">
          <circle cx="50" cy="50" r="46" className="cmp-ring" />
          <text x="50" y="12" className="cmp-tick">N</text>
          <text x="90" y="53" className="cmp-tick">E</text>
          <text x="50" y="92" className="cmp-tick">S</text>
          <text x="10" y="53" className="cmp-tick">W</text>
          {horizontal.map((e) => (
            <circle
              key={e.direction}
              cx={50 + Math.sin((ANGLES[e.direction] * Math.PI) / 180) * 40}
              cy={50 - Math.cos((ANGLES[e.direction] * Math.PI) / 180) * 40}
              r={4}
              className={e.locked ? "cmp-node cmp-node-locked" : "cmp-node cmp-node-open"}
              onMouseEnter={() => setTarget(ANGLES[e.direction])}
              onMouseLeave={() => setTarget(null)}
            />
          ))}
          <g style={{ transform: `rotate(${angle}deg)`, transformOrigin: "50px 50px" }}>
            <polygon points="50,10 44,52 50,46 56,52" className="cmp-needle-n" />
            <polygon points="50,90 44,48 50,54 56,48" className="cmp-needle-s" />
          </g>
          <circle cx="50" cy="50" r="3" className="cmp-pivot" />
        </svg>
      </div>

      {vertical.length > 0 && (
        <div className="cmp-vert">
          {vertical.map((e) => (
            <span key={e.direction} className={e.locked ? "cmp-locked" : "cmp-on"}>
              {e.direction === "up" ? "▲" : "▼"} {e.direction}
            </span>
          ))}
        </div>
      )}

      <ul className="cmp-legend">
        {named.map((e) => (
          <li key={e.direction}>
            <span className="dim">{e.direction}</span> → {e.to}
            {e.locked && <span className="c-red small"> (locked)</span>}
          </li>
        ))}
        {named.length === 0 && <li className="dim small">paths unexplored…</li>}
      </ul>
    </div>
  );
}
