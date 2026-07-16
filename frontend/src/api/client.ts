/**
 * Typed client for the VOIDFALL backend.
 *
 * In development requests go to `/api/*`, which Vite proxies to FastAPI (no CORS). In
 * production set `VITE_API_URL` to the backend origin. A bearer token, once obtained, is
 * attached to authenticated calls (cloud saves, admin).
 */

const BASE = import.meta.env.VITE_API_URL ?? "/api";

export interface AttributeView {
  name: string;
  value: number;
  modifier: number;
}

export interface PlayerView {
  name: string;
  level: number;
  exp: number;
  exp_next: number;
  attribute_points: number;
  hp: number;
  hp_max: number;
  mp: number;
  mp_max: number;
  stamina: number;
  stamina_max: number;
  attributes: AttributeView[];
}

export interface ItemView {
  name: string;
  icon: string;
  rarity: string;
  quantity: number;
  equipped: boolean;
}

export interface EntityView {
  glyph: string;
  name: string;
  note: string;
}

export interface QuestView {
  name: string;
  completed: boolean;
  objectives: { text: string; done: boolean }[];
}

export interface ExitView {
  direction: string;
  to: string;
  locked: boolean;
}

export interface GameView {
  session_id: string;
  echo: string;
  narration: string;
  art: string | null;
  scene: string;
  location: string;
  time: string;
  weather: string;
  exits: ExitView[];
  ambience: string;
  sounds: string[];
  player: PlayerView;
  inventory: ItemView[];
  equipped: ItemView[];
  entities: EntityView[];
  quests: QuestView[];
  journal: string[];
  turn: number;
  success: boolean;
  code: string;
}

export interface SaveSummary {
  id: number;
  name: string;
  turn: number;
  updated_at: string;
}

let authToken: string | null = null;
export const setToken = (token: string | null) => {
  authToken = token;
};
export const hasToken = () => authToken !== null;

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (authToken) headers.set("Authorization", `Bearer ${authToken}`);
  const response = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    let detail = `${response.status}`;
    try {
      detail = (await response.json()).detail ?? detail;
    } catch {
      /* keep status */
    }
    throw new Error(String(detail));
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  // Gameplay
  newGame: (theme = "medieval", seed?: number, playerName?: string) =>
    request<GameView>("/game/new", json({ theme, seed: seed ?? null, player_name: playerName ?? null })),
  command: (sessionId: string, text: string) =>
    request<GameView>("/game/command", json({ session_id: sessionId, text })),

  // Auth
  register: (username: string, password: string) =>
    request<unknown>("/auth/register", json({ username, password })),
  login: async (username: string, password: string) => {
    const body = new URLSearchParams({ username, password });
    const res = await fetch(`${BASE}/auth/login`, { method: "POST", body });
    if (!res.ok) throw new Error("Invalid username or password");
    const data = (await res.json()) as { access_token: string };
    setToken(data.access_token);
    return data.access_token;
  },

  // Cloud saves
  listSaves: () => request<SaveSummary[]>("/saves"),
  createSave: (sessionId: string, name: string) =>
    request<SaveSummary>("/saves", json({ session_id: sessionId, name })),
  loadSave: (saveId: number) =>
    request<GameView>(`/saves/${saveId}/load`, { method: "POST" }),
  deleteSave: (saveId: number) => request<void>(`/saves/${saveId}`, { method: "DELETE" }),
};
