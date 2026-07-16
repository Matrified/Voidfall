import { useState } from "react";

import { api } from "../api/client";

/** A compact register/login dialog. On success it hands back the auth state. */
export function AuthModal({ onClose, onAuthed }: { onClose: () => void; onAuthed: () => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setError(null);
    setBusy(true);
    try {
      if (mode === "register") await api.register(username, password);
      await api.login(username, password);
      onAuthed();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" role="dialog" aria-label="Account" onClick={(e) => e.stopPropagation()}>
        <h2>{mode === "login" ? "Sign in" : "Create account"}</h2>
        <p className="dim small">Cloud saves let you continue on any device.</p>
        <label className="field">
          Username
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
        </label>
        <label className="field">
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submit()}
          />
        </label>
        {mode === "register" && (
          <p className="dim small">12+ chars, with upper, lower, digit, and a symbol.</p>
        )}
        {error && <p className="c-red small">{error}</p>}
        <div className="modal-actions">
          <button disabled={busy} onClick={submit}>
            {mode === "login" ? "Sign in" : "Register"}
          </button>
          <button
            className="link"
            onClick={() => setMode(mode === "login" ? "register" : "login")}
          >
            {mode === "login" ? "need an account?" : "have an account?"}
          </button>
        </div>
      </div>
    </div>
  );
}
