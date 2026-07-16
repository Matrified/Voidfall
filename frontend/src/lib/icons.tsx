/**
 * Maps semantic item/entity keys to real vector icons (lucide-react). The backend sends a
 * key like "sword" or "key"; the UI resolves it to a crisp SVG glyph — no emoji.
 */
import {
  Coins,
  FlaskRound,
  Flame,
  KeyRound,
  type LucideIcon,
  Package,
  ScrollText,
  Shield,
  Shirt,
  Skull,
  Sparkles,
  Sword,
  User,
} from "lucide-react";

const ITEM_ICONS: Record<string, LucideIcon> = {
  sword: Sword,
  shield: Shield,
  potion: FlaskRound,
  key: KeyRound,
  torch: Flame,
  coin: Coins,
  armor: Shirt,
  scroll: ScrollText,
  relic: Sparkles,
  generic: Package,
};

export function ItemIcon({ icon, size = 14 }: { icon: string; size?: number }) {
  const Icon = ITEM_ICONS[icon] ?? Package;
  return <Icon size={size} className="lucide" strokeWidth={1.75} aria-hidden />;
}

export function EntityIcon({ hostile, size = 14 }: { hostile: boolean; size?: number }) {
  const Icon = hostile ? Skull : User;
  return <Icon size={size} className="lucide" strokeWidth={1.75} aria-hidden />;
}
