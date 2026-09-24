import { useMemo, useState } from "react";
import { CalendarDays, ChevronLeft, ChevronRight, Clock, MapPin } from "lucide-react";

export type CalendarEvent = {
  id: string;
  title: string;
  date: string;
  startTime?: string;
  endTime?: string;
  location?: string;
};

type CalendarWidgetProps = {
  events?: CalendarEvent[];
  onSelectDate?: (date: string) => void;
  className?: string;
};

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

const pad = (n: number) => String(n).padStart(2, "0");
const toKey = (d: Date) =>
  `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

export default function CalendarWidget({
  events = [],
  onSelectDate,
  className = "",
}: CalendarWidgetProps) {
  const today = new Date();
  const todayKey = toKey(today);

  const [viewDate, setViewDate] = useState(
    () => new Date(today.getFullYear(), today.getMonth(), 1)
  );
  const [selected, setSelected] = useState<string>(todayKey);

  const eventsByDate = useMemo(() => {
    const map = new Map<string, CalendarEvent[]>();
    for (const ev of events) {
      const list = map.get(ev.date);
      if (list) list.push(ev);
      else map.set(ev.date, [ev]);
    }
    return map;
  }, [events]);

  const grid = useMemo(() => {
    const first = new Date(viewDate.getFullYear(), viewDate.getMonth(), 1);
    const start = new Date(first);
    start.setDate(first.getDate() - first.getDay());
    return Array.from({ length: 42 }, (_, i) => {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      return d;
    });
  }, [viewDate]);

  const selectedEvents = useMemo(() => {
    const list = eventsByDate.get(selected) ?? [];
    return [...list].sort((a, b) =>
      (a.startTime ?? "").localeCompare(b.startTime ?? "")
    );
  }, [eventsByDate, selected]);

  const shiftMonth = (delta: number) =>
    setViewDate((d) => new Date(d.getFullYear(), d.getMonth() + delta, 1));

  const handleSelect = (key: string) => {
    setSelected(key);
    onSelectDate?.(key);
  };

  const monthLabel = viewDate.toLocaleString(undefined, {
    month: "long",
    year: "numeric",
  });

  return (
    <div
      className={`rounded-2xl border border-slate-200 bg-white p-4 shadow-sm ${className}`}
      style={{ color: "#1e2e40" }}
    >
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <CalendarDays className="h-5 w-5" style={{ color: "#22b4f0" }} />
          <h3 style={{ fontSize: "0.95rem", fontWeight: 700, color: "#1e2e40" }}>
            {monthLabel}
          </h3>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => shiftMonth(-1)}
            aria-label="Previous month"
            style={{ padding: "4px", borderRadius: "8px", color: "#748095" }}
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => {
              const now = new Date();
              setViewDate(new Date(now.getFullYear(), now.getMonth(), 1));
              handleSelect(toKey(now));
            }}
            style={{
              padding: "4px 8px",
              borderRadius: "8px",
              fontSize: "0.75rem",
              fontWeight: 600,
              color: "#748095",
            }}
          >
            Today
          </button>
          <button
            type="button"
            onClick={() => shiftMonth(1)}
            aria-label="Next month"
            style={{ padding: "4px", borderRadius: "8px", color: "#748095" }}
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: "4px" }}>
        {WEEKDAYS.map((d) => (
          <div
            key={d}
            style={{
              paddingBottom: "4px",
              textAlign: "center",
              fontSize: "10px",
              fontWeight: 600,
              letterSpacing: "0.05em",
              color: "#94a3b8",
              textTransform: "uppercase",
            }}
          >
            {d}
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: "4px" }}>
        {grid.map((d) => {
          const key = toKey(d);
          const inMonth = d.getMonth() === viewDate.getMonth();
          const isToday = key === todayKey;
          const isSelected = key === selected;
          const hasEvents = eventsByDate.has(key);

          return (
            <button
              key={key}
              type="button"
              onClick={() => handleSelect(key)}
              style={{
                position: "relative",
                height: "36px",
                borderRadius: "8px",
                fontSize: "0.8rem",
                border: isToday && !isSelected ? "1px solid #22b4f0" : "1px solid transparent",
                background: isSelected ? "#22b4f0" : "transparent",
                color: isSelected ? "#fff" : inMonth ? "#1e2e40" : "#cbd5e1",
                fontWeight: isSelected ? 700 : 500,
                cursor: "pointer",
              }}
            >
              {d.getDate()}
              {hasEvents && (
                <span
                  style={{
                    position: "absolute",
                    bottom: "4px",
                    left: "50%",
                    transform: "translateX(-50%)",
                    height: "4px",
                    width: "4px",
                    borderRadius: "999px",
                    background: isSelected ? "#fff" : "#22b4f0",
                  }}
                />
              )}
            </button>
          );
        })}
      </div>

      <div style={{ marginTop: "16px", borderTop: "1px solid #f1f5f9", paddingTop: "12px" }}>
        <p
          style={{
            marginBottom: "8px",
            fontSize: "0.7rem",
            fontWeight: 700,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "#94a3b8",
          }}
        >
          {selected === todayKey
            ? "Today"
            : new Date(`${selected}T00:00:00`).toLocaleDateString(undefined, {
                weekday: "short",
                month: "short",
                day: "numeric",
              })}
        </p>

        {selectedEvents.length === 0 ? (
          <p style={{ padding: "12px 0", textAlign: "center", fontSize: "0.8rem", color: "#94a3b8" }}>
            No classes scheduled
          </p>
        ) : (
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: "8px" }}>
            {selectedEvents.map((ev) => (
              <li
                key={ev.id}
                style={{
                  display: "flex",
                  gap: "8px",
                  borderRadius: "8px",
                  border: "1px solid #f1f5f9",
                  background: "#f8fafc",
                  padding: "8px",
                }}
              >
                <span style={{ width: "4px", borderRadius: "999px", background: "#22b4f0" }} />
                <div style={{ minWidth: 0 }}>
                  <p style={{ fontSize: "0.8rem", fontWeight: 600, color: "#1e2e40", margin: 0 }}>
                    {ev.title}
                  </p>
                  <div
                    style={{
                      marginTop: "2px",
                      display: "flex",
                      flexWrap: "wrap",
                      gap: "12px",
                      fontSize: "0.7rem",
                      color: "#748095",
                    }}
                  >
                    {(ev.startTime || ev.endTime) && (
                      <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
                        <Clock className="h-3 w-3" />
                        {ev.startTime}
                        {ev.endTime ? `-${ev.endTime}` : ""}
                      </span>
                    )}
                    {ev.location && (
                      <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
                        <MapPin className="h-3 w-3" />
                        {ev.location}
                      </span>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
