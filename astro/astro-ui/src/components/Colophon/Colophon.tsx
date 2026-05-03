"use client";

import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/context/ThemeContext";
import { ENDPOINTS } from "@/lib/api/endpoints";

interface Stats {
  directives: number;
  stars: number;
  constellations: number;
  connected: boolean;
}

export function Colophon() {
  const [now, setNow] = useState(new Date());
  const [stats, setStats] = useState<Stats>({
    directives: 0,
    stars: 0,
    constellations: 0,
    connected: false,
  });
  const { theme, toggleTheme } = useTheme();
  const night = theme === "dark";

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 15000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    async function fetchStats() {
      try {
        const [dirRes, starRes, constRes] = await Promise.all([
          fetch(ENDPOINTS.DIRECTIVES),
          fetch(ENDPOINTS.STARS),
          fetch(ENDPOINTS.CONSTELLATIONS),
        ]);
        const [directives, stars, constellations] = await Promise.all([
          dirRes.json(),
          starRes.json(),
          constRes.json(),
        ]);
        setStats({
          directives: directives.length,
          stars: stars.length,
          constellations: constellations.length,
          connected: true,
        });
      } catch {
        setStats((s) => ({ ...s, connected: false }));
      }
    }
    fetchStats();
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <footer
      style={{
        display: "flex",
        alignItems: "center",
        gap: 18,
        padding: "0 20px",
        height: 28,
        borderTop: "1px solid var(--rule-1)",
        background: "var(--paper-0)",
        font: "var(--t-mono-sm)",
        color: "var(--ink-3)",
        flexShrink: 0,
      }}
    >
      <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span
          style={{
            width: 7,
            height: 7,
            borderRadius: "50%",
            background: stats.connected ? "var(--live)" : "var(--ink-4)",
          }}
        />
        <span className="breath">
          {stats.connected ? "connected" : "disconnected"}
        </span>
      </span>
      <span>{"\u00B7"}</span>
      <span>{stats.directives} directives</span>
      <span>{"\u00B7"}</span>
      <span>{stats.stars} stars</span>
      <span>{"\u00B7"}</span>
      <span>{stats.constellations} constellations</span>

      <span style={{ flex: 1 }} />

      <span>
        {now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
      </span>
      <span>{"\u00B7"}</span>
      <button
        onClick={toggleTheme}
        style={{
          background: "transparent",
          border: "none",
          color: "var(--ink-3)",
          cursor: "pointer",
          font: "inherit",
          display: "inline-flex",
          alignItems: "center",
          gap: 4,
          padding: 0,
        }}
      >
        {night ? <Moon size={13} /> : <Sun size={13} />}
        {night ? "night" : "paper"}
      </button>
    </footer>
  );
}
