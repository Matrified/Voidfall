/**
 * Scene painter.
 *
 * Paints a real, layered illustration to an offscreen canvas at the target pixel grid:
 * a graded sky, silhouettes with atmospheric perspective (distant shapes wash toward the
 * sky color), one dominant warm light source, and a fine grain pass. The result is then
 * turned into terminal art by the half-block renderer.
 *
 * Painters are deliberately composed from a small set of shared primitives so adding a
 * new location is a few lines, and so every scene shares a coherent lighting language.
 */

export interface Tone {
  light: number; // brightness multiplier for time of day
  sky: [string, string]; // vertical gradient stops (top, horizon)
  ambient: string; // faint wash over the whole frame
}

export function toneFor(time: string): Tone {
  switch (time) {
    case "Dawn":
      return { light: 1.0, sky: ["#3a2c3a", "#b06a4a"], ambient: "rgba(255,180,120,0.04)" };
    case "Morning":
    case "Noon":
      return { light: 1.1, sky: ["#25404a", "#6a8a90"], ambient: "rgba(180,210,220,0.03)" };
    case "Afternoon":
      return { light: 1.0, sky: ["#2a3550", "#5a6a80"], ambient: "rgba(160,170,200,0.04)" };
    case "Dusk":
      return { light: 0.88, sky: ["#241832", "#7a3a52"], ambient: "rgba(150,70,110,0.05)" };
    default: // Night / Deep Night
      return { light: 0.72, sky: ["#070a1a", "#1a2340"], ambient: "rgba(30,45,90,0.06)" };
  }
}

// --- deterministic RNG so a scene paints identically each visit -----------

function rng(seed: number) {
  let s = (seed || 1) >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

// --- shared primitives ----------------------------------------------------

function sky(ctx: Ctx, w: number, h: number, tone: Tone, horizon: number) {
  const g = ctx.createLinearGradient(0, 0, 0, h * horizon);
  g.addColorStop(0, tone.sky[0]);
  g.addColorStop(1, tone.sky[1]);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h * horizon + 1);
}

function groundFill(ctx: Ctx, w: number, h: number, y: number, top: string, bottom: string) {
  const g = ctx.createLinearGradient(0, y, 0, h);
  g.addColorStop(0, top);
  g.addColorStop(1, bottom);
  ctx.fillStyle = g;
  ctx.fillRect(0, y, w, h - y);
}

function stars(ctx: Ctx, w: number, h: number, r: () => number, count: number) {
  for (let i = 0; i < count; i++) {
    ctx.globalAlpha = 0.25 + r() * 0.6;
    ctx.fillStyle = "#dfeaff";
    ctx.fillRect(r() * w, r() * h * 0.5, 1, 1);
  }
  ctx.globalAlpha = 1;
}

/** A jagged distant ridge (mountains, rubble, treeline) with atmospheric wash. */
function ridge(ctx: Ctx, w: number, h: number, baseY: number, amp: number, color: string, r: () => number) {
  ctx.beginPath();
  ctx.moveTo(0, h);
  ctx.lineTo(0, baseY);
  let x = 0;
  while (x <= w) {
    const step = 6 + r() * 14;
    x += step;
    ctx.lineTo(x, baseY - r() * amp);
  }
  ctx.lineTo(w, h);
  ctx.closePath();
  ctx.fillStyle = color;
  ctx.fill();
}

function light(ctx: Ctx, x: number, y: number, radius: number, color: string, intensity = 1) {
  const g = ctx.createRadialGradient(x, y, 0, x, y, radius);
  g.addColorStop(0, color);
  g.addColorStop(0.35, color);
  g.addColorStop(1, "rgba(0,0,0,0)");
  ctx.globalAlpha = intensity;
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  ctx.fill();
  ctx.globalAlpha = 1;
}

function poly(ctx: Ctx, pts: [number, number][], color: string) {
  ctx.beginPath();
  ctx.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
  ctx.closePath();
  ctx.fillStyle = color;
  ctx.fill();
}

/** Subtle film grain — disabled at small sizes where it becomes corrupting noise. */
function grain(ctx: Ctx, w: number, h: number, r: () => number, amount: number) {
  if (w < 300 || h < 200) return; // skip on small source canvases (the half-block source)
  const img = ctx.getImageData(0, 0, w, h);
  const d = img.data;
  for (let i = 0; i < d.length; i += 4) {
    const n = (r() - 0.5) * amount;
    d[i] = clamp(d[i] + n);
    d[i + 1] = clamp(d[i + 1] + n);
    d[i + 2] = clamp(d[i + 2] + n);
  }
  ctx.putImageData(img, 0, 0);
}

/** A soft dark vignette that pulls the eye toward the lit center. */
function vignette(ctx: Ctx, w: number, h: number) {
  const g = ctx.createRadialGradient(w / 2, h * 0.5, h * 0.2, w / 2, h * 0.5, h * 0.85);
  g.addColorStop(0, "rgba(0,0,0,0)");
  g.addColorStop(1, "rgba(0,0,0,0.55)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h);
}

const clamp = (v: number) => (v < 0 ? 0 : v > 255 ? 255 : v);
type Ctx = CanvasRenderingContext2D;
type Painter = (ctx: Ctx, w: number, h: number, tone: Tone, r: () => number) => void;

// --- scenes ---------------------------------------------------------------

const gate: Painter = (ctx, w, h, tone, r) => {
  const hz = 0.62;
  sky(ctx, w, h, tone, hz);
  stars(ctx, w, h, r, tone.light < 0.75 ? 90 : 0);
  ridge(ctx, w, h * hz, h * 0.42, h * 0.12, "rgba(30,40,55,0.7)", r);

  const wallColor = `rgba(18,26,30,1)`;
  const wallTop = h * 0.2;
  const wallW = w * 0.62;
  const wallX = (w - wallW) / 2;
  // Curtain wall.
  ctx.fillStyle = wallColor;
  ctx.fillRect(wallX, wallTop, wallW, h - wallTop);
  // Battlements.
  for (let x = wallX; x < wallX + wallW; x += w * 0.05) ctx.fillRect(x, wallTop - h * 0.03, w * 0.03, h * 0.03);
  // Flanking towers.
  poly(ctx, [[wallX - w * 0.06, h], [wallX - w * 0.06, h * 0.12], [wallX - w * 0.02, h * 0.08], [wallX + w * 0.02, h * 0.12], [wallX + w * 0.02, h]], "rgba(14,20,24,1)");
  poly(ctx, [[wallX + wallW - w * 0.02, h], [wallX + wallW - w * 0.02, h * 0.12], [wallX + wallW + w * 0.02, h * 0.08], [wallX + wallW + w * 0.06, h * 0.12], [wallX + wallW + w * 0.06, h]], "rgba(14,20,24,1)");
  // Arch opening (dark, sky-lit rim).
  const archX = w / 2;
  const archTop = h * 0.42;
  ctx.beginPath();
  ctx.moveTo(archX - w * 0.09, h);
  ctx.lineTo(archX - w * 0.09, archTop + h * 0.08);
  ctx.quadraticCurveTo(archX, archTop, archX + w * 0.09, archTop + h * 0.08);
  ctx.lineTo(archX + w * 0.09, h);
  ctx.closePath();
  ctx.fillStyle = "rgba(6,8,12,1)";
  ctx.fill();
  // One brazier at the gate mouth — a single warm light, low and centered.
  light(ctx, archX, h * 0.82, h * 0.34, "rgba(255,150,60,0.55)", 0.9 * tone.light);
  ctx.fillStyle = "#ffcf7a";
  ctx.beginPath();
  ctx.ellipse(archX, h * 0.8, w * 0.008, h * 0.02, 0, 0, Math.PI * 2);
  ctx.fill();
  // Torn banner.
  poly(ctx, [[wallX + w * 0.06, wallTop], [wallX + w * 0.09, wallTop], [wallX + w * 0.075, wallTop + h * 0.16], [wallX + w * 0.06, wallTop + h * 0.1]], "rgba(150,40,50,0.85)");
  // Foreground: mud + a broken cart on the left.
  groundFill(ctx, w, h, h * 0.82, "rgba(20,18,14,1)", "rgba(6,6,4,1)");
  ctx.fillStyle = "rgba(28,22,14,1)";
  ctx.fillRect(w * 0.08, h * 0.82, w * 0.14, h * 0.06);
  ctx.beginPath();
  ctx.arc(w * 0.11, h * 0.9, h * 0.03, 0, Math.PI * 2);
  ctx.arc(w * 0.19, h * 0.9, h * 0.03, 0, Math.PI * 2);
  ctx.fillStyle = "rgba(14,11,7,1)";
  ctx.fill();
  vignette(ctx, w, h);
  grain(ctx, w, h, r, 16);
};

const hall: Painter = (ctx, w, h, tone, r) => {
  ctx.fillStyle = "rgba(8,12,12,1)";
  ctx.fillRect(0, 0, w, h);
  groundFill(ctx, w, h, h * 0.62, "rgba(16,20,18,1)", "rgba(5,7,6,1)");
  // Receding colonnade with perspective + depth fade.
  const vanish = w / 2;
  for (let i = 6; i >= 0; i--) {
    const t = i / 6;
    const px = vanish + (i - 3) * w * 0.14 * (1 + t);
    const colW = w * 0.05 * (1 + t);
    const top = h * 0.18 - t * h * 0.05;
    const shade = 40 - t * 22;
    ctx.fillStyle = `rgb(${shade},${shade + 6},${shade + 2})`;
    ctx.fillRect(px - colW / 2, top, colW, h * 0.7);
  }
  light(ctx, vanish, h * 0.5, h * 0.4, "rgba(255,140,50,0.4)", tone.light);
  ctx.fillStyle = "#ffcf7a";
  ctx.beginPath();
  ctx.ellipse(vanish, h * 0.48, w * 0.006, h * 0.02, 0, 0, Math.PI * 2);
  ctx.fill();
  vignette(ctx, w, h);
  grain(ctx, w, h, r, 14);
};

const crypt: Painter = (ctx, w, h, tone, r) => {
  ctx.fillStyle = "rgba(6,10,12,1)";
  ctx.fillRect(0, 0, w, h);
  for (let i = 0; i < 3; i++) {
    const x = w * (0.2 + i * 0.28);
    ctx.fillStyle = "rgba(24,28,30,1)";
    ctx.fillRect(x, h * 0.35, w * 0.1, h * 0.2);
    poly(ctx, [[x - w * 0.01, h * 0.35], [x + w * 0.05, h * 0.3], [x + w * 0.11, h * 0.35]], "rgba(30,34,36,1)");
  }
  light(ctx, w * 0.8, h * 0.28, h * 0.28, "rgba(120,255,180,0.28)", tone.light);
  // Still black water.
  const g = ctx.createLinearGradient(0, h * 0.6, 0, h);
  g.addColorStop(0, "rgba(20,40,45,1)");
  g.addColorStop(1, "rgba(4,10,12,1)");
  ctx.fillStyle = g;
  ctx.fillRect(0, h * 0.6, w, h * 0.4);
  ctx.strokeStyle = "rgba(140,200,210,0.1)";
  for (let i = 0; i < 6; i++) {
    ctx.beginPath();
    ctx.moveTo(0, h * 0.63 + i * h * 0.05);
    ctx.lineTo(w, h * 0.63 + i * h * 0.05 - 2);
    ctx.stroke();
  }
  vignette(ctx, w, h);
  grain(ctx, w, h, r, 12);
};

const forest: Painter = (ctx, w, h, tone, r) => {
  sky(ctx, w, h, tone, 0.5);
  stars(ctx, w, h, r, tone.light < 0.75 ? 70 : 0);
  ridge(ctx, w, h * 0.5, h * 0.36, h * 0.1, "rgba(20,34,26,0.8)", r);
  // Pine silhouettes, near ones darker.
  for (let i = 0; i < 12; i++) {
    const x = r() * w;
    const th = h * (0.28 + r() * 0.32);
    const near = th / h;
    const shade = 8 + near * 14;
    poly(ctx, [[x, h], [x - th * 0.28, h - th * 0.55], [x - th * 0.06, h - th * 0.55],
      [x - th * 0.2, h - th], [x, h - th * 1.12], [x + th * 0.2, h - th],
      [x + th * 0.06, h - th * 0.55], [x + th * 0.28, h - th * 0.55]],
      `rgb(${shade},${shade + 12},${shade + 4})`);
  }
  light(ctx, w * 0.55, h * 0.7, h * 0.22, "rgba(255,150,60,0.3)", tone.light);
  groundFill(ctx, w, h, h * 0.85, "rgba(14,20,12,1)", "rgba(4,8,4,1)");
  vignette(ctx, w, h);
  grain(ctx, w, h, r, 14);
};

const vault: Painter = (ctx, w, h, tone, r) => {
  ctx.fillStyle = "rgba(12,10,6,1)";
  ctx.fillRect(0, 0, w, h);
  light(ctx, w / 2, h * 0.3, h * 0.5, "rgba(255,205,110,0.32)", tone.light);
  ctx.fillStyle = "rgba(40,32,16,1)";
  ctx.fillRect(w * 0.3, h * 0.5, w * 0.4, h * 0.18);
  ctx.fillStyle = "rgba(70,56,26,1)";
  ctx.fillRect(w * 0.33, h * 0.45, w * 0.34, h * 0.05);
  // Gold glints.
  for (let i = 0; i < 30; i++) {
    ctx.fillStyle = `rgba(255,210,90,${0.3 + r() * 0.5})`;
    ctx.fillRect(w * (0.15 + r() * 0.7), h * (0.68 + r() * 0.18), 1, 1);
  }
  groundFill(ctx, w, h, h * 0.7, "rgba(24,18,8,1)", "rgba(8,6,3,1)");
  vignette(ctx, w, h);
  grain(ctx, w, h, r, 12);
};

const village: Painter = (ctx, w, h, tone, r) => {
  sky(ctx, w, h, tone, 0.55);
  ridge(ctx, w, h * 0.55, h * 0.3, h * 0.08, "rgba(30,28,32,0.7)", r);
  for (let i = 0; i < 5; i++) {
    const x = w * (0.08 + i * 0.2);
    const bw = w * 0.13;
    const bh = h * 0.28;
    ctx.fillStyle = "rgba(24,20,18,1)";
    ctx.fillRect(x, h * 0.55, bw, bh);
    poly(ctx, [[x - w * 0.01, h * 0.55], [x + bw / 2, h * 0.42], [x + bw + w * 0.01, h * 0.55]], "rgba(14,12,12,1)");
    if (r() > 0.5) light(ctx, x + bw / 2, h * 0.62, h * 0.08, "rgba(255,190,110,0.3)", tone.light);
  }
  groundFill(ctx, w, h, h * 0.82, "rgba(18,18,16,1)", "rgba(6,7,6,1)");
  vignette(ctx, w, h);
  grain(ctx, w, h, r, 14);
};

const church: Painter = (ctx, w, h, tone, r) => {
  ctx.fillStyle = "rgba(8,10,14,1)";
  ctx.fillRect(0, 0, w, h);
  // Rose window glow.
  light(ctx, w / 2, h * 0.3, h * 0.24, "rgba(180,110,255,0.3)", tone.light);
  ctx.strokeStyle = "rgba(120,90,160,0.5)";
  ctx.lineWidth = Math.max(1, w * 0.004);
  ctx.beginPath();
  ctx.arc(w / 2, h * 0.3, h * 0.16, 0, Math.PI * 2);
  ctx.stroke();
  for (let i = 0; i < 8; i++) {
    const a = (i / 8) * Math.PI * 2;
    ctx.beginPath();
    ctx.moveTo(w / 2, h * 0.3);
    ctx.lineTo(w / 2 + Math.cos(a) * h * 0.16, h * 0.3 + Math.sin(a) * h * 0.16);
    ctx.stroke();
  }
  // Columns.
  for (let i = 0; i < 5; i++) {
    ctx.fillStyle = "rgba(26,24,28,1)";
    ctx.fillRect(w * (0.14 + i * 0.18), h * 0.5, w * 0.04, h * 0.4);
  }
  groundFill(ctx, w, h, h * 0.82, "rgba(16,16,18,1)", "rgba(6,6,8,1)");
  vignette(ctx, w, h);
  grain(ctx, w, h, r, 12);
};

const clinic: Painter = (ctx, w, h, tone, r) => {
  ctx.fillStyle = "rgba(10,14,14,1)";
  ctx.fillRect(0, 0, w, h);
  light(ctx, w / 2, h * 0.2, h * 0.3, "rgba(200,220,220,0.14)", tone.light);
  for (let i = 0; i < 3; i++) {
    const x = w * (0.18 + i * 0.3);
    ctx.fillStyle = "rgba(60,20,20,1)"; // bloodstained cots
    ctx.fillRect(x, h * 0.45, w * 0.14, h * 0.2);
  }
  ctx.fillStyle = "rgba(120,30,30,0.9)"; // medical cross marks
  ctx.fillRect(w * 0.1, h * 0.15, w * 0.01, h * 0.06);
  ctx.fillRect(w * 0.085, h * 0.17, w * 0.04, h * 0.015);
  groundFill(ctx, w, h, h * 0.82, "rgba(14,16,16,1)", "rgba(5,7,7,1)");
  vignette(ctx, w, h);
  grain(ctx, w, h, r, 12);
};

const ship: Painter = (ctx, w, h, tone, r) => {
  ctx.fillStyle = "rgba(6,10,14,1)";
  ctx.fillRect(0, 0, w, h);
  light(ctx, w / 2, h * 0.3, h * 0.4, "rgba(255,60,60,0.22)", tone.light);
  ctx.fillStyle = "rgba(18,24,30,1)";
  ctx.fillRect(w * 0.1, h * 0.2, w * 0.8, h * 0.45);
  ctx.strokeStyle = "rgba(60,90,110,0.6)";
  ctx.lineWidth = Math.max(1, w * 0.003);
  for (let x = w * 0.14; x < w * 0.9; x += w * 0.06) {
    ctx.beginPath();
    ctx.moveTo(x, h * 0.2);
    ctx.lineTo(x, h * 0.65);
    ctx.stroke();
  }
  // blinking hazard strips
  ctx.fillStyle = "rgba(255,180,40,0.8)";
  ctx.fillRect(w * 0.45, h * 0.4, w * 0.1, h * 0.02);
  groundFill(ctx, w, h, h * 0.65, "rgba(14,18,22,1)", "rgba(5,7,9,1)");
  vignette(ctx, w, h);
  grain(ctx, w, h, r, 12);
};

const bridge: Painter = (ctx, w, h, tone, r) => {
  const g = ctx.createRadialGradient(w / 2, h * 0.28, 0, w / 2, h * 0.28, h * 0.7);
  g.addColorStop(0, "rgba(90,120,180,0.9)");
  g.addColorStop(1, "rgba(6,10,20,1)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h);
  light(ctx, w / 2, h * 0.28, h * 0.12, "rgba(255,235,190,0.7)", tone.light);
  // console silhouettes
  for (let i = 0; i < 4; i++) {
    ctx.fillStyle = "rgba(16,22,30,1)";
    ctx.fillRect(w * (0.16 + i * 0.2), h * 0.62, w * 0.1, h * 0.28);
  }
  groundFill(ctx, w, h, h * 0.62, "rgba(16,20,28,1)", "rgba(5,7,10,1)");
  vignette(ctx, w, h);
  grain(ctx, w, h, r, 12);
};

const shaft: Painter = (ctx, w, h, tone, r) => {
  ctx.fillStyle = "rgba(5,9,10,1)";
  ctx.fillRect(0, 0, w, h);
  for (let i = 0; i < 7; i++) {
    ctx.strokeStyle = "rgba(40,60,60,0.7)";
    ctx.lineWidth = Math.max(1, w * 0.004);
    ctx.beginPath();
    ctx.moveTo(0, h * (0.1 + i * 0.13));
    ctx.lineTo(w, h * (0.1 + i * 0.13));
    ctx.stroke();
  }
  light(ctx, w * 0.25, h * 0.5, h * 0.24, "rgba(90,255,220,0.22)", tone.light);
  light(ctx, w * 0.8, h * 0.6, h * 0.2, "rgba(255,70,70,0.18)", tone.light);
  vignette(ctx, w, h);
  grain(ctx, w, h, r, 12);
};

const PAINTERS: Record<string, Painter> = {
  gate, hall, crypt, forest, vault, village, church, clinic, ship, bridge, shaft,
};

/** Paint scene `key` onto `ctx` at `w x h` pixels. Deterministic for a given seed. */
export function paintScene(
  ctx: Ctx,
  key: string,
  w: number,
  h: number,
  tone: Tone,
  seed: number,
): void {
  (PAINTERS[key] ?? gate)(ctx, w, h, tone, rng(seed));
  // Apply the time-of-day ambient wash and a global brightness scale.
  ctx.fillStyle = tone.ambient;
  ctx.fillRect(0, 0, w, h);
}

export function seedFor(key: string): number {
  let hsh = 0;
  for (const c of key) hsh = (hsh * 31 + c.charCodeAt(0)) >>> 0;
  return hsh || 1;
}
