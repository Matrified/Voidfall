/**
 * A fully procedural sound engine built on the Web Audio API — no audio files, no
 * licensing. It produces two things:
 *
 *   • Ambience beds that loop and cross-fade: rain, wind, and a cavern drone.
 *   • One-shot SFX reacting to the story: hits, discoveries, footsteps, chimes, errors.
 *
 * Everything is synthesized from oscillators and filtered noise, so it is tiny, instant,
 * and infinitely reusable. The browser requires a user gesture before audio may play, so
 * call `resume()` from a click/keypress.
 */

type Ambience = "rain" | "wind" | "cave" | "none";

export class SoundEngine {
  private ctx: AudioContext | null = null;
  private master: GainNode | null = null;
  private noise: AudioBuffer | null = null;

  private ambienceKey: Ambience = "none";
  private ambienceNodes: AudioNode[] = [];
  private ambienceGain: GainNode | null = null;
  private dripTimer: number | null = null;

  private enabled = false;

  // -- lifecycle ---------------------------------------------------------

  private ensure(): AudioContext {
    if (!this.ctx) {
      this.ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
      this.master = this.ctx.createGain();
      this.master.gain.value = 0.35;
      this.master.connect(this.ctx.destination);
      this.noise = this.makeNoise(this.ctx);
    }
    return this.ctx;
  }

  resume() {
    if (this.enabled) this.ensure().resume();
  }

  setEnabled(on: boolean) {
    this.enabled = on;
    if (!on) {
      this.stopAmbience();
      this.ctx?.suspend();
    } else {
      this.ensure().resume();
      this.setAmbience(this.ambienceKey);
    }
  }

  private makeNoise(ctx: AudioContext): AudioBuffer {
    const len = ctx.sampleRate * 2;
    const buffer = ctx.createBuffer(1, len, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    let last = 0;
    for (let i = 0; i < len; i++) {
      // Brown-ish noise: smoother, less harsh than white.
      const white = Math.random() * 2 - 1;
      last = (last + 0.02 * white) / 1.02;
      data[i] = last * 3.5;
    }
    return buffer;
  }

  private noiseSource(ctx: AudioContext): AudioBufferSourceNode {
    const src = ctx.createBufferSource();
    src.buffer = this.noise;
    src.loop = true;
    return src;
  }

  // -- ambience ----------------------------------------------------------

  setAmbience(key: Ambience) {
    this.ambienceKey = key;
    if (!this.enabled) return;
    const ctx = this.ensure();
    this.stopAmbience();
    if (key === "none") return;

    const gain = ctx.createGain();
    gain.gain.value = 0;
    gain.connect(this.master!);
    this.ambienceGain = gain;

    if (key === "rain") {
      const src = this.noiseSource(ctx);
      const bp = ctx.createBiquadFilter();
      bp.type = "bandpass";
      bp.frequency.value = 1400;
      bp.Q.value = 0.6;
      src.connect(bp).connect(gain);
      src.start();
      this.ambienceNodes = [src, bp];
      gain.gain.linearRampToValueAtTime(0.5, ctx.currentTime + 1.2);
    } else if (key === "wind") {
      const src = this.noiseSource(ctx);
      const lp = ctx.createBiquadFilter();
      lp.type = "lowpass";
      lp.frequency.value = 500;
      const lfo = ctx.createOscillator();
      const lfoGain = ctx.createGain();
      lfo.frequency.value = 0.08;
      lfoGain.gain.value = 260;
      lfo.connect(lfoGain).connect(lp.frequency);
      src.connect(lp).connect(gain);
      src.start();
      lfo.start();
      this.ambienceNodes = [src, lp, lfo, lfoGain];
      gain.gain.linearRampToValueAtTime(0.3, ctx.currentTime + 1.5);
    } else if (key === "cave") {
      const drone = ctx.createOscillator();
      drone.type = "sine";
      drone.frequency.value = 58;
      const droneGain = ctx.createGain();
      droneGain.gain.value = 0.25;
      drone.connect(droneGain).connect(gain);
      drone.start();
      this.ambienceNodes = [drone, droneGain];
      gain.gain.linearRampToValueAtTime(0.4, ctx.currentTime + 1.5);
      // Occasional water drips.
      const scheduleDrip = () => {
        if (this.ambienceKey !== "cave") return;
        this.drip();
        this.dripTimer = window.setTimeout(scheduleDrip, 2500 + Math.random() * 4000);
      };
      this.dripTimer = window.setTimeout(scheduleDrip, 1500);
    }
  }

  private stopAmbience() {
    if (this.dripTimer) {
      clearTimeout(this.dripTimer);
      this.dripTimer = null;
    }
    const gain = this.ambienceGain;
    const nodes = this.ambienceNodes;
    this.ambienceNodes = [];
    this.ambienceGain = null;
    if (gain && this.ctx) {
      gain.gain.cancelScheduledValues(this.ctx.currentTime);
      gain.gain.linearRampToValueAtTime(0, this.ctx.currentTime + 0.4);
    }
    setTimeout(() => {
      nodes.forEach((n) => {
        try {
          (n as OscillatorNode).stop?.();
        } catch {
          /* already stopped */
        }
        n.disconnect();
      });
      gain?.disconnect();
    }, 500);
  }

  private drip() {
    const ctx = this.ctx!;
    const osc = ctx.createOscillator();
    const g = ctx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(900, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(400, ctx.currentTime + 0.12);
    g.gain.setValueAtTime(0.0001, ctx.currentTime);
    g.gain.exponentialRampToValueAtTime(0.12, ctx.currentTime + 0.01);
    g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.25);
    osc.connect(g).connect(this.master!);
    osc.start();
    osc.stop(ctx.currentTime + 0.3);
  }

  // -- one-shot SFX ------------------------------------------------------

  play(cue: string) {
    if (!this.enabled) return;
    this.ensure();
    switch (cue) {
      case "hit":
        this.burst(140, 0.18, "square", 0.28);
        this.noiseHit(0.2);
        break;
      case "defeat":
        this.sweep(320, 60, 0.6);
        break;
      case "unlock":
        this.metalClank();
        break;
      case "footstep":
        this.noiseHit(0.08, 300);
        break;
      case "pickup":
        this.blip(520, 780, 0.12);
        break;
      case "discover":
        this.arp([523, 784], 0.12);
        break;
      case "chime":
        this.arp([523, 659, 784, 1046], 0.14);
        break;
      case "ui_error":
        this.burst(90, 0.18, "sawtooth", 0.18);
        break;
      case "intro":
        this.arp([196, 262, 330, 392], 0.35);
        break;
      case "type":
      default:
        this.blip(320, 360, 0.03);
        break;
    }
  }

  private tone(freq: number, dur: number, type: OscillatorType, vol: number, at = 0) {
    const ctx = this.ctx!;
    const t0 = ctx.currentTime + at;
    const osc = ctx.createOscillator();
    const g = ctx.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.exponentialRampToValueAtTime(vol, t0 + 0.008);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    osc.connect(g).connect(this.master!);
    osc.start(t0);
    osc.stop(t0 + dur + 0.02);
  }

  private burst(freq: number, dur: number, type: OscillatorType, vol: number) {
    this.tone(freq, dur, type, vol);
  }

  private blip(from: number, to: number, dur: number) {
    const ctx = this.ctx!;
    const osc = ctx.createOscillator();
    const g = ctx.createGain();
    osc.type = "triangle";
    osc.frequency.setValueAtTime(from, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(to, ctx.currentTime + dur);
    g.gain.setValueAtTime(0.0001, ctx.currentTime);
    g.gain.exponentialRampToValueAtTime(0.12, ctx.currentTime + 0.006);
    g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + dur);
    osc.connect(g).connect(this.master!);
    osc.start();
    osc.stop(ctx.currentTime + dur + 0.02);
  }

  private sweep(from: number, to: number, dur: number) {
    const ctx = this.ctx!;
    const osc = ctx.createOscillator();
    const g = ctx.createGain();
    osc.type = "sawtooth";
    osc.frequency.setValueAtTime(from, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(to, ctx.currentTime + dur);
    g.gain.setValueAtTime(0.22, ctx.currentTime);
    g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + dur);
    osc.connect(g).connect(this.master!);
    osc.start();
    osc.stop(ctx.currentTime + dur + 0.02);
  }

  private arp(freqs: number[], step: number) {
    freqs.forEach((f, i) => this.tone(f, step * 1.6, "triangle", 0.16, i * step));
  }

  private metalClank() {
    // A key turning: two detuned metallic clicks, then a brief rust screech.
    const ctx = this.ctx!;
    [1180, 880].forEach((f, i) => {
      const osc = ctx.createOscillator();
      const g = ctx.createGain();
      osc.type = "square";
      osc.frequency.value = f;
      const t0 = ctx.currentTime + i * 0.09;
      g.gain.setValueAtTime(0.0001, t0);
      g.gain.exponentialRampToValueAtTime(0.14, t0 + 0.005);
      g.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.08);
      osc.connect(g).connect(this.master!);
      osc.start(t0);
      osc.stop(t0 + 0.1);
    });
    // Rust screech: a filtered sawtooth sweep with noise.
    const t = ctx.currentTime + 0.18;
    const saw = ctx.createOscillator();
    const bp = ctx.createBiquadFilter();
    const g = ctx.createGain();
    saw.type = "sawtooth";
    saw.frequency.setValueAtTime(320, t);
    saw.frequency.linearRampToValueAtTime(520, t + 0.35);
    bp.type = "bandpass";
    bp.frequency.value = 2200;
    bp.Q.value = 6;
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(0.09, t + 0.05);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.38);
    saw.connect(bp).connect(g).connect(this.master!);
    saw.start(t);
    saw.stop(t + 0.4);
  }

  private noiseHit(vol: number, cutoff = 1200) {
    const ctx = this.ctx!;
    const src = this.noiseSource(ctx);
    const lp = ctx.createBiquadFilter();
    lp.type = "lowpass";
    lp.frequency.value = cutoff;
    const g = ctx.createGain();
    g.gain.setValueAtTime(vol, ctx.currentTime);
    g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.18);
    src.connect(lp).connect(g).connect(this.master!);
    src.start();
    src.stop(ctx.currentTime + 0.2);
  }
}

export const sound = new SoundEngine();
