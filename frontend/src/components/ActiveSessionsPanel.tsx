import { useEffect, useMemo, useState } from "react";
import "./ActiveSessionsPanel.css";

interface Props {
  entriesBySlot: Map<string, any[]>;
  days: any[];
}

type ViewMode = "class" | "teacher" | "room" | "free";

const DOW = ["SUN","MON","TUE","WED","THU","FRI","SAT"];
const DAY_NAMES = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"];

const PERIOD_TIMES = [
  { p: 1,  start: 7 * 60 + 30, end: 8 * 60 + 10 },
  { p: 2,  start: 8 * 60 + 10, end: 8 * 60 + 50 },
  { p: 3,  start: 8 * 60 + 50, end: 9 * 60 + 30 },
  { p: 4,  start: 9 * 60 + 30, end: 10 * 60 + 10 },
  { p: 5,  start: 10 * 60 + 30, end: 11 * 60 + 10 },
  { p: 6,  start: 11 * 60 + 10, end: 11 * 60 + 50 },
  { p: 7,  start: 11 * 60 + 50, end: 12 * 60 + 30 },
  { p: 8,  start: 14 * 60 + 0,  end: 14 * 60 + 40 },
  { p: 9,  start: 14 * 60 + 40, end: 15 * 60 + 20 },
  { p: 10, start: 15 * 60 + 20, end: 16 * 60 + 0 },
];

function firstText(...cands: any[]): string {
  for (const c of cands) {
    if (c === undefined || c === null) continue;
    const s = String(c).trim();
    if (s && s !== "0" && s !== "[object Object]") return s;
  }
  return "";
}
function fmtMins(n: number): string {
  const h = Math.floor(n / 60), m = n % 60;
  return String(h).padStart(2, "0") + ":" + String(m).padStart(2, "0");
}
function pullRoom(e: any): string {
  return firstText(e?.room_code, e?.roomCode, e?.room && (e.room.code || e.room.name), e?.room_name, e?.roomName);
}
function pullSubjectCode(e: any): string {
  return firstText(e?.subject_code, e?.subjectCode, e?.subject && (e.subject.code));
}
function pullSubjectName(e: any): string {
  return firstText(e?.subject_name, e?.subjectName, e?.subject && (e.subject.name));
}
function pullTeacherCode(e: any): string {
  return firstText(e?.teacher_code, e?.teacherCode, e?.employee_code,
    e?.teacher && (e.teacher.employee_code || e.teacher.code));
}
function pullTeacherName(e: any): string {
  return firstText(e?.teacher_name, e?.teacherName,
    e?.teacher && (e.teacher.name || e.teacher.full_name));
}
function pullClass(e: any): string {
  const ig = firstText(e?.instructional_group_name, e?.instructionalGroupName);
  if (ig) {
    const parts = ig.split(/\s*-\s*/);
    if (parts.length >= 2) return parts[1].trim();
    return ig;
  }
  return firstText(e?.class_code, e?.classCode, e?.class_name, e?.className) || "—";
}
function pullLearnerCount(e: any): number | null {
  const cands = [e?.learner_count, e?.learnerCount, e?.student_count, e?.studentCount];
  for (const c of cands) {
    if (typeof c === "number" && c > 0) return c;
    if (typeof c === "string") { const n = parseInt(c, 10); if (!isNaN(n) && n > 0) return n; }
  }
  return null;
}

export function ActiveSessionsPanel({ entriesBySlot, days }: Props) {
  const [tick, setTick] = useState<Date>(() => new Date());
  const [preview, setPreview] = useState<number>(0);
  const [view, setView] = useState<ViewMode>("class");
  const [daySel, setDaySel] = useState<string>("");

  useEffect(() => {
    const id = setInterval(() => setTick(new Date()), 20000);
    return () => clearInterval(id);
  }, []);

  const dow = tick.getDay();
  const isSchoolDay = dow >= 1 && dow <= 5;
  const todayCode = DOW[dow];
  const todayName = DAY_NAMES[dow];
  const mins = tick.getHours() * 60 + tick.getMinutes();

  const livePeriod = useMemo(() => {
    for (const s of PERIOD_TIMES) if (mins >= s.start && mins < s.end) return s.p;
    return 0;
  }, [mins]);
  const nextPeriod = useMemo(() => {
    for (const s of PERIOD_TIMES) if (mins < s.start) return s.p;
    return 0;
  }, [mins]);
  const showPeriod = preview || livePeriod || nextPeriod || 1;

  const dayList = Array.isArray(days) ? days : [];
  const dayCode = useMemo(() => {
    if (isSchoolDay) {
      const hit = dayList.find((d: any) => String(d?.code || d?.day || d?.name || "").toUpperCase() === todayCode);
      return hit?.code ? String(hit.code) : todayCode;
    }
    return dayList[0]?.code ? String(dayList[0].code) : "MON";
  }, [dayList, isSchoolDay, todayCode]);

  const effectiveDayCode = daySel || dayCode;

  // Free afternoons: teachers with NO assignment in periods 8-10 on effective day
  const freeAfternoon = useMemo(() => {
    if (!entriesBySlot) return { teachers: [], periodsChecked: [8, 9, 10] };
    const periods = [8, 9, 10];
    const busy = new Set<string>();
    const allTeachers = new Set<string>();
    for (const p of periods) {
      const arr = entriesBySlot.get(effectiveDayCode + ":" + p) || [];
      for (const e of arr) {
        const tc = String(e?.teacher_code ?? e?.teacherCode ?? e?.employee_code ?? "").trim();
        if (tc) busy.add(tc);
      }
    }
    // Collect every teacher who teaches on this day at all
    for (const p of [1,2,3,4,5,6,7,8,9,10]) {
      const arr = entriesBySlot.get(effectiveDayCode + ":" + p) || [];
      for (const e of arr) {
        const tc = String(e?.teacher_code ?? e?.teacherCode ?? e?.employee_code ?? "").trim();
        if (tc) allTeachers.add(tc);
      }
    }
    const free = Array.from(allTeachers).filter((t) => !busy.has(t)).sort();
    return { teachers: free, periodsChecked: periods, busy: Array.from(busy).sort() };
  }, [entriesBySlot, effectiveDayCode]);

  const entries = useMemo(() => {
    if (!entriesBySlot || !showPeriod) return [];
    const arr = entriesBySlot.get(effectiveDayCode + ":" + showPeriod);
    return Array.isArray(arr) ? arr : [];
  }, [entriesBySlot, dayCode, showPeriod]);

  // Group by class / teacher / room
  const grouped = useMemo(() => {
    const keyOf = (e: any) =>
      view === "class" ? pullClass(e) :
      view === "teacher" ? (pullTeacherCode(e) || "—") :
      (pullRoom(e) || "—");
    const map = new Map<string, { key: string; rows: any[] }>();
    for (const e of entries) {
      const k = keyOf(e);
      if (!map.has(k)) map.set(k, { key: k, rows: [] });
      map.get(k)!.rows.push({
        cls: pullClass(e),
        subjectCode: pullSubjectCode(e) || "—",
        subjectName: pullSubjectName(e) || "",
        teacherCode: pullTeacherCode(e) || "—",
        teacherName: pullTeacherName(e) || "",
        room: pullRoom(e) || "—",
        count: pullLearnerCount(e),
      });
    }
    return Array.from(map.values()).sort((a, b) => a.key.localeCompare(b.key));
  }, [entries, view]);

  const [start, end] = (() => {
    const t = PERIOD_TIMES.find((x) => x.p === showPeriod);
    return t ? [t.start, t.end] : [0, 0];
  })();
  const timeStr = tick.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const statusText = preview
    ? "PREVIEW · " + todayName + " · P" + showPeriod
    : livePeriod
      ? "LIVE · " + todayName + " · P" + livePeriod
      : "NEXT · " + todayName + " · P" + showPeriod;

  return (
    <div className="as3-panel">
      <div className="as3-header">
        <div className="as3-live">
          <span className={"as3-dot" + (livePeriod && !preview ? " is-live" : "")} />
          <span className="as3-status">{statusText}</span>
        </div>
        <div className="as3-meta">
          <span className="as3-clock">{timeStr}</span>
          <span className="as3-sep">·</span>
          <span className="as3-range">
            {fmtMins(start)}–{fmtMins(end)}<em> ({end - start}m)</em>
          </span>
        </div>
      </div>

      <div className="as3-toolbar">
        <div className="as3-tabs">
          {PERIOD_TIMES.map((t) => (
            <button key={t.p} type="button"
              className={"as3-tab" + (t.p === showPeriod ? " is-active" : "") + (t.p === livePeriod ? " is-live" : "")}
              onClick={() => setPreview(t.p === preview ? 0 : t.p)}>
              P{t.p}
            </button>
          ))}
          {preview ? (
            <button type="button" className="as3-tab as3-tab-clear" onClick={() => setPreview(0)}>⟲ auto</button>
          ) : null}
        </div>
        {(view === "free") ? (
          <div className="as3-daysel">
            <span className="as3-views-label">Day</span>
            <select value={daySel} onChange={(e) => setDaySel(e.target.value)}
              className="as3-daysel-select">
              <option value="">Auto ({todayName})</option>
              {dayList.map((d: any) => (
                <option key={d.code || d.day || d.name} value={d.code || d.day || d.name}>
                  {d.name || d.day || d.code}
                </option>
              ))}
            </select>
          </div>
        ) : null}
        <div className="as3-views">
          <span className="as3-views-label">View</span>
          {(["class","teacher","room","free"] as ViewMode[]).map((v) => (
            <button key={v} type="button"
              className={"as3-view" + (view === v ? " is-active" : "")}
              onClick={() => setView(v)}>
              {v === "class" ? "By Class" : v === "teacher" ? "By Teacher" : v === "room" ? "By Room" : "Free PM"}
            </button>
          ))}
        </div>
      </div>

      <div className="as3-stats">
        <span className="as3-stat"><b>{grouped.length}</b> {view === "class" ? "classes" : view === "teacher" ? "teachers" : "rooms"}</span>
        <span className="as3-stat"><b>{entries.length}</b> lessons</span>
      </div>

      {view === "free" ? (
        <div className="as3-free-wrap">
          <div className="as3-free-note">
            Teachers with NO assignment in <b>P8–P10</b> on <b>{effectiveDayCode}</b>.
            {freeAfternoon.teachers.length === 0
              ? " (all teachers are teaching in the afternoon)"
              : ""}
          </div>
          {freeAfternoon.teachers.length === 0 ? (
            <div className="as3-empty">No teachers are free in the afternoon.</div>
          ) : (
            <div className="as3-free-grid">
              {freeAfternoon.teachers.map((t, i) => (
                <div className="as3-free-chip" key={t} style={{ animationDelay: i * 25 + "ms" }}>
                  {t}
                </div>
              ))}
            </div>
          )}
        </div>
      ) : grouped.length === 0 ? (
        <div className="as3-empty">No sessions scheduled for {effectiveDayCode} · P{showPeriod}.</div>
      ) : (
        <div className="as3-grid">
          {grouped.map((g, gi) => (
            <div className="as3-card" key={g.key} style={{ animationDelay: gi * 35 + "ms" }}>
              <div className="as3-card-head">
                <span className="as3-key">{g.key}</span>
                <span className="as3-badge">{g.rows.length} {g.rows.length === 1 ? "lesson" : "lessons"}</span>
              </div>
              <div className="as3-rows">
                {g.rows.map((r, i) => (
                  <div className="as3-row" key={i}>
                    <div className="as3-row-main">
                      <span className="as3-subj">{r.subjectCode}</span>
                      {r.subjectName ? <span className="as3-subj-name">{r.subjectName}</span> : null}
                    </div>
                    <div className="as3-row-meta">
                      {view !== "class" ? <span className="as3-chip as3-cls">{r.cls}</span> : null}
                      {view !== "teacher" ? <span className="as3-chip as3-teach">{r.teacherCode}</span> : null}
                      {view !== "room" ? <span className="as3-chip as3-room">{r.room}</span> : null}
                      {r.count ? <span className="as3-chip as3-count">{r.count} std</span> : null}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
