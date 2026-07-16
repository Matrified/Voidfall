import type { GameView } from "../api/client";
import { ItemIcon } from "../lib/icons";
import { Compass } from "./Compass";
import { NpcPortrait } from "./NpcPortrait";
import { WeatherBadge } from "./WeatherBadge";

/** The right column: location, conditions, a living compass, entities, and quests. */
export function LocationPanel({ view }: { view: GameView }) {
  const items = view.entities.filter((e) => e.note === "item");
  const actors = view.entities.filter((e) => e.note !== "item");

  return (
    <aside className="panel location-panel">
      <section>
        <h3 className="panel-title">Location</h3>
        <div className="loc-name">{view.location}</div>
        <div className="loc-cond">{view.time}</div>
        <div className="loc-cond c-cyan weather-row">
          <WeatherBadge weather={view.weather} time={view.time} />
          {view.weather}
        </div>
      </section>

      <section>
        <h3 className="panel-title">Ways</h3>
        <Compass exits={view.exits} />
      </section>

      {actors.length > 0 && (
        <section>
          <h3 className="panel-title">Present</h3>
          <div className="portrait-row">
            {actors.map((e, i) => (
              <div key={`${e.name}-${i}`} className="portrait-card">
                <NpcPortrait name={e.name} />
                <div className={e.note === "hostile" ? "c-red small" : "dim small"}>
                  {e.name}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {items.length > 0 && (
        <section>
          <h3 className="panel-title">Nearby</h3>
          <ul className="entity-list">
            {items.map((e, i) => (
              <li key={`${e.name}-${i}`}>
                <span className="entity-icon">
                  <ItemIcon icon={e.glyph} size={13} />
                </span>
                {e.name}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section>
        <h3 className="panel-title">Quests</h3>
        <ul className="quest-list">
          {view.quests.filter((q) => !q.completed).length === 0 && (
            <li className="dim small">no active quests</li>
          )}
          {view.quests
            .filter((q) => !q.completed)
            .map((q) => (
              <li key={q.name}>
                <div className="quest-name c-yellow">◆ {q.name}</div>
                <ul>
                  {q.objectives.map((o, i) => (
                    <li key={i} className={o.done ? "obj-done" : "obj"}>
                      {o.done ? "✓" : "○"} {o.text}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
        </ul>
      </section>
    </aside>
  );
}
