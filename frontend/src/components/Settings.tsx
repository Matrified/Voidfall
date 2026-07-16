/**
 * Player-facing display settings, persisted to localStorage. These are presentation-only
 * toggles; nothing here affects the authoritative engine.
 */

export interface Settings {
  reducedMotion: boolean;
  highContrast: boolean;
  sound: boolean;
}

const KEY = "voidfall.settings";
// Bump this whenever a default changes, so a stale save from an older build (e.g. one
// where sound defaulted to off) doesn't silently override the new intended default.
const SETTINGS_VERSION = 2;

const DEFAULTS: Settings = {
  reducedMotion: false,
  highContrast: false,
  sound: true,
};

export function loadSettings(): Settings {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return DEFAULTS;
    const parsed = JSON.parse(raw) as Partial<Settings> & { __v?: number };
    if (parsed.__v !== SETTINGS_VERSION) return DEFAULTS; // stale shape/defaults -> reset
    return { ...DEFAULTS, ...parsed };
  } catch {
    return DEFAULTS;
  }
}

export function saveSettings(settings: Settings): void {
  try {
    localStorage.setItem(KEY, JSON.stringify({ ...settings, __v: SETTINGS_VERSION }));
  } catch {
    /* storage may be unavailable; settings simply won't persist */
  }
}

interface Props {
  settings: Settings;
  onChange: (settings: Settings) => void;
  onClose: () => void;
}

export function SettingsPanel({ settings, onChange, onClose }: Props) {
  const toggle = (key: keyof Settings) => onChange({ ...settings, [key]: !settings[key] });

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" role="dialog" aria-label="Settings" onClick={(e) => e.stopPropagation()}>
        <h2>Settings</h2>
        <label className="check">
          <input
            type="checkbox"
            checked={settings.reducedMotion}
            onChange={() => toggle("reducedMotion")}
          />
          Reduced motion (disables typewriter, scanlines, glow)
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={settings.highContrast}
            onChange={() => toggle("highContrast")}
          />
          High contrast
        </label>
        <label className="check">
          <input type="checkbox" checked={settings.sound} onChange={() => toggle("sound")} />
          Sound effects
        </label>
        <button className="modal-close" onClick={onClose}>
          close
        </button>
      </div>
    </div>
  );
}
