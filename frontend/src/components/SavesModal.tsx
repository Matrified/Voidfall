import { useEffect, useState } from "react";

import { api, type GameView, type SaveSummary } from "../api/client";

/** Lists cloud saves for the signed-in user; supports save, load, and delete. */
export function SavesModal({
  sessionId,
  onClose,
  onLoaded,
}: {
  sessionId: string | null;
  onClose: () => void;
  onLoaded: (view: GameView) => void;
}) {
  const [saves, setSaves] = useState<SaveSummary[]>([]);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const refresh = () => api.listSaves().then(setSaves).catch((e) => setError(e.message));
  useEffect(() => {
    refresh();
  }, []);

  const save = async () => {
    if (!sessionId || !name.trim()) return;
    try {
      await api.createSave(sessionId, name.trim());
      setName("");
      refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const load = async (id: number) => {
    try {
      onLoaded(await api.loadSave(id));
      onClose();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" role="dialog" aria-label="Cloud saves" onClick={(e) => e.stopPropagation()}>
        <h2>Cloud Saves</h2>
        <div className="save-new">
          <input
            placeholder="name this save…"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && save()}
          />
          <button onClick={save} disabled={!sessionId || !name.trim()}>
            save
          </button>
        </div>
        {error && <p className="c-red small">{error}</p>}
        <ul className="save-list">
          {saves.length === 0 && <li className="dim">no saves yet</li>}
          {saves.map((s) => (
            <li key={s.id}>
              <span className="save-name">{s.name}</span>
              <span className="dim small">turn {s.turn}</span>
              <button className="link" onClick={() => load(s.id)}>
                load
              </button>
              <button
                className="link c-red"
                onClick={() => api.deleteSave(s.id).then(refresh)}
              >
                delete
              </button>
            </li>
          ))}
        </ul>
        <button className="modal-close" onClick={onClose}>
          close
        </button>
      </div>
    </div>
  );
}
