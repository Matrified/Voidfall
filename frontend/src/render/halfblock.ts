/**
 * Half-block ANSI renderer.
 *
 * This is the technique real terminal image viewers (chafa, timg, viu) use to render
 * full-color pictures with characters, and it is what makes VOIDFALL's scenes look like a
 * painting rendered through a terminal rather than ASCII noise.
 *
 * Each character cell renders TWO stacked pixels: the upper half-block glyph "▀" is drawn
 * in the *top* pixel's color, and the cell background is filled with the *bottom* pixel's
 * color. With 24-bit ("truecolor") color per half, one row of characters encodes two rows
 * of full-color pixels — doubling vertical resolution and preserving color completely,
 * which a brightness→character ramp cannot do.
 *
 * The scene is baked to an offscreen buffer exactly once per scene/resize; animation is
 * layered on top as cheap primitives, so this stays comfortably real-time.
 */

const UPPER_HALF = "\u2580"; // ▀

export interface HalfBlockGrid {
  cols: number;
  rows: number;
}

/**
 * Choose a character grid that keeps the source image's aspect ratio roughly square on
 * screen while staying within a performance budget.
 */
export function gridFor(displayWidth: number, displayHeight: number): HalfBlockGrid {
  const TARGET_CELL_PX = 7; // on-screen size of one character cell
  const cols = Math.max(80, Math.min(200, Math.round(displayWidth / TARGET_CELL_PX)));
  const cellW = displayWidth / cols;
  const rows = Math.max(40, Math.min(120, Math.round(displayHeight / cellW)));
  return { cols, rows };
}

/**
 * Bake a source image (sized `cols x rows*2` pixels) into the target context as half-block
 * characters. `cellW`/`cellH` are in device pixels; call once, then animate over the top.
 */
export function bakeHalfBlock(
  source: HTMLCanvasElement,
  target: CanvasRenderingContext2D,
  grid: HalfBlockGrid,
  cellW: number,
  cellH: number,
): void {
  const { cols, rows } = grid;
  const sctx = source.getContext("2d", { willReadFrequently: true })!;
  const data = sctx.getImageData(0, 0, cols, rows * 2).data;

  target.textBaseline = "top";
  target.textAlign = "left";
  target.font = `${cellH * 1.08}px "Cascadia Code", "Fira Code", monospace`;

  for (let y = 0; y < rows; y++) {
    const py = y * cellH;
    for (let x = 0; x < cols; x++) {
      const top = ((2 * y) * cols + x) * 4;
      const bottom = ((2 * y + 1) * cols + x) * 4;
      const px = x * cellW;

      // Bottom pixel becomes the cell background.
      target.fillStyle = `rgb(${data[bottom]},${data[bottom + 1]},${data[bottom + 2]})`;
      target.fillRect(px, py, cellW + 0.75, cellH + 0.75);

      // Top pixel is painted with the upper half-block glyph.
      target.fillStyle = `rgb(${data[top]},${data[top + 1]},${data[top + 2]})`;
      target.fillText(UPPER_HALF, px, py);
    }
  }
}
