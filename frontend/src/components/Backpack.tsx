import { useState } from "react";

import type { ItemView } from "../api/client";
import { ItemIcon } from "../lib/icons";

const RARITY_CLASS: Record<string, string> = {
  common: "r-common",
  uncommon: "r-uncommon",
  rare: "r-rare",
  epic: "r-epic",
  legendary: "r-legendary",
};

const SLOT_COUNT = 16;

/** A slotted grid backpack — real inventory-game texture instead of a plain list. */
export function Backpack({ items }: { items: ItemView[] }) {
  const [hover, setHover] = useState<ItemView | null>(null);
  const slots = Array.from({ length: SLOT_COUNT }, (_, i) => items[i] ?? null);

  return (
    <div className="backpack">
      <div className="backpack-grid">
        {slots.map((item, i) => (
          <div
            key={i}
            className={`bp-slot ${item ? "bp-filled " + (RARITY_CLASS[item.rarity] ?? "") : ""}`}
            onMouseEnter={() => item && setHover(item)}
            onMouseLeave={() => setHover(null)}
          >
            {item && (
              <>
                <ItemIcon icon={item.icon} size={16} />
                {item.quantity > 1 && <span className="bp-qty">{item.quantity}</span>}
              </>
            )}
          </div>
        ))}
      </div>
      <div className="bp-tooltip">
        {hover ? (
          <>
            <span className={RARITY_CLASS[hover.rarity] ?? "r-common"}>{hover.name}</span>
            {hover.quantity > 1 && <span className="dim"> ×{hover.quantity}</span>}
          </>
        ) : (
          <span className="dim small">
            {items.length}/{SLOT_COUNT} slots
          </span>
        )}
      </div>
    </div>
  );
}
