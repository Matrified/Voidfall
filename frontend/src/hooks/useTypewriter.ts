import { useEffect, useRef, useState } from "react";

/**
 * Reveals `total` characters over time, returning how many are currently visible. When
 * `enabled` is false (reduced motion) it snaps straight to `total`. Restarts whenever the
 * `key` changes so each new narration types itself out.
 */
export function useTypewriter(total: number, key: unknown, enabled: boolean): number {
  const [count, setCount] = useState(enabled ? 0 : total);
  const frame = useRef<number>();

  useEffect(() => {
    if (!enabled) {
      setCount(total);
      return;
    }
    setCount(0);
    const start = performance.now();
    const cps = 220; // characters per second
    const tick = (now: number) => {
      const revealed = Math.min(total, Math.floor(((now - start) / 1000) * cps));
      setCount(revealed);
      if (revealed < total) frame.current = requestAnimationFrame(tick);
    };
    frame.current = requestAnimationFrame(tick);
    return () => {
      if (frame.current) cancelAnimationFrame(frame.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, total, enabled]);

  return count;
}
