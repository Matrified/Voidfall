import { useEffect, useRef } from "react";

import { bakeHalfBlock, gridFor } from "../render/halfblock";
import { paintScene, seedFor, toneFor } from "../render/painter";
import type { EntityView } from "../api/client";

interface Props {
  sceneKey: string;
  weather: string;
  time: string;
  torchLit: boolean;
  reducedMotion: boolean;
  entities: EntityView[];
}

interface Drop {
  x: number;
  y: number;
  v: number;
  len: number;
}

/**
 * The scene renderer. On mount, it:
 * 1. Renders a fast procedural placeholder immediately (never blocks)
 * 2. Requests real AI-generated concept art from `/api/assets/scene/{key}` in the bg
 * 3. When the image arrives, re-bakes the scene from the real art (vastly higher quality)
 *
 * Both paths use the same half-block renderer, so the upgrade from procedural→real is a
 * seamless visual quality jump without layout changes.
 */
export function SceneCanvas({ sceneKey, weather, time, torchLit, reducedMotion, entities }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const wrap = wrapRef.current!;
    const canvas = canvasRef.current!;
    const ctx = canvas.getContext("2d")!;
    const tone = toneFor(time);
    const seed = seedFor(sceneKey);
    const isRainy = weather.toLowerCase() === "rain";
    const isFoggy = weather.toLowerCase() === "fog";
    const hasFlame = ["gate", "hall", "crypt", "vault", "village", "church"].includes(sceneKey);

    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    let buffer = document.createElement("canvas");
    let raf = 0;
    let drops: Drop[] = [];
    let nextBolt = 0;
    let cancelled = false;

    const bake = (sourceCanvas: HTMLCanvasElement) => {
      const rect = wrap.getBoundingClientRect();
      const w = Math.max(240, rect.width) * dpr;
      const h = Math.max(180, rect.height) * dpr;
      canvas.width = w;
      canvas.height = h;
      canvas.style.width = `${rect.width}px`;
      canvas.style.height = `${rect.height}px`;

      const grid = gridFor(w, h);
      const cellW = w / grid.cols;
      const cellH = h / grid.rows;

      // Downscale source to the exact grid the half-block renderer needs.
      const ds = document.createElement("canvas");
      ds.width = grid.cols;
      ds.height = grid.rows * 2;
      const dctx = ds.getContext("2d")!;
      dctx.imageSmoothingEnabled = true;
      dctx.imageSmoothingQuality = "high";
      dctx.drawImage(sourceCanvas, 0, 0, sourceCanvas.width, sourceCanvas.height, 0, 0, grid.cols, grid.rows * 2);

      buffer = document.createElement("canvas");
      buffer.width = w;
      buffer.height = h;
      bakeHalfBlock(ds, buffer.getContext("2d")!, grid, cellW, cellH);

      const count = isRainy ? Math.min(80, Math.floor(rect.width / 11)) : 0;
      drops = Array.from({ length: count }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        v: (7 + Math.random() * 9) * dpr,
        len: (10 + Math.random() * 16) * dpr,
      }));
    };

    const buildProcedural = () => {
      const rect = wrap.getBoundingClientRect();
      const w = Math.max(240, rect.width) * dpr;
      const h = Math.max(180, rect.height) * dpr;
      const grid = gridFor(w, h);
      const src = document.createElement("canvas");
      src.width = grid.cols;
      src.height = grid.rows * 2;
      paintScene(src.getContext("2d")!, sceneKey, grid.cols, grid.rows * 2, tone, seed);
      bake(src);
    };

    // Load real art in the background; upgrade seamlessly when it arrives.
    const loadRealArt = () => {
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.onload = () => {
        if (cancelled) return;
        const src = document.createElement("canvas");
        src.width = img.naturalWidth;
        src.height = img.naturalHeight;
        src.getContext("2d")!.drawImage(img, 0, 0);
        bake(src);
      };
      const base = (import.meta.env.VITE_API_URL ?? "/api");
      img.src = `${base}/assets/scene/${sceneKey}`;
    };

    let t = 0;
    const frame = () => {
      t += 1;
      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);

      const flick = reducedMotion ? 1 : 0.96 + 0.04 * Math.sin(t * 0.2);
      ctx.globalAlpha = flick;
      ctx.drawImage(buffer, 0, 0);
      ctx.globalAlpha = 1;

      if (hasFlame || torchLit) {
        const pulse = reducedMotion ? 0.5 : 0.5 + 0.5 * Math.sin(t * 0.15 + Math.sin(t * 0.07) * 2);
        const cx = w * 0.5;
        const cy = torchLit ? h * 0.6 : h * 0.78;
        const rad = w * (torchLit ? 0.45 : 0.3);
        const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, rad);
        g.addColorStop(0, `rgba(255,180,90,${0.04 + pulse * 0.05})`);
        g.addColorStop(1, "rgba(0,0,0,0)");
        ctx.globalCompositeOperation = "screen";
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, w, h);
        ctx.globalCompositeOperation = "source-over";
      }

      if (isFoggy) {
        const drift = reducedMotion ? 0.3 : Math.sin(t * 0.006) * 0.5 + 0.5;
        const cx = drift * w;
        const g = ctx.createLinearGradient(cx - w * 0.45, 0, cx + w * 0.45, 0);
        g.addColorStop(0, "rgba(200,210,215,0)");
        g.addColorStop(0.5, "rgba(200,210,215,0.14)");
        g.addColorStop(1, "rgba(200,210,215,0)");
        ctx.fillStyle = g;
        ctx.fillRect(0, h * 0.3, w, h * 0.5);
      }

      if (!reducedMotion && isRainy) {
        ctx.strokeStyle = "rgba(160,220,255,0.28)";
        ctx.lineWidth = 1 * dpr;
        ctx.beginPath();
        for (const d of drops) {
          ctx.moveTo(d.x, d.y);
          ctx.lineTo(d.x - d.len * 0.2, d.y + d.len);
          d.y += d.v;
          d.x -= d.v * 0.2;
          if (d.y > h) {
            d.y = -d.len;
            d.x = Math.random() * w;
          }
        }
        ctx.stroke();

        if (t > nextBolt) {
          nextBolt = t + 260 + Math.random() * 500;
        }
        const since = nextBolt - t;
        if (since > -6 && since < 0) {
          ctx.fillStyle = `rgba(200,220,255,${0.15 * (1 + since / 6)})`;
          ctx.fillRect(0, 0, w, h);
        }
      }

      // --- NPC/entity compositing: dark silhouettes at the bottom of the scene ---
      const actors = entities.filter((e) => e.note !== "item");
      if (actors.length > 0) {
        const spacing = w / (actors.length + 1);
        const figH = h * 0.22;
        const figW = figH * 0.4;
        ctx.font = `bold ${figH * 0.2}px "Cascadia Code", monospace`;
        ctx.textAlign = "center";
        ctx.textBaseline = "bottom";
        actors.forEach((actor, i) => {
          const fx = spacing * (i + 1);
          const fy = h - figH * 0.15;
          // Dark silhouette body.
          ctx.beginPath();
          ctx.ellipse(fx, fy - figH * 0.75, figW * 0.35, figH * 0.2, 0, 0, Math.PI * 2);
          ctx.fillStyle = "rgba(0,0,0,0.7)";
          ctx.fill();
          ctx.fillRect(fx - figW * 0.2, fy - figH * 0.6, figW * 0.4, figH * 0.6);
          // Colored eye/mark glow for hostile.
          const color = actor.note === "hostile" ? "rgba(255,80,60,0.9)" : "rgba(200,220,255,0.7)";
          ctx.fillStyle = color;
          ctx.fillRect(fx - figW * 0.12, fy - figH * 0.72, figW * 0.08, figW * 0.06);
          ctx.fillRect(fx + figW * 0.04, fy - figH * 0.72, figW * 0.08, figW * 0.06);
          // Name label below.
          ctx.fillStyle = color;
          ctx.fillText(actor.name, fx, h - 2);
        });
      }

      const animate = !reducedMotion && (isRainy || hasFlame || torchLit || isFoggy || actors.length > 0);
      if (animate) raf = requestAnimationFrame(frame);
    };

    buildProcedural();
    frame();
    loadRealArt(); // upgrade in background

    const ro = new ResizeObserver(() => {
      cancelAnimationFrame(raf);
      buildProcedural(); // fast re-bake on resize
      frame();
      loadRealArt(); // re-upgrade at new size
    });
    ro.observe(wrap);

    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, [sceneKey, weather, time, torchLit, reducedMotion]);

  return (
    <div className="scene-canvas-wrap" ref={wrapRef}>
      <canvas ref={canvasRef} className="scene-canvas" />
    </div>
  );
}
