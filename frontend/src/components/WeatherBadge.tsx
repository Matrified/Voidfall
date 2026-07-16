import { CloudFog, CloudRain, Moon, Rocket, Sun } from "lucide-react";

const ICONS: Record<string, typeof CloudRain> = {
  rain: CloudRain,
  fog: CloudFog,
  clear: Sun,
  vacuum: Rocket,
};

/** A small animated weather indicator, echoing the reference's compact weather glyph. */
export function WeatherBadge({ weather, time }: { weather: string; time: string }) {
  const key = weather.toLowerCase();
  const Icon = ICONS[key] ?? Moon;
  const isNight = time === "Night" || time === "Deep Night";

  return (
    <span className={`weather-badge wx-${key}`}>
      <Icon size={15} strokeWidth={1.8} />
      {isNight && key === "clear" && <Moon size={11} className="wx-moon" strokeWidth={1.8} />}
    </span>
  );
}
