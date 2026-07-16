import { useState } from "react";

import { Castle, Rocket, Skull } from "lucide-react";

const TITLE = [
  " ██╗   ██╗ ██████╗ ██╗██████╗ ███████╗ █████╗ ██╗     ██╗",
  " ██║   ██║██╔═══██╗██║██╔══██╗██╔════╝██╔══██╗██║     ██║",
  " ██║   ██║██║   ██║██║██║  ██║█████╗  ███████║██║     ██║",
  " ╚██╗ ██╔╝██║   ██║██║██║  ██║██╔══╝  ██╔══██║██║     ██║",
  "  ╚████╔╝ ╚██████╔╝██║██████╔╝██║     ██║  ██║███████╗███████╗",
  "   ╚═══╝   ╚═════╝ ╚═╝╚═════╝ ╚═╝     ╚═╝  ╚═╝╚══════╝╚══════╝",
];

interface Scenario {
  id: string;
  title: string;
  tagline: string;
  Icon: typeof Castle;
  accent: string;
}

const SCENARIOS: Scenario[] = [
  {
    id: "medieval",
    title: "The Fall of Greyhelm",
    tagline: "A rain-drowned keep, a lost heir, a debt owed to the dead.",
    Icon: Castle,
    accent: "#7fe0a3",
  },
  {
    id: "undead",
    title: "The Hollow Harvest",
    tagline: "A plague village where the dead refuse to lie still.",
    Icon: Skull,
    accent: "#c98bff",
  },
  {
    id: "starship",
    title: "The Derelict Aurora",
    tagline: "A silent starship, a severed distress call, something aboard.",
    Icon: Rocket,
    accent: "#5fb3ff",
  },
];

/** Title screen. Choose a story to begin; each builds a different world. */
export function MainMenu({
  onStart,
  onContinue,
  canContinue,
}: {
  onStart: (theme: string, playerName: string) => void;
  onContinue: () => void;
  canContinue: boolean;
}) {
  const [name, setName] = useState("");

  return (
    <div className="menu">
      <pre className="menu-title">{TITLE.join("\n")}</pre>
      <div className="menu-sub">NATURAL LANGUAGE RPG ENGINE</div>

      <div className="name-entry">
        <label className="dim small">Your name</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="wanderer"
          spellCheck={false}
          autoComplete="off"
          className="name-input"
        />
      </div>

      <div className="menu-prompt">— choose your story —</div>
      <div className="scenario-grid">
        {SCENARIOS.map((s) => (
          <button
            key={s.id}
            className="scenario-card"
            style={{ ["--accent" as string]: s.accent }}
            onClick={() => onStart(s.id, name.trim() || "wanderer")}
          >
            <s.Icon size={40} strokeWidth={1.4} className="scenario-icon" />
            <div className="scenario-title">{s.title}</div>
            <div className="scenario-tag">{s.tagline}</div>
            <div className="scenario-go">▸ begin</div>
          </button>
        ))}
      </div>

      <div className="menu-footer">
        {canContinue && (
          <button className="link menu-continue" onClick={onContinue}>
            ⏵ continue last session
          </button>
        )}
        <span className="dim small">type plain English · the engine is the world</span>
      </div>
    </div>
  );
}
