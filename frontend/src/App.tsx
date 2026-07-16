import { useCallback, useEffect, useRef, useState } from "react";

import { api, hasToken, type GameView } from "./api/client";
import { sound } from "./audio/SoundEngine";
import { AuthModal } from "./components/AuthModal";
import { CommandInput } from "./components/CommandInput";
import { GameLog, type LogEntry } from "./components/GameLog";
import { HelpOverlay } from "./components/HelpOverlay";
import { LocationPanel } from "./components/LocationPanel";
import { MainMenu } from "./components/MainMenu";
import { PlayerPanel } from "./components/PlayerPanel";
import { SavesModal } from "./components/SavesModal";
import { SceneCanvas } from "./components/SceneCanvas";
import { SettingsPanel, loadSettings, saveSettings, type Settings } from "./components/Settings";

type Modal = "auth" | "saves" | "help" | "settings" | null;

export default function App() {
  const [settings, setSettings] = useState<Settings>(loadSettings);
  const [phase, setPhase] = useState<"menu" | "playing">("menu");
  const [view, setView] = useState<GameView | null>(null);
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [busy, setBusy] = useState(false);
  const [modal, setModal] = useState<Modal>(null);
  const [authed, setAuthed] = useState(hasToken());
  const [booting, setBooting] = useState(false);
  const [shake, setShake] = useState(false);
  const [flash, setFlash] = useState<null | "damage" | "gold">(null);
  const nextId = useRef(1);
  const ambienceRef = useRef<string>("");
  const prevHpRef = useRef<number | null>(null);

  useEffect(() => saveSettings(settings), [settings]);
  useEffect(() => {
    sound.setEnabled(settings.sound);
    if (settings.sound && view) sound.setAmbience(view.ambience as never);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settings.sound]);

  // Browsers require a user gesture before audio starts — resume on the first one.
  useEffect(() => {
    const wake = () => sound.resume();
    window.addEventListener("pointerdown", wake, { once: true });
    window.addEventListener("keydown", wake, { once: true });
    return () => {
      window.removeEventListener("pointerdown", wake);
      window.removeEventListener("keydown", wake);
    };
  }, []);

  const triggerFx = useCallback((kind: "damage" | "gold") => {
    if (kind === "damage") {
      setShake(true);
      setTimeout(() => setShake(false), 420);
    }
    setFlash(kind);
    setTimeout(() => setFlash(null), 500);
  }, []);

  const ingest = useCallback(
    (next: GameView) => {
      setView(next);
      setEntries((prev) => [
        ...prev,
        { id: nextId.current++, echo: next.echo, narration: next.narration, success: next.success },
      ]);

      // Audio: switch ambience only when it changes; fire one-shot cues.
      if (next.ambience !== ambienceRef.current) {
        ambienceRef.current = next.ambience;
        sound.setAmbience(next.ambience as never);
      }
      next.sounds.forEach((cue, i) => setTimeout(() => sound.play(cue), i * 90));

      // Visual FX: red shake when the player loses health, gold pulse on triumph.
      const prevHp = prevHpRef.current;
      prevHpRef.current = next.player.hp;
      if (prevHp !== null && next.player.hp < prevHp) triggerFx("damage");
      else if (next.sounds.includes("chime")) triggerFx("gold");
    },
    [triggerFx],
  );

  const startGame = useCallback(
    (theme: string, playerName: string) => {
      sound.resume();
      setEntries([]);
      prevHpRef.current = null;
      ambienceRef.current = "";
      setPhase("playing");
      setBooting(true);
      setBusy(true);
      setTimeout(() => setBooting(false), 1900);
      api
        .newGame(theme, undefined, playerName)
        .then(ingest)
        .catch((e) =>
          setEntries([
            { id: nextId.current++, echo: "", narration: `Could not reach the engine: ${e.message}`, success: false },
          ]),
        )
        .finally(() => setBusy(false));
    },
    [ingest],
  );

  const submit = useCallback(
    async (text: string) => {
      if (!view) return;
      sound.resume();
      setBusy(true);
      try {
        ingest(await api.command(view.session_id, text));
      } catch (e) {
        setEntries((prev) => [
          ...prev,
          { id: nextId.current++, echo: text, narration: `${(e as Error).message}`, success: false },
        ]);
      } finally {
        setBusy(false);
      }
    },
    [view, ingest],
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey && (e.key === "s" || e.key === "l")) {
        e.preventDefault();
        setModal(authed ? "saves" : "auth");
      } else if (e.key === "?" && !(e.target as HTMLElement)?.closest("input")) {
        e.preventDefault();
        setModal("help");
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [authed]);

  const flat = settings.reducedMotion;
  const loadFromModal = useCallback(
    (v: GameView) => {
      setEntries([]);
      prevHpRef.current = null;
      ambienceRef.current = "";
      setPhase("playing");
      ingest(v);
    },
    [ingest],
  );

  return (
    <div className={`room ${settings.highContrast ? "high-contrast" : ""}`}>
      <div className={`device ${flat ? "flat" : ""} ${shake && !flat ? "shake" : ""}`}>
        <div className="power-led" aria-hidden />
        <div className="screen">
          {phase === "menu" ? (
            <MainMenu
              onStart={startGame}
              onContinue={() => setModal(authed ? "saves" : "auth")}
              canContinue
            />
          ) : (
            <>
              <header className="app-header">
                <div className="title-block">
                  <span className="brand">◄ V O I D F A L L ►</span>
                  <button className="link menu-return" onClick={() => setPhase("menu")}>
                    ⏴ menu
                  </button>
                </div>
              </header>

              <main className="layout">
                {view ? (
                  <PlayerPanel view={view} onAllocate={(attr) => submit(`allocate ${attr}`)} />
                ) : (
                  <aside className="panel" />
                )}

                <div className="center">
                  <div className="viewport">
                    {view && (
                      <SceneCanvas
                        sceneKey={view.scene}
                        weather={view.weather}
                        time={view.time}
                        torchLit={view.equipped.some((i) => i.icon === "torch")}
                        reducedMotion={flat}
                        entities={view.entities}
                      />
                    )}
                    <div className="location-stamp">
                      {view?.location}
                      <span className="dim"> · {view?.time} · {view?.weather}</span>
                    </div>
                  </div>
                  <GameLog entries={entries} reducedMotion={flat} />
                  <CommandInput onSubmit={submit} disabled={busy} />
                </div>

                {view ? <LocationPanel view={view} /> : <aside className="panel" />}
              </main>

              <footer className="app-footer">
                <span>↑↓ history</span>
                <span>Tab complete</span>
                <button className="link" onClick={() => setModal(authed ? "saves" : "auth")}>
                  Ctrl+S save
                </button>
                <button className="link" onClick={() => setModal(authed ? "saves" : "auth")}>
                  Ctrl+L load
                </button>
                <button className="link" onClick={() => setModal("help")}>
                  ? help
                </button>
                <button className="link" onClick={() => setModal("settings")}>
                  ⚙ settings
                </button>
              </footer>
            </>
          )}

          {!flat && <div className="crt-scanlines" aria-hidden />}
          {!flat && <div className="crt-flicker" aria-hidden />}
          <div className="crt-glare" aria-hidden />
          <div className="crt-vignette" aria-hidden />
          {flash && <div className={`fx-flash fx-${flash}`} aria-hidden />}
          {booting && !flat && (
            <div className="boot" aria-hidden>
              <div className="boot-line" />
            </div>
          )}
        </div>
      </div>

      {modal === "auth" && (
        <AuthModal
          onClose={() => setModal(null)}
          onAuthed={() => {
            setAuthed(true);
            setModal("saves");
          }}
        />
      )}
      {modal === "saves" && (
        <SavesModal
          sessionId={view?.session_id ?? null}
          onClose={() => setModal(null)}
          onLoaded={loadFromModal}
        />
      )}
      {modal === "help" && <HelpOverlay onClose={() => setModal(null)} />}
      {modal === "settings" && (
        <SettingsPanel settings={settings} onChange={setSettings} onClose={() => setModal(null)} />
      )}
    </div>
  );
}
