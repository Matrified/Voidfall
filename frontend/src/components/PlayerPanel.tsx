import type { GameView } from "../api/client";
import { ItemIcon } from "../lib/icons";
import { Backpack } from "./Backpack";
import { Bar } from "./Bar";

const RARITY_CLASS: Record<string, string> = {
  common: "r-common",
  uncommon: "r-uncommon",
  rare: "r-rare",
  epic: "r-epic",
  legendary: "r-legendary",
};

const ATTRIBUTE_COMMANDS: Record<string, string> = {
  STR: "strength", DEX: "dexterity", CON: "constitution",
  INT: "intelligence", WIS: "wisdom", CHA: "charisma",
};

/** The left column: identity, vitals, attributes, inventory, and equipped gear. */
export function PlayerPanel({
  view,
  onAllocate,
}: {
  view: GameView;
  onAllocate?: (attribute: string) => void;
}) {
  const p = view.player;
  const hasGrowth = p.attribute_points > 0;

  return (
    <aside className="panel player-panel">
      <section>
        <h3 className="panel-title">Player</h3>
        <div className="player-name">{p.name}</div>
        <div className="player-level">
          LVL {p.level} <span className="dim">·······</span>
        </div>
        <Bar label="EXP" value={p.exp} max={p.exp_next} className="b-exp" />
        <Bar label="HP" value={p.hp} max={p.hp_max} className="b-hp" />
        <Bar label="MP" value={p.mp} max={p.mp_max} className="b-mp" />
        <Bar label="STA" value={p.stamina} max={p.stamina_max} className="b-sta" />
      </section>

      {hasGrowth && (
        <div className="growth-banner">
          ✦ {p.attribute_points} growth point{p.attribute_points > 1 ? "s" : ""} to spend
          — click an attribute below
        </div>
      )}

      <section className={`attributes ${hasGrowth ? "attributes-glow" : ""}`}>
        {p.attributes.map((a) => (
          <button
            key={a.name}
            className={`attr-row ${hasGrowth ? "attr-clickable" : ""}`}
            disabled={!hasGrowth}
            onClick={() => onAllocate?.(ATTRIBUTE_COMMANDS[a.name])}
            title={hasGrowth ? `Spend a point on ${ATTRIBUTE_COMMANDS[a.name]}` : undefined}
          >
            <span className="attr-name">{a.name}</span>
            <span className="attr-value">{a.value}</span>
            <span className="attr-mod dim">
              ({a.modifier >= 0 ? "+" : ""}
              {a.modifier})
            </span>
          </button>
        ))}
      </section>

      <section>
        <h3 className="panel-title">Backpack</h3>
        <Backpack items={view.inventory} />
      </section>

      {view.equipped.length > 0 && (
        <section>
          <h3 className="panel-title">Equipped</h3>
          <ul className="item-list">
            {view.equipped.map((item, i) => (
              <li key={`${item.name}-${i}`} className={RARITY_CLASS[item.rarity] ?? "r-common"}>
                <span className="item-icon">
                  <ItemIcon icon={item.icon} />
                </span>
                {item.name}
              </li>
            ))}
          </ul>
        </section>
      )}

      {view.journal.length > 0 && (
        <section>
          <h3 className="panel-title">Chronicle</h3>
          <ul className="chronicle">
            {view.journal.slice(-4).map((entry, i) => (
              <li key={i} className="dim small">
                — {entry}
              </li>
            ))}
          </ul>
        </section>
      )}
    </aside>
  );
}
