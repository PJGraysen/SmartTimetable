import { useSearchParams } from "react-router-dom";
import { useCallback, useEffect, useMemo, useState, useRef } from "react";
import { useAuth } from "../auth/AuthContext";
import { Printer, RefreshCw } from "lucide-react";
import {
  getSchedulingRunResults,
  getSchedulingRuns,
  createSchedulingRun,
  executeSchedulingRun,
  pollRunUntilDone,
  type SchedulingRun,
  type TimetableEntryResult,
} from "../services/scheduling";
import { ActiveSessionsPanel } from "../components/ActiveSessionsPanel";

type TimetableColumn = {
  key: string;
  label: string;
  time: string;
  kind: "lesson" | "tea" | "lunch" | "prayers" | "activities";
  period?: number;
};

type ClassDefinition = {
  code?: string;
  name?: string;
  label: string;
  aliases: string[];
};

type DayDefinition = {
  code: string;
  label: string;
};

const DAYS: DayDefinition[] = [
  { code: "MON", label: "MONDAY" },
  { code: "TUE", label: "TUESDAY" },
  { code: "WED", label: "WEDNESDAY" },
  { code: "THU", label: "THURSDAY" },
  { code: "FRI", label: "FRIDAY" },
];

const CLASSES: ClassDefinition[] = [
  {
    label: "Form 4E",
    aliases: ["form 4e", "form 4 east", "f4 east", "4e", "f4e"],
  },
  {
    label: "Form 4W",
    aliases: ["form 4w", "form 4 west", "f4 west", "4w", "f4w"],
  },
  {
    label: "G11E",
    aliases: ["grade 11e", "grade 11 east", "11e", "11 east", "grade11e", "g11e"],
  },
  {
    label: "G11W",
    aliases: ["grade 11w", "grade 11 west", "11w", "11 west", "grade11w", "g11w"],
  },
  {
    label: "Grade 10E",
    aliases: ["grade 10e", "grade 10 east", "10e", "10 east", "grade10e", "g10e"],
  },
  {
    label: "Grade 10W",
    aliases: ["grade 10w", "grade 10 west", "10w", "10 west", "grade10w", "g10w"],
  },
  {
    label: "Grade 9E",
    aliases: ["grade 9e", "grade 9 east", "9e", "9 east", "grade9e", "g9e"],
  },
];

// Canonical teacher codes/names. Any entry whose teacher_code or
// teacher_name doesn't match this list is normalised against it before
// being shown in the roster, so a single teacher never appears twice.
const CANONICAL_TEACHERS: Array<{ code: string; name: string }> = [
  { code: "T001",   name: "Fr. Rector" },
  { code: "T002",   name: "Fr. Samuel" },
  { code: "T003",   name: "Fr. Mburu" },
  { code: "T004",   name: "Mr. Wanjohi" },
  { code: "T005",   name: "Mr. Magothe" },
  { code: "T006",   name: "Mr. Ogilo" },
  { code: "T007",   name: "Madam Prisca" },
  { code: "T008",   name: "Ms. Ndeta" },
  { code: "T009",   name: "Mr. Omanga" },
  { code: "T010",   name: "Ms. Kinyua" },
  { code: "T011",   name: "Mr. Nyaga" },
  { code: "T012",   name: "Mr. Wamalwa" },
  { code: "T013",   name: "Sis. Felistas" },
  { code: "T014",   name: "Ms. Erambi" },
  { code: "T015",   name: "Madam Maryann" },
  { code: "T016",   name: "Mr. Osano" },
  { code: "T017",   name: "Mr. Baraza" },
  { code: "T018",   name: "Mr. Namuye" },
  { code: "T019",   name: "Mr. Peter" },
  { code: "T020",   name: "Ms. Wainaina" },
  { code: "LAB001", name: "Lab Technician" },
];
const CANON_BY_CODE = new Map(CANONICAL_TEACHERS.map((t) => [t.code.toUpperCase(), t]));
const CANON_BY_NAME = new Map(CANONICAL_TEACHERS.map((t) => [t.name.toLowerCase(), t]));

const COLUMNS: TimetableColumn[] = [
  {
    key: "p1",
    label: "P1",
    time: "08:00â€“08:40",
    kind: "lesson",
    period: 1,
  },
  {
    key: "p2",
    label: "P2",
    time: "08:40â€“09:20",
    kind: "lesson",
    period: 2,
  },
  {
    key: "p3",
    label: "P3",
    time: "09:20â€“10:00",
    kind: "lesson",
    period: 3,
  },
  {
    key: "p4",
    label: "P4",
    time: "10:00â€“10:40",
    kind: "lesson",
    period: 4,
  },
  {
    key: "tea",
    label: "TEA",
    time: "10:40â€“11:00",
    kind: "tea",
  },
  {
    key: "p5",
    label: "P5",
    time: "11:00â€“11:40",
    kind: "lesson",
    period: 6,
  },
  {
    key: "p6",
    label: "P6",
    time: "11:40â€“12:20",
    kind: "lesson",
    period: 7,
  },
  {
    key: "p7",
    label: "P7",
    time: "12:20â€“13:00",
    kind: "lesson",
    period: 8,
  },
  {
    key: "lunch",
    label: "LUNCH",
    time: "13:00â€“14:00",
    kind: "lunch",
  },
  {
    key: "p8",
    label: "P8",
    time: "14:00â€“14:40",
    kind: "lesson",
    period: 10,
  },
  {
    key: "p9",
    label: "P9",
    time: "14:40â€“15:20",
    kind: "lesson",
    period: 11,
  },
  {
    key: "p10",
    label: "P10",
    time: "15:20â€“16:00",
    kind: "lesson",
    period: 12,
  },
  {
    key: "prayers",
    label: "PRAYERS",
    time: "16:00â€“16:30",
    kind: "prayers",
  },
  {
    key: "activities",
    label: "ACTIVITIES",
    time: "16:30â€“17:45",
    kind: "activities",
  },
];

// Defensive: cap rendered lesson columns at 10. If a stale
// state ever produces an exploded COLUMNS array, this prevents
// html2canvas from generating a >1000-column PDF capture.
function _startMinute(t: string): number {
  const m = t.match(/(\d{1,2}):(\d{2})/);
  if (!m) return 999999;
  return parseInt(m[1], 10) * 60 + parseInt(m[2], 10);
}

const COLUMNS_SAFE: TimetableColumn[] = (() => {
  const lessons = COLUMNS.filter((c) => c.kind === "lesson").slice(0, 10);
  const others = COLUMNS.filter((c) => c.kind !== "lesson");
  return [...lessons, ...others].sort(
    (a, b) => _startMinute(a.time) - _startMinute(b.time)
  );
})();

// --- Compact day / class labels for space-saving headers ---
function shortDayLabel(value: string | null | undefined): string {
  if (!value) return "";
  const key = String(value).toUpperCase().trim();
  return ({
    "MONDAY": "MON", "MON": "MON",
    "TUESDAY": "TUE", "TUE": "TUE",
    "WEDNESDAY": "WED", "WED": "WED",
    "THURSDAY": "THU", "THUR": "THU", "THU": "THU",
    "FRIDAY": "FRI", "FRI": "FRI",
  } as Record<string, string>)[key] ?? value;
}

function shortClassLabel(value: string | null | undefined): string {
  if (!value) return "";
  const key = String(value).trim();
  return ({
    "Form 4E": "F4E", "Form 4W": "F4W",
    "Grade 10E": "G10E", "Grade 10W": "G10W",
    "Grade 8E": "G8E", "Grade 8W": "G8W",
    "Grade 9E": "G9E", "Grade 9W": "G9W",
  } as Record<string, string>)[key] ?? value;
}




/* ============================================================
   LIVE NOW  -  active sessions panel
   ============================================================ */
const AS_DEFAULT_PERIODS = [
  { label: "P1", start: "07:30", end: "08:10" },
  { label: "P2", start: "08:10", end: "08:50" },
  { label: "P3", start: "08:50", end: "09:30" },
  { label: "P4", start: "09:30", end: "10:10" },
  { label: "P5", start: "10:30", end: "11:10" },
  { label: "P6", start: "11:10", end: "11:50" },
  { label: "P7", start: "11:50", end: "12:30" },
  { label: "P8", start: "14:00", end: "14:40" },
  { label: "P9", start: "14:40", end: "15:20" },
  { label: "P10", start: "15:20", end: "16:00" },
];

function asToMin(s: any) {
  if (!s && s !== 0) return null;
  const m = String(s).match(/(\d{1,2})[:.](\d{1,2})/);
  if (!m) return null;
  return parseInt(m[1], 10) * 60 + parseInt(m[2], 10);
}

function asPeriodRange(p: any) {
  if (!p || typeof p !== "object") return [null, null];
  const s = asToMin(p.start ?? p.start_time ?? p.from ?? p.time_start ?? p.begin);
  const e = asToMin(p.end ?? p.end_time ?? p.to ?? p.time_end ?? p.finish);
  return [s, e];
}

function asKeyMatchesDayPeriod(key: any, di: any, pi: any, dayNames: any, periodLabels: any) {
  const k = String(key);
  const kl = k.toLowerCase();
  const nums = k.match(/\d+/g) || [];
  if (nums.length >= 2) {
    const a = parseInt(nums[0] || '0', 10), b = parseInt(nums[1], 10);
    if ((a === di && b === pi) || (a === pi && b === di)) return true;
  }
  const dn = String(dayNames?.[di] ?? "").toLowerCase().slice(0, 3);
  if (dn && !kl.includes(dn)) return false;
  const pl = String(periodLabels?.[pi] ?? "").toLowerCase();
  if (pl && !kl.includes(pl)) return false;
  return dn.length > 0 || pl.length > 0;
}

function asPullEntryFields(e: any) {
  if (!e) return null;
  const cls =
    e.class_name || e.className || e.class_code || e.classCode ||
    (e.klass && (e.klass.name || e.klass.code)) ||
    (e.class && (e.class.name || e.class.code)) || "";
  const subj =
    e.subject_code || e.subjectCode ||
    (e.subject && (e.subject.code || e.subject.name)) ||
    e.subject_name || e.subjectName ||
    (typeof formatLesson === "function" ? (() => {
      try { const l = formatLesson(e); return l.code || l.name || ""; } catch { return ""; }
    })() : "") || "";
  const teacher =
    e.teacher_code || e.teacherCode ||
    (e.teacher && (e.teacher.code || e.teacher.name)) ||
    e.teacher_name || e.teacherName || "";
  let room = "";
  try { room = typeof roomCode === "function" ? roomCode(e) : ""; } catch {}
  return { cls, subj, teacher, room, id: e.id };
}


function normalise(value: unknown): string {
  return String(value ?? "")
    .toLowerCase()
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function text(value: unknown): string {
  if (typeof value === "string") {
    return value.trim();
  }

  if (typeof value === "number") {
    return String(value);
  }

  return "";
}

function normalisedSubjectCode(entry: TimetableEntryResult): string {
  return text(entry.subject_code);
}

function subjectName(entry: TimetableEntryResult): string {
  return text(entry.subject_name);
}

function teacherCode(entry: TimetableEntryResult): string {
  return text(entry.teacher_code) || text(entry.employee_code);
}

function displayTeacherCode(entry: TimetableEntryResult): string {
  // Prefer the entry's own teacher. The block DTO carries ALL
  // members of the block; using it here would (a) combine every
  // block teacher into one string and (b) prevent per-teacher
  // filtering since a single teacher code never matches the
  // combined string. Only fall back to the block when the entry
  // itself has no primary teacher.
  const raw = entry as unknown as Record<string, unknown>;
  const own =
    teacherCode(entry) ||
    text(raw.teacher_number) ||
    text(raw.teacherNumber);
  if (own) return own;
  const block = entry.block ?? null;
  if (block) {
    if (!block.has_any_teacher) return "";
    return block.members
      .map((m: any) => m.teacher_code ?? "-")
      .join(" / ");
  }
  return "";
}

const ROOM_ALIASES = {
  "computer science lab": "CSLAB",
  "computer lab": "CSLAB",
  "computer laboratory": "CSLAB",
  "cs lab": "CSLAB",
  "chemistry lab": "ChemLab",
  "chemistry laboratory": "ChemLab",
  "chem lab": "ChemLab",
  "physics lab": "PhyLab",
  "physics laboratory": "PhyLab",
  "phys lab": "PhyLab",
  "biology lab": "BioLab",
  "biology laboratory": "BioLab",
  "bio lab": "BioLab",
  "science lab": "SciLab",
  "language lab": "LangLab",
  "multimedia lab": "MMLab",
  "computer room": "CSLAB",
  "library": "LIB",
  "staff room": "Staff",
  "auditorium": "AUD",
  "gymnasium": "GYM",
  "gym": "GYM",
  "phy-lab": "PhyLab",
  "chem/bio lab": "ChemLab",
  "biochem laboratory": "ChemLab",
  "lab1": "CSLAB",
  "bdrm": "Board",
  "board-room": "Board",
  "dhl": "Dining",
  "dining hall": "Dining",
  "f4e": "RM 4E",
  "f4w": "RM 4W",
  "f3e": "RM 3E",
  "f3w": "RM 3W",
  "g10e": "RM 10E",
  "g10w": "RM 10W",
  "g9e": "RM 9E",
  "g9w": "RM 9W",
  "g8e": "RM 8E",
  "g8w": "RM 8W",
};

function pickRoomName(x: any) {
  if (x === undefined || x === null) return "";
  if (typeof x === "string") return x;
  if (typeof x === "number") return x === 0 ? "" : String(x);
  if (typeof x !== "object") return String(x);
  const cands = [
    x.room_code, x.roomCode,
    x.room && typeof x.room === "object" && x.room.code,
    x.room_name, x.roomName,
    x.room && typeof x.room === "object" && (x.room.name || x.room.label),
    x.room_label, x.roomLabel,
    x.room_id_name,
    typeof x.room === "string" ? null : x.room,
  ];
  for (const c of cands) {
    if (c === undefined || c === null) continue;
    if (typeof c === "object") {
      const inner = c.name || c.label || c.code;
      if (inner !== undefined && inner !== null && String(inner).trim() !== "") return String(inner);
      continue;
    }
    const s = String(c).trim();
    if (s && s !== "0") return s;
  }
  return "";
}

function roomCode(x: any) {
  const raw = pickRoomName(x).trim();
  if (!raw) return "\u2014";
  const lower = raw.toLowerCase();
  const JUNK = new Set([
    "0","null","undefined","tba","n/a","na","-","none",
    "unassigned","no room","nan","[object object]"
  ]);
  if (JUNK.has(lower)) return "\u2014";
  if (typeof ROOM_ALIASES !== "undefined" && (ROOM_ALIASES as Record<string, string>)[lower]) return (ROOM_ALIASES as Record<string, string>)[lower];
  const rmm = raw.match(/^(?:room|rm|r)[\s.\-]*(\S+)$/i);
  if (rmm) return "RM " + rmm[1].toUpperCase();
  if (raw.length <= 7) return raw.toUpperCase();
  const words = raw.split(/\s+/).filter(Boolean);
  if (words.length >= 2) {
    const initials = words.map(w => w[0]).join("").toUpperCase();
    if (initials.length <= 5) return initials;
  }
  return raw.replace(/\s+/g, "").slice(0, 6).toUpperCase();
}

function teacherName(entry: TimetableEntryResult): string {
  return text(entry.teacher_name);
}

function groupName(entry: TimetableEntryResult): string {
  // Prefer the authoritative instructional_group_code field.
  // Falling back to the display name only when the code is absent.
  const raw = entry as unknown as Record<string, unknown>;
  const code = raw.instructional_group_code;
  if (typeof code === "string" && code.trim()) {
    return code.trim();
  }
  return text(entry.instructional_group_name);
}

function canonicalDayCode(entry: TimetableEntryResult): string {
  const raw = normalise(entry.day || entry.day_display);

  if (raw === "mon" || raw === "monday") {
    return "MON";
  }

  if (raw === "tue" || raw === "tuesday" || raw === "tues") {
    return "TUE";
  }

  if (raw === "wed" || raw === "wednesday") {
    return "WED";
  }

  if (
    raw === "thu" ||
    raw === "thursday" ||
    raw === "thur" ||
    raw === "thurs"
  ) {
    return "THU";
  }

  if (raw === "fri" || raw === "friday") {
    return "FRI";
  }

  return raw.toUpperCase();
}

function periodNumber(entry: TimetableEntryResult): number {
  const value = Number(entry.period_number);
  return Number.isFinite(value) ? value : 0;
}

function classMatches(
  entry: TimetableEntryResult,
  definition: ClassDefinition,
): boolean {
  const group = normalise(groupName(entry));

  if (!group) {
    return false;
  }

  // Exact match only. Substring fallback previously caused
  // cross-group leakage (e.g. an 11W entry appearing under 10W)
  // when the aliases shared substrings.
  return definition.aliases.some((alias) => {
    const candidate = normalise(alias);
    return group === candidate;
  });
}

function electiveLabel(entry: TimetableEntryResult): string {
  const raw = entry as unknown as Record<string, unknown>;

  const candidates = [
    raw.elective_option,
    raw.electiveOption,
    raw.option,
    raw.option_name,
    raw.optionName,
    raw.elective_block,
    raw.electiveBlock,
    raw.pathway,
    raw.pathway_name,
    raw.pathwayName,
  ];

  for (const candidate of candidates) {
    const value = text(candidate);

    if (value) {
      return value;
    }
  }

  const requirement = text(entry.lesson_requirement_name);

  const optionMatch = requirement.match(
    /\b(option\s*[1-4]|elective\s*(?:option\s*)?[1-4])\b/i,
  );

  return optionMatch ? optionMatch[1] : "";
}

const GRADE10_ELECTIVE_BLOCKS: Record<string, string[]> = {
  "OPTION 1": ["BIO", "MUS", "FRE"],
  "OPTION 2": ["CHEM", "PHY", "LIT"],
  "OPTION 3": ["GEO", "HIS", "CS"],
  "OPTION 4": ["BUS", "AGR"],
};

function electiveSubjectCode(entry: TimetableEntryResult): string {
  const code = normalisedSubjectCode(entry).toUpperCase();
  const name = normalise(subjectName(entry));

  if (code === "BIO" || name === "biology") {
    return "BIO";
  }

  if (code === "MUS" || name === "music") {
    return "MUS";
  }

  if (code === "FRE" || name === "french") {
    return "FRE";
  }

  if (code === "CHEM" || code === "CHE" || name === "chemistry") {
    return "CHEM";
  }

  if (code === "PHY" || name === "physics") {
    return "PHY";
  }

  if (code === "LIT" || name === "literature" || name === "english literature") {
    return "LIT";
  }

  if (code === "GEO" || name === "geography") {
    return "GEO";
  }

  if (code === "HIST" || code === "HIS" || name === "history") {
    return "HIS";
  }

  if (code === "CS" || code === "COMPUTER STUDIES" || name === "computer studies" || name === "computer science") {
    return "CS";
  }

  if (code === "BUS" || name === "business" || name === "business studies") {
    return "BUS";
  }

  if (code === "AGRI" || code === "AGR" || name === "agriculture") {
    return "AGR";
  }

  return code;
}

function electiveBlockForSubject(subjectCode: string): string[] | null {
  const code = text(subjectCode).toUpperCase();

  for (const subjects of Object.values(GRADE10_ELECTIVE_BLOCKS)) {
    if (subjects.includes(code)) {
      return subjects;
    }
  }

  return null;
}

function formatLesson(entry: TimetableEntryResult) {
  const block = entry.block ?? null;
  if (block) {
    const teacherDisplay = block.has_any_teacher
      ? block.members.map((m: any) => m.teacher_code ?? "-").join(" / ")
      : "";
    return {
      code: block.display,
      name: block.display,
      teacher: teacherDisplay,
      teacherName: "",
      elective: block.code,
    };
  }
  return {
    code: normalisedSubjectCode(entry),
    name: subjectName(entry),
    teacher: teacherCode(entry),
    teacherName: teacherName(entry),
    elective: electiveLabel(entry),
  };
}

function completedRuns(runs: SchedulingRun[]): SchedulingRun[] {
  return [...runs]
    .filter((run) => {
      const status = normalise(run.status);

      return (
        status === "completed" ||
        status === "complete" ||
        status === "success" ||
        status === "successful"
      );
    })
    .sort((a, b) => {
      const left = Date.parse(a.completed_at || a.created_at || "");
      const right = Date.parse(b.completed_at || b.created_at || "");

      return right - left;
    });
}

function cellClass(column: TimetableColumn): string {
  if (column.kind === "tea") {
    return "tt-cell tt-break tt-tea";
  }

  if (column.kind === "lunch") {
    return "tt-cell tt-break tt-lunch";
  }

  if (column.kind === "prayers") {
    return "tt-cell tt-break tt-prayers";
  }

  if (column.kind === "activities") {
    return "tt-cell tt-break tt-activities";
  }

  return "tt-cell";
}

// --- PDF/PNG export: force React render flush before capture ---
// html2canvas fires synchronously and can snapshot the DOM before React
// commits a fresh render. Double requestAnimationFrame guarantees the
// browser has painted the latest tree. Added to fix intermittent
// phantom-column and stale-cell captures.
async function waitForRenderFlush(): Promise<void> {
  await new Promise<void>((resolve) =>
    requestAnimationFrame(() => requestAnimationFrame(() => resolve()))
  );
  await Promise.resolve();
}
// --- end flush helper ---

function Timetable() {
  const [entries, setEntries] = useState<TimetableEntryResult[]>([]);
  const [version, setVersion] = useState("Live timetable");
  const [activeTermId, setActiveTermId] = useState<string>("");
  const [loadedAt, setLoadedAt] = useState<Date | null>(null);
  const [runCompletedAt] = useState<string | null>(null);
  const [availableRuns, setAvailableRuns] = useState<any[]>([]);
  const [entrySignature, setEntrySignature] = useState<string>("");
  const { role: _ttRole } = useAuth();
  const isStudentView = _ttRole === "STUDENT";
  const [changedKeys, setChangedKeys] = useState<Set<string>>(new Set());
  const [highlightOn, setHighlightOn] = useState(true);
  const [changesSummary, setChangesSummary] = useState<{
    total: number;
    byDay: Record<string, number>;
    samples: string[];
  } | null>(null);
  const prevEntryMapRef = useRef<Map<string, string> | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string>("");
  // True once the user explicitly picks a run from the dropdown.
  // While true, the 6-second auto-poller must NOT switch back to newest.
  const userPickedRef = useRef<boolean>(false);
  const [schoolName] = useState<string>("Queen of Apostles Seminary Senior School");
  const [termDisplay, setTermDisplay] = useState<string>("");
  const [searchParams] = useSearchParams();

  // Canonical teacher table: teacher_id -> { code, name }.
  // Fetched once from the backend so the roster is immune to
  // denormalised teacher_code / teacher_name drift in entries.
  const [teacherLookup, setTeacherLookup] = useState<Map<string, { code: string; name: string }>>(
    () => new Map(),
  );

  useEffect(() => {
    const tryLoad = async () => {
      const candidates: Array<() => Promise<any>> = [];
      try {
        const mod: any = await import("../services/teachersAdmin");
        for (const k of ["listTeachers", "getTeachers", "list", "fetchTeachers"]) {
          if (typeof mod?.[k] === "function") candidates.push(() => mod[k]());
        }
        if (typeof mod?.default === "function") candidates.push(() => mod.default());
        else if (mod?.default && typeof mod.default.list === "function") candidates.push(() => mod.default.list());
      } catch { /* module not present, fine */ }
      try {
        const sched: any = await import("../services/scheduling");
        for (const k of ["listAllTeachers", "fetchAllTeachers"]) {
          if (typeof sched?.[k] === "function") candidates.push(() => sched[k]());
        }
      } catch { /* fine */ }
      // Final fallback: raw fetch
      candidates.push(async () => {
        const r = await fetch("/api/platform/teachers/?page_size=500", { credentials: "include" });
        if (!r.ok) throw new Error(String(r.status));
        return r.json();
      });

      for (const fn of candidates) {
        try {
          const data = await fn();
          const list = Array.isArray(data) ? data : (data?.results || []);
          if (!Array.isArray(list) || list.length === 0) continue;
          const m = new Map<string, { code: string; name: string }>();
          for (const t of list) {
            const id = String(t?.id ?? "");
            if (!id) continue;
            const code = String(t?.employee_code || t?.teacher_number || t?.code || "").trim();
            const name =
              String(`${t?.first_name || ""} ${t?.last_name || ""}`).trim() ||
              String(t?.name || "").trim();
            if (code || name) m.set(id, { code, name });
          }
          if (m.size > 0) {
            setTeacherLookup(m);
            return;
          }
        } catch { /* try next */ }
      }
    };
    void tryLoad();
  }, []);

  // Fetch active term/year for the masthead (best-effort, non-blocking)
  useEffect(() => {
    import("../services/scheduling").then(({ fetchSchedulingDashboard }) => {
      fetchSchedulingDashboard()
        .then((d: any) => {
          const t = d?.active_term;
          if (t) {
            setTermDisplay(`${t.academic_year_name} ${t.name}`);
            setActiveTermId(String(t.id));
          }
        })
        .catch(() => {});
    });
  }, []);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const _urlScope = (() => {
    try {
      const params = new URLSearchParams(window.location.search);
      return params.get("scope"); // e.g. "grade-4" | "grade-9" | "master"
    } catch { return null; }
  })();
  const _initialFilter = (() => {
    if (!_urlScope || _urlScope === "master") return null;
    const m = _urlScope.match(/^grade-(\d+)$/);
    if (!m) return null;
    const num = m[1];
    const label = num === "4" ? "Form 4" : `Grade ${num}`;
    return { mode: "grade" as const, label };
  })();

  const [regenerating, setRegenerating] = useState(false);
  const [hoveredRow, setHoveredRow] = useState<string | null>(null);
  const [hoveredCol, setHoveredCol] = useState<number | null>(null);
  const [filterMode, setFilterMode] = useState<
    "master" | "class" | "teacher" | "grade" | "subject"
  >(_initialFilter?.mode ?? "master");
  const [filterValue, setFilterValue] = useState<string>("");
  const [subjectValue, setSubjectValue] = useState<string>("");
  const [selectedGrade, setSelectedGrade] = useState<string>(_initialFilter?.label ?? "Grade 11");

  const loadTimetable = useCallback(async () => {
    setRefreshing(true);
    setError("");

    try {
      const runsData = await getSchedulingRuns();
      const runs = Array.isArray(runsData) ? runsData : [];
        if (runs.length > 0 && runs[0].term) {
          setActiveTermId(runs[0].term);
        }
      const completed = completedRuns(runs)
        .slice()
        .sort((a: any, b: any) => {
          const ak = String(a.completed_at || a.created_at || "");
          const bk = String(b.completed_at || b.created_at || "");
          if (bk && ak) return bk.localeCompare(ak);
          if (bk && !ak) return 1;
          if (!bk && ak) return -1;
          return 0;
        });

      if (completed.length === 0) {
        setEntries([]);
        setVersion("No completed timetable");
        return;
      }

      // Save completed runs so the user can pick one explicitly
      setAvailableRuns(
        completed.map((r: any) => ({
          id: r.id,
          version: r.timetable_version,
          completed_at: r.completed_at,
        })),
      );

      // Always sort by completed_at DESC so [0] is genuinely the newest
      completed.sort((a: any, b: any) => {
        const da = a.completed_at ? Date.parse(a.completed_at) : 0;
        const db = b.completed_at ? Date.parse(b.completed_at) : 0;
        return db - da;
      });
      // Honor explicit pick, else newest by completed_at
      // Prefer the active term's newest completed run so the
      // fingerprint matches the Scheduling page header. Fall
      // back to global newest if the active term has no runs.
      const completedInActiveTerm = activeTermId
        ? completed.filter((r: any) => String(r.term) === activeTermId)
        : completed;
      let latestRun =
        (completedInActiveTerm.length > 0
          ? completedInActiveTerm
          : completed)[0];
      if (selectedRunId) {
        const picked = completed.find((r: any) => r.id === selectedRunId);
        if (picked) latestRun = picked;
      }

      // eslint-disable-next-line no-console
      console.log(
        "[Timetable] selectedRunId:", selectedRunId || "(auto)",
        "| picked id:", String(latestRun.id).slice(0, 8),
        "| found in completed:", completed.some((r: any) => r.id === latestRun.id),
      );
      // eslint-disable-next-line no-console
      console.log(
        "[Timetable] picking run:", String(latestRun.id).slice(0, 8),
        "version:", String(latestRun.timetable_version || "").slice(0, 8),
        "completed_at:", (latestRun as any).completed_at,
        "| total completed:", completed.length,
        "| first 3:", completed.slice(0, 3).map((r: any) =>
          String(r.id).slice(0, 8) + "@" + (r.completed_at || "-")
        ),
      );
      let result: any = null;
      try {
        result = await getSchedulingRunResults(latestRun.id);
      } catch (e) {
        console.error("Failed to fetch run results:", e);
      }
      const timetableVersion = result?.timetable_version;

      // Fetch the previous completed run so the change counter compares
      // against a real previous generation, not the previous page load.
      let previousRunId: string | null = null; void previousRunId;
      let previousVersionName: string = ""; void previousVersionName;
      let previousEntries: any[] = [];
      try {
        const latestIdx = completed.findIndex((r: any) => r.id === latestRun.id);
        const prevRun = (latestIdx >= 0 && latestIdx + 1 < completed.length)
          ? completed[latestIdx + 1]
          : null;
        if (prevRun) {
          previousRunId = prevRun.id;
          const prevResult = await getSchedulingRunResults(prevRun.id);
          const prevTV = (prevResult as any).timetable_version;
          previousVersionName = String(prevTV?.name || prevRun.timetable_version || "");
          previousEntries = Array.isArray(prevTV?.entries) ? prevTV.entries : [];
        }
      } catch (e) {
        // eslint-disable-next-line no-console
        console.log("[Timetable] previous-run baseline fetch failed:", e);
      }

      if (!timetableVersion) {
        setEntries([]);
        setVersion("No timetable data");
        setError(
          "This run is missing timetable entries. It may have been created before the system supported full viewing, or the data was deleted.",
        );
        return;
      }

      const backendEntries = Array.isArray(timetableVersion.entries)
        ? timetableVersion.entries
        : [];

      setEntries(backendEntries);
      setLoadedAt(new Date());
      // Build a small fingerprint so we can SEE when content changed
      try {
        const sorted = backendEntries
          .map((e: any) =>
            String(e?.day || "") + "/" + String(e?.period_number || "") +
            "/" + String(e?.instructional_group_name || "") +
            "/" + String(e?.subject_code || "") +
            "/" + String(e?.teacher_code || "") +
            "/" + String(e?.room_code || "")
          )
          .sort()
          .join("|");
        // small non-crypto hash
        let h = 5381;
        for (let i = 0; i < sorted.length; i++) h = ((h * 33) ^ sorted.charCodeAt(i)) >>> 0;
        setEntrySignature(h.toString(16).padStart(8, "0"));
      } catch {
        setEntrySignature("");
      }

      // Build a per-cell map for change detection
      try {
        const classOf = (e: any): string => {
          const raw = String(e?.instructional_group_name || "");
          const parts = raw.split(" - ");
          return (parts[1] || parts[0] || raw).trim();
        };
        const map = new Map<string, string>();
        for (const e of backendEntries) {
          const d = String(e?.day || "");
          const c = classOf(e);
          const p = String(e?.period_number || "");
          const k = d + ":" + c + ":" + p;
          const sig = [
            String(e?.subject_code || ""),
            String(e?.teacher_code || ""),
            String(e?.room_code || ""),
          ].join("/");
          map.set(k, (map.get(k) ? map.get(k) + "|" : "") + sig);
        }
        // Sort each entry's sig
        for (const [k, v] of map) {
          map.set(k, v.split("|").sort().join("|"));
        }
        const buildCellMap = (list: any[]): Map<string, string> => {
          const m = new Map<string, string>();
          for (const e of list) {
            const code = String(e?.instructional_group_code || "").trim();
            const nm = String(e?.instructional_group_name || "");
            const c = code || nm.split(" - ")[1] || nm;
            const d = String(e?.day || "");
            const pp = String(e?.period_number || "");
            const k = d + ":" + c + ":" + pp;
            const sig = [
              String(e?.subject_code || ""),
              String(e?.teacher_code || ""),
              String(e?.room_code || ""),
            ].join("/");
            m.set(k, (m.get(k) ? m.get(k) + "|" : "") + sig);
          }
          for (const [k, v] of m) m.set(k, v.split("|").sort().join("|"));
          return m;
        };
        const prevFromBackend = previousEntries.length > 0
          ? buildCellMap(previousEntries)
          : null;
        const prev = prevFromBackend ?? prevEntryMapRef.current;
        if (prev && prev.size > 0) {
          const byDay: Record<string, number> = {};
          const samples: string[] = [];
          let total = 0;
          const allKeys = new Set<string>([...prev.keys(), ...map.keys()]);
          for (const k of allKeys) {
            const a = prev.get(k) || "";
            const b = map.get(k) || "";
            if (a !== b) {
              total++;
              const [dd] = k.split(":");
              byDay[dd] = (byDay[dd] || 0) + 1;
              if (samples.length < 12) {
                const [day, cls, per] = k.split(":");
                samples.push(day + " P" + per + " " + cls + ": " + (a || "(empty)") + " -> " + (b || "(empty)"));
              }
            }
          }
          setChangesSummary({ total, byDay, samples });
          // Build the changed cell key set for per-cell highlight
          const chk = new Set<string>();
          for (const k of allKeys) {
            const a = prev.get(k) || "";
            const b = map.get(k) || "";
            if (a !== b) chk.add(k);
          }
          setChangedKeys(chk);
          // eslint-disable-next-line no-console
          console.log("[Timetable] changes vs previous load:", total, byDay);
        } else {
          setChangesSummary({ total: 0, byDay: {}, samples: [] });
          setChangedKeys(new Set());
        }
        prevEntryMapRef.current = map;
      } catch (err) {
        // eslint-disable-next-line no-console
        console.log("[Timetable] diff failed:", err);
      }
      try {
        const keys = new Set<string>();
        for (const e of backendEntries.slice(0, 50)) {
          if (e && typeof e === "object") {
            Object.keys(e as any).forEach((k) => keys.add(k));
          }
        }
      } catch (err) {
      }
      setError(""); // Clear any previous error on successful load
      setVersion(
        timetableVersion.name ||
          latestRun.timetable_version ||
          "Live timetable",
      );
    } catch (err) {
      console.error("Timetable loading failed:", err);

      setEntries([]);
      setVersion("Live timetable");

      setError(
        "Unable to load the latest completed timetable from the backend.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [selectedRunId, activeTermId]);

  // Sync URL ?run=<id> into selectedRunId (from "View" button)
  useEffect(() => {
    const urlRunId = searchParams.get("run") || "";
    if (urlRunId && urlRunId !== selectedRunId) {
      setSelectedRunId(urlRunId);
    }
    // eslint-disable-next-line
  }, [searchParams]);


  // Mark changed cells in the DOM after render
  useEffect(() => {
    // Clear old markers
    document
      .querySelectorAll("[data-ttcell-key].is-changed")
      .forEach((el) => el.classList.remove("is-changed"));

    if (!highlightOn) return;
    if (changedKeys.size === 0) return;

    const cells = document.querySelectorAll<HTMLElement>("[data-ttcell-key]");
    cells.forEach((el) => {
      const k = el.getAttribute("data-ttcell-key");
      if (!k) return;
      // Match by day:class:period OR day:classCode:period
      for (const ck of changedKeys) {
        const [dk, ckp, pk] = ck.split(":");
        const [edk, eck, epk] = k.split(":");
        // Match if day + period + class-name overlap
        if (dk === edk && pk === epk && (ckp === eck || eck.includes(ckp) || ckp.includes(eck))) {
          el.classList.add("is-changed");
          break;
        }
      }
    });
  }, [changedKeys, highlightOn, entries, version]);

  // ------------------------------------------------------------
  // Download the visible timetable as PNG or PDF
  // ------------------------------------------------------------
  const captureTarget = (): HTMLElement | null => {
    return (
      document.querySelector<HTMLElement>("[data-tt-capture]") ||
      document.querySelector<HTMLElement>(".tt-grid-wrap") ||
      document.querySelector<HTMLElement>(".tt-table-wrap") ||
      null
    );
  };

  // ==========================================================================
  // EXPORT â€” HARD RULE: A3 only, never A4.
  // Timetables are A3 sheets. Any shrink to A4 is a bug.
  //   * PNG: rendered at >= 3508px shortest edge (A3/300 DPI) so it prints
  //          at A3 without upscaling artefacts.
  //   * PDF: A3 page, orientation auto-derived from the capture aspect.
  // ==========================================================================
  const A3_SHORT_PX = 3508;
  const A3_LONG_PX = 4961;

  function a3TargetWidth(el: HTMLElement): number {
    const isLandscape = el.scrollWidth >= el.scrollHeight;
    return isLandscape ? A3_LONG_PX : A3_SHORT_PX;
  }

  function stableCloneOverrides(clonedDoc: Document) {
    clonedDoc.querySelectorAll("table").forEach((t) => {
      const tbl = t as HTMLElement;
      tbl.style.tableLayout = "fixed";
      tbl.style.width = "auto";
      tbl.style.minWidth = "100%";
      tbl.style.borderCollapse = "collapse";
    });
    clonedDoc.querySelectorAll("th, td").forEach((c) => {
      const cell = c as HTMLElement;
      cell.style.whiteSpace = "nowrap";
      cell.style.overflow = "visible";
      cell.style.maxWidth = "none";
    });
    clonedDoc.querySelectorAll("table thead tr").forEach((row) => {
      const cells = Array.from(row.children) as HTMLElement[];
      const n = cells.length;
      if (n === 0) return;
      cells.forEach((c, i) => {
        c.style.width = i === 0 ? "8%" : `${92 / (n - 1)}%`;
      });
    });
  }

  // ==========================================================================
  // EXPORT — HARD RULE: A3 only, never A4.
  //   * PNG: padded to exact A3 pixel dims + pHYs chunk declaring 300 DPI,
  //          so the file IS a 297x420mm (or 420x297mm) image at the byte level.
  //   * PDF: jsPDF format="a3", aspect-preserving fit.
  // ==========================================================================
  const A3_PORTRAIT_PX: [number, number] = [3508, 4961];
  const A3_LANDSCAPE_PX: [number, number] = [4961, 3508];
  const A3_PORTRAIT_MM: [number, number] = [297, 420];
  const A3_LANDSCAPE_MM: [number, number] = [420, 297];
  const EXPORT_DPI = 300;

  function a3Dims(el: HTMLElement) {
    const landscape = el.scrollWidth >= el.scrollHeight;
    return landscape
      ? { px: A3_LANDSCAPE_PX, mm: A3_LANDSCAPE_MM, landscape: true }
      : { px: A3_PORTRAIT_PX,  mm: A3_PORTRAIT_MM,  landscape: false };
  }

  let _crcTable: Uint32Array | null = null;
  function crc32(bytes: Uint8Array): number {
    if (!_crcTable) {
      _crcTable = new Uint32Array(256);
      for (let n = 0; n < 256; n++) {
        let c = n;
        for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
        _crcTable[n] = c >>> 0;
      }
    }
    let crc = 0xffffffff;
    for (let i = 0; i < bytes.length; i++) {
      crc = (crc >>> 8) ^ _crcTable[(crc ^ bytes[i]) & 0xff];
    }
    return (crc ^ 0xffffffff) >>> 0;
  }

  function canvasToA3PngBlob(canvas: HTMLCanvasElement): Blob {
    const dataUrl = canvas.toDataURL("image/png");
    const b64 = dataUrl.substring(dataUrl.indexOf(",") + 1);
    const bin = atob(b64);
    const png = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) png[i] = bin.charCodeAt(i);

    const ppu = Math.round(EXPORT_DPI / 0.0254);
    const chunk = new Uint8Array(21);
    const dv = new DataView(chunk.buffer);
    dv.setUint32(0, 9);
    chunk.set([0x70, 0x48, 0x59, 0x73], 4);
    dv.setUint32(8, ppu);
    dv.setUint32(12, ppu);
    chunk[16] = 1;
    dv.setUint32(17, crc32(chunk.slice(4, 17)));

    const out = new Uint8Array(png.length + 21);
    out.set(png.slice(0, 33), 0);
    out.set(chunk, 33);
    out.set(png.slice(33), 54);
    return new Blob([out], { type: "image/png" });
  }

  function padToA3(canvas: HTMLCanvasElement, dims: { px: [number, number] }): HTMLCanvasElement {
    const W = dims.px[0];
    const H = dims.px[1];
    const out = document.createElement("canvas");
    out.width = W;
    out.height = H;
    const ctx = out.getContext("2d");
    if (!ctx) return canvas;
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, W, H);
    const contentRatio = canvas.width / canvas.height;
    const pageRatio = W / H;
    let dw: number, dh: number, dx: number, dy: number;
    if (contentRatio > pageRatio) {
      dw = W; dh = W / contentRatio; dx = 0; dy = (H - dh) / 2;
    } else {
      dh = H; dw = H * contentRatio; dx = (W - dw) / 2; dy = 0;
    }
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(canvas, dx, dy, dw, dh);
    return out;
  }

  function stableCloneOverrides(clonedDoc: Document) {
    clonedDoc.querySelectorAll("table").forEach((t) => {
      const tbl = t as HTMLElement;
      tbl.style.tableLayout = "fixed";
      tbl.style.width = "auto";
      tbl.style.minWidth = "100%";
      tbl.style.borderCollapse = "collapse";
    });
    clonedDoc.querySelectorAll("th, td").forEach((c) => {
      const cell = c as HTMLElement;
      cell.style.whiteSpace = "nowrap";
      cell.style.overflow = "visible";
      cell.style.maxWidth = "none";
    });
    clonedDoc.querySelectorAll("table thead tr").forEach((row) => {
      const cells = Array.from(row.children) as HTMLElement[];
      const n = cells.length;
      if (n === 0) return;
      cells.forEach((c, i) => {
        c.style.width = i === 0 ? "8%" : `${92 / (n - 1)}%`;
      });
    });

    // Normalize vertical-mode text (TEA BREAK / LUNCH / PRAYERS) — html2canvas
    // flips these because it renders horizontally then applies the baked 180deg
    // rotate. Strip writing-mode, apply a single explicit rotate.
    const win: any = clonedDoc.defaultView || window;
    let vCount = 0;
    clonedDoc.querySelectorAll<HTMLElement>("*").forEach((el) => {
      let cs: CSSStyleDeclaration | null = null;
      try { cs = win.getComputedStyle(el); } catch { return; }
      if (!cs) return;
      const wm = (cs as any).writingMode || (cs as any).webkitWritingMode || "";
      if (!/vertical/.test(wm)) return;
      vCount++;
      const tr = cs.transform || "";
      const flipped = /matrix\(-1,\s*0,\s*0,\s*-1/.test(tr);
      const dir = flipped ? -90 : 90;
      const apply = (target: HTMLElement) => {
        target.style.writingMode = "horizontal-tb";
        (target.style as any).webkitWritingMode = "horizontal-tb";
        target.style.transform = `rotate(${dir}deg)`;
        target.style.transformOrigin = "center center";
        target.style.whiteSpace = "nowrap";
        target.style.display = "inline-block";
      };
      if (el.tagName === "TD" || el.tagName === "TH") {
        Array.from(el.children).forEach((c) => apply(c as HTMLElement));
      } else {
        apply(el);
      }
    });
    // eslint-disable-next-line no-console
    console.log(`[export] vertical-text cells normalized: ${vCount}`);
  }

  // ==========================================================================
  // EXPORT — HARD RULE: A3 Landscape ONLY. No auto-detection.
  //   * PNG: exact A3 Landscape dims (4961x3508px @ 300 DPI = 420x297mm).
  //   * PDF: jsPDF format="a3" landscape.
  // ==========================================================================
  const A3_LANDSCAPE_PX: [number, number] = [4961, 3508];
  const A3_LANDSCAPE_MM: [number, number] = [420, 297];
  const EXPORT_DPI = 300;

  let _crcTable: Uint32Array | null = null;
  function crc32(bytes: Uint8Array): number {
    if (!_crcTable) {
      _crcTable = new Uint32Array(256);
      for (let n = 0; n < 256; n++) {
        let c = n;
        for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
        _crcTable[n] = c >>> 0;
      }
    }
    let crc = 0xffffffff;
    for (let i = 0; i < bytes.length; i++) {
      crc = (crc >>> 8) ^ _crcTable[(crc ^ bytes[i]) & 0xff];
    }
    return (crc ^ 0xffffffff) >>> 0;
  }

  function canvasToA3PngBlob(canvas: HTMLCanvasElement): Blob {
    const dataUrl = canvas.toDataURL("image/png");
    const b64 = dataUrl.substring(dataUrl.indexOf(",") + 1);
    const bin = atob(b64);
    const png = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) png[i] = bin.charCodeAt(i);

    const ppu = Math.round(EXPORT_DPI / 0.0254);
    const chunk = new Uint8Array(21);
    const dv = new DataView(chunk.buffer);
    dv.setUint32(0, 9);
    chunk.set([0x70, 0x48, 0x59, 0x73], 4);
    dv.setUint32(8, ppu);
    dv.setUint32(12, ppu);
    chunk[16] = 1;
    dv.setUint32(17, crc32(chunk.slice(4, 17)));

    const out = new Uint8Array(png.length + 21);
    out.set(png.slice(0, 33), 0);
    out.set(chunk, 33);
    out.set(png.slice(33), 54);
    return new Blob([out], { type: "image/png" });
  }

  function padToA3Landscape(canvas: HTMLCanvasElement): HTMLCanvasElement {
    const W = A3_LANDSCAPE_PX[0];
    const H = A3_LANDSCAPE_PX[1];
    const out = document.createElement("canvas");
    out.width = W;
    out.height = H;
    const ctx = out.getContext("2d");
    if (!ctx) return canvas;
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, W, H);
    const contentRatio = canvas.width / canvas.height;
    const pageRatio = W / H;
    let dw: number, dh: number, dx: number, dy: number;
    if (contentRatio > pageRatio) {
      dw = W; dh = W / contentRatio; dx = 0; dy = (H - dh) / 2;
    } else {
      dh = H; dw = H * contentRatio; dx = (W - dw) / 2; dy = 0;
    }
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(canvas, dx, dy, dw, dh);
    return out;
  }

  function stableCloneOverrides(clonedDoc: Document) {
    // Force a wide fixed layout so the table never squishes
    clonedDoc.querySelectorAll("[data-tt-capture], .tt-grid-wrap, .tt-table-wrap").forEach((el) => {
      (el as HTMLElement).style.width = "max-content";
      (el as HTMLElement).style.minWidth = "3500px";
    });

    clonedDoc.querySelectorAll("table").forEach((t) => {
      const tbl = t as HTMLElement;
      tbl.style.tableLayout = "fixed";
      tbl.style.width = "3500px"; // Force wide layout
      tbl.style.maxWidth = "none";
      tbl.style.borderCollapse = "collapse";
    });

    clonedDoc.querySelectorAll("th, td").forEach((c) => {
      const cell = c as HTMLElement;
      cell.style.whiteSpace = "nowrap";
      cell.style.overflow = "visible";
      cell.style.maxWidth = "none";
    });

    // Fix upside-down text: strip writing-mode and transform completely.
    const win: any = clonedDoc.defaultView || window;
    let vCount = 0;
    clonedDoc.querySelectorAll<HTMLElement>("*").forEach((el) => {
      let cs: CSSStyleDeclaration | null = null;
      try { cs = win.getComputedStyle(el); } catch { return; }
      if (!cs) return;
      const wm = (cs as any).writingMode || (cs as any).webkitWritingMode || "";
      if (/vertical/.test(wm)) {
        vCount++;
        el.style.writingMode = "horizontal-tb";
        (el.style as any).webkitWritingMode = "horizontal-tb";
        el.style.transform = "none";
        el.style.display = "inline-block";
        el.style.whiteSpace = "nowrap";
      }
    });
    // eslint-disable-next-line no-console
    console.log(`[export] vertical-text cells normalized: ${vCount}`);
  }

  async function downloadTimetablePNG() {
    try {
      await waitForRenderFlush();
      const mod = await import("html2canvas");
      const html2canvas = (mod as any).default || (mod as any);
      const el = captureTarget();
      if (!el) { alert("Could not find the timetable to capture."); return; }
      
      const scale = Math.max(2, A3_LANDSCAPE_PX[0] / Math.max(1, el.scrollWidth));
      const raw = await html2canvas(el, {
        scale,
        backgroundColor: "#ffffff",
        useCORS: true,
        logging: false,
        width: el.scrollWidth,
        height: el.scrollHeight,
        onclone: stableCloneOverrides,
      });
      const a3 = padToA3Landscape(raw);
      const blob = canvasToA3PngBlob(a3);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      const safe = String(version || "timetable").replace(/[^a-z0-9_-]+/gi, "_");
      link.download = safe + "_A3.png";
      link.href = url;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 5000);
      // eslint-disable-next-line no-console
      console.log(`[export] PNG ${A3_LANDSCAPE_PX[0]}x${A3_LANDSCAPE_PX[1]}px @ ${EXPORT_DPI}DPI = 420.0 x 297.0 mm (A3 LANDSCAPE)`);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.log("[download] PNG failed:", err);
      alert("PNG download failed - see console.");
    }
  }

  async function downloadTimetablePDF() {
    try {
      await waitForRenderFlush();
      const h2cMod = await import("html2canvas");
      const html2canvas = (h2cMod as any).default || (h2cMod as any);
      const jsPdfMod: any = await import("jspdf");
      const jsPDF = jsPdfMod.jsPDF || jsPdfMod.default;
      const el = captureTarget();
      if (!el) { alert("Could not find the timetable to capture."); return; }
      
      const scale = Math.max(2, A3_LANDSCAPE_PX[0] / Math.max(1, el.scrollWidth));
      const raw = await html2canvas(el, {
        scale,
        backgroundColor: "#ffffff",
        useCORS: true,
        logging: false,
        width: el.scrollWidth,
        height: el.scrollHeight,
        onclone: stableCloneOverrides,
      });
      const a3 = padToA3Landscape(raw);
      const imgData = a3.toDataURL("image/png");
      const pdf = new jsPDF({
        orientation: "landscape",
        unit: "mm",
        format: "a3",
      });
      const pw = pdf.internal.pageSize.getWidth();
      const ph = pdf.internal.pageSize.getHeight();
      pdf.addImage(imgData, "PNG", 0, 0, pw, ph);
      const safe = String(version || "timetable").replace(/[^a-z0-9_-]+/gi, "_");
      pdf.save(safe + "_A3.pdf");
      // eslint-disable-next-line no-console
      console.log(`[export] PDF A3 landscape 420.0 x 297.0 mm`);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.log("[download] PDF failed:", err);
      alert("PDF download failed - see console.");
    }
  }

  useEffect(() => {
    void loadTimetable();
  }, [loadTimetable, selectedRunId]);

  // ------------------------------------------------------------
  // AUTO-POLL: every 6 seconds, refetch the runs list and if a
  // newer completed run exists, reload the timetable.
  // This makes the grid reflect new generations regardless of
  // which page you are on, without any manual refresh.
  // ------------------------------------------------------------
  useEffect(() => {
    let cancelled = false;
    let lastSeenVersion: string | null = null;

    async function checkForNewer() {
      try {
        const runsData = await getSchedulingRuns();
        const arr = Array.isArray(runsData) ? runsData : [];
        const completed = completedRuns(arr)
          .slice()
          .sort((a: any, b: any) => {
            const ak = String(a.completed_at || a.created_at || "");
            const bk = String(b.completed_at || b.created_at || "");
            if (bk && ak) return bk.localeCompare(ak);
            if (bk && !ak) return 1;
            if (!bk && ak) return -1;
            return 0;
          });
        if (completed.length === 0) return;
        const newest = completed[0];
        const v = String(newest.timetable_version || newest.id || "");
        if (lastSeenVersion === null) {
          // First poll - just record baseline; don't reload
          lastSeenVersion = v;
          return;
        }
        if (v !== lastSeenVersion) {
          lastSeenVersion = v;
          if (userPickedRef.current) {
            // eslint-disable-next-line no-console
            console.log("[Timetable] newer version detected but user has pinned a run; skipping auto-reload:", v);
            return;
          }
          // eslint-disable-next-line no-console
          console.log("[Timetable] newer version detected, reloading:", v);
          if (!cancelled) await loadTimetable();
        }
      } catch {
        /* ignore - transient network issues */
      }
    }

    const id = window.setInterval(checkForNewer, 6000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [loadTimetable]);


  // ---- Filter derivations ----
  const allTeachers = useMemo(() => {
    const set = new Set<string>();
    for (const e of entries) {
      const code = displayTeacherCode(e);
      if (code && code !== "-") set.add(code);
    }
    return Array.from(set).sort();
  }, [entries]);

  const teacherRoster = useMemo(() => {
    // Resolve each entry to its canonical teacher via FK teacher_id.
    // Fall back to teacher_code only if the FK is missing.
    const byId = new Map<string, { code: string; name: string }>();
    const orphanCodes = new Map<string, string>(); // code -> name for FK-less entries
    for (const e of entries) {
      const tid = String(
        (e as any)?.teacher_id || (e as any)?.teacher || ""
      ).trim();
      const rawCode = String(displayTeacherCode(e) || "").toUpperCase().trim();
      const rawName = String(
        (e as any)?.teacher_name || (e as any)?.teacher || ""
      ).trim();

      if (tid && teacherLookup.has(tid)) {
        if (!byId.has(tid)) byId.set(tid, teacherLookup.get(tid)!);
        continue;
      }
      // No FK: bucket by code so a teacher never appears twice under the
      // same code. Names are still shown for display only.
      if (rawCode && rawCode !== "-") {
        if (!orphanCodes.has(rawCode)) orphanCodes.set(rawCode, rawName);
      }
    }
    const merged: { code: string; name: string }[] = [];
    for (const rec of byId.values()) merged.push(rec);
    for (const [code, name] of orphanCodes) merged.push({ code, name });
    return merged.sort((a, b) => (a.code || "").localeCompare(b.code || ""));
  }, [entries, teacherLookup]);

  function handleRegenScope() {
    const match = selectedGrade.match(/(\d+)/);
    if (!match) return alert("Could not parse grade number");
    const scopeId = match[1];
    window.location.href = `/scheduling?scope_kind=grade&scope_id=${scopeId}&auto_start=true`;
  }

  const visibleEntries = useMemo(() => {
    if (filterMode === "teacher" && filterValue) {
      return entries.filter((e) => displayTeacherCode(e) === filterValue);
    }
    if (filterMode === "subject" && subjectValue) {
      const sv = subjectValue.trim().toUpperCase();
      return entries.filter(
        (e) => normalisedSubjectCode(e).toUpperCase() === sv,
      );
    }
    return entries;
  }, [entries, filterMode, filterValue, subjectValue]);

  const visibleClasses = useMemo(() => {
    if (filterMode === "class" && filterValue) {
      return CLASSES.filter((c) => c.label === filterValue);
    }
    if (filterMode === "grade" && selectedGrade) {
      // Grade mode: show BOTH E and W streams of the selected
      // grade side-by-side. Match across label styles:
      //   "Grade 10E" / "Grade 10W"  (Grade 9, 10)
      //   "G11E" / "G11W"            (Grade 11)
      //   "Form 4E" / "Form 4W"      (Form 4)
      const norm = (s: string) =>
        s.trim().toLowerCase().replace(/\s+/g, "");
      const sel = norm(selectedGrade);
      // Extract the numeric part: "grade10"->"10", "form4"->"4"
      const numMatch = sel.match(/(\d+)/);
      const num = numMatch ? numMatch[1] : null;

      return CLASSES.filter((c) => {
        const lbl = norm(c.label);
        // Direct match: "grade 10e"/"grade 10w"
        if (lbl === sel + "e" || lbl === sel + "w") return true;
        // Number-only match: "g11e"/"g11w"/"f4e"/"f4w"
        if (num) {
          if (lbl === "g" + num + "e" || lbl === "g" + num + "w") return true;
          if (lbl === "f" + num + "e" || lbl === "f" + num + "w") return true;
          if (lbl === "grade" + num + "e" || lbl === "grade" + num + "w") return true;
          if (lbl === "form" + num + "e" || lbl === "form" + num + "w") return true;
        }
        return false;
      });
    }
    if (filterMode === "subject" && subjectValue) {
      // Subject mode: show every class that has at least one
      // entry for the selected subject code.
      const sv = subjectValue.trim().toUpperCase();
      const taught = new Set<string>();
      for (const e of entries) {
        const sc = normalisedSubjectCode(e).toUpperCase();
        if (sc !== sv) continue;
        for (const c of CLASSES) {
          if (classMatches(e, c)) taught.add(c.label);
        }
      }
      return CLASSES.filter((c) => taught.has(c.label));
    }
    if (filterMode === "teacher" && filterValue) {
      const taught = new Set<string>();
      for (const e of visibleEntries) {
        const gn = groupName(e);
        if (!gn) continue;
        for (const c of CLASSES) {
          if (classMatches(e, c)) taught.add(c.label);
        }
      }
      return CLASSES.filter((c) => taught.has(c.label));
    }
    return CLASSES;
  }, [filterMode, filterValue, subjectValue, visibleEntries,
      selectedGrade, entries]);

  const scheduledEntries = visibleEntries.length;

  // Dynamic header based on the active view.
  const viewTitle = useMemo(() => {
    if (filterMode === "grade" && selectedGrade) {
      return `${selectedGrade} Streams`;
    }
    if (filterMode === "class" && filterValue) {
      return `${filterValue} Timetable`;
    }
    if (filterMode === "teacher" && filterValue) {
      return `Teacher ${filterValue} Timetable`;
    }
    if (filterMode === "subject" && subjectValue) {
      return `Subject ${subjectValue} Timetable`;
    }
    return "Master Timetable";
  }, [filterMode, filterValue, subjectValue, selectedGrade]);

  // Unique subject codes present in the loaded timetable â€” used by
  // the subject-mode dropdown.
  const allSubjects = useMemo(() => {
    const s = new Set<string>();
    for (const e of entries) {
      const sc = normalisedSubjectCode(e).toUpperCase();
      if (sc && sc !== "GST") s.add(sc);
    }
    return Array.from(s).sort();
  }, [entries]);


    const uniquePeriods = useMemo(() => {
    const map = new Map();
    for (const e of entries) {
      if (e.period_number && !map.has(e.period_number)) {
        map.set(e.period_number, {
          period_number: e.period_number,
          start_time: e.period_start_time,
          end_time: e.period_end_time
        });
      }
    }
    return Array.from(map.values());
  }, [entries]);

  const entriesBySlot = useMemo(() => {
    const map = new Map<string, TimetableEntryResult[]>();

    for (const entry of visibleEntries) {
      const day = canonicalDayCode(entry);
      const period = periodNumber(entry);

      if (!day || !period) {
        continue;
      }

      const key = `${day}:${period}`;
      const existing = map.get(key) || [];

      existing.push(entry);
      map.set(key, existing);
    }

    return map;
  }, [visibleEntries]);

  function getSlotEntries(
    dayCode: string,
    definition: ClassDefinition,
    period: number,
  ): TimetableEntryResult[] {
    const slot = entriesBySlot.get(`${dayCode}:${period}`) || [];

    return slot.filter((entry) => classMatches(entry, definition));
  }

  return (
    <>
      

      <main className="tt-page" data-student={isStudentView || undefined}>
<style>{`
        /* â”€â”€â”€ THE APPROVED A3 GRID CSS â”€â”€â”€ */
        
        /* Table container and borders */
        .tt-table-wrap {
          border: 3px solid #0f172a !important;
          border-radius: 8px !important;
          background: #fff !important;
          overflow-x: auto !important;
          overflow-y: visible !important;
          width: 100% !important;
          padding-bottom: 20px !important;
          margin-bottom: 1rem !important;
        }

        .tt-table {
          min-width: 1300px !important; /* Wide enough for 3 lines */
          width: 100% !important;
          table-layout: fixed !important;
          border-collapse: collapse !important;
          font-size: 0.72rem !important;
        }

        .tt-table th, .tt-table td {
          border: 1px solid #94a3b8 !important;
          padding: 4px !important;
          text-align: center !important;
          vertical-align: middle !important;
        }

        /* Dark Blue Headers */
        .tt-table th, .tt-day-head, .tt-class-head, .tt-day, .tt-class {
          background: #0f172a !important;
          color: #ffffff !important;
          font-weight: 800 !important;
        }

        .tt-period-head {
          background: #0f172a !important;
          color: #ffffff !important;
        }
        .tt-period-label { color: #ffffff !important; font-size: 0.75rem; }
        .tt-period-time { color: #cbd5e1 !important; font-size: 0.6rem; }

        /* Vertical Day and Class columns */
        .tt-day-head, .tt-day {
          writing-mode: vertical-rl !important;
          transform: rotate(180deg) !important;
          padding: 8px 2px !important;
          width: 40px !important;
        }
        .tt-class-head, .tt-class { width: 60px !important; }

        /* Vertical Breaks */
        .tt-tea, td.tt-tea { background: #fef3c7 !important; color: #92400e !important; writing-mode: vertical-rl !important; transform: rotate(180deg) !important; font-weight: 800 !important; }
        .tt-lunch, td.tt-lunch { background: #dcfce7 !important; color: #166534 !important; writing-mode: vertical-rl !important; transform: rotate(180deg) !important; font-weight: 800 !important; }
        .tt-prayers, td.tt-prayers { background: #f3e8ff !important; color: #6b21a8 !important; writing-mode: vertical-rl !important; transform: rotate(180deg) !important; font-weight: 800 !important; }
        .tt-activities, td.tt-activities { background: #dbeafe !important; color: #1e40af !important; writing-mode: vertical-rl !important; transform: rotate(180deg) !important; font-weight: 800 !important; }

        /* THE 3-LINE CELL STACKING */
        .tt-lesson {
          display: flex !important;
          flex-direction: column !important;
          align-items: center !important;
          justify-content: center !important;
          gap: 1px !important;
          width: 100% !important;
        }
        
        .tt-subject, .tt-teacher, .tt-room {
          display: block !important;
          width: 100% !important;
          text-align: center !important;
          white-space: nowrap !important; /* Forces exactly 1 line */
          overflow: hidden !important;
          text-overflow: ellipsis !important;
          line-height: 1.1 !important;
        }
        
        .tt-subject { font-weight: 800 !important; font-size: 0.7rem !important; color: #0f172a !important; }
        .tt-teacher { font-weight: 600 !important; font-size: 0.62rem !important; color: #475569 !important; }
        .tt-room    { font-weight: 500 !important; font-size: 0.58rem !important; color: #64748b !important; }

        /* 75% ZOOM HOVER */
        .tt-table td {
          transition: transform 0.15s ease-out, box-shadow 0.15s ease-out !important;
          transform-origin: center center !important;
          will-change: transform !important;
        }
        .tt-table td:hover:not(.tt-tea):not(.tt-lunch):not(.tt-prayers):not(.tt-activities) {
          background-color: #e0f2fe !important;
          box-shadow: 0 20px 40px rgba(0,0,0,0.5) !important;
          border: 2px solid #0284c7 !important;
          transform: scale(1.75) !important;
          z-index: 9999 !important;
          position: relative !important;
          pointer-events: none !important;
        }

        /* Fingerprint */
        .tt-fingerprint {
          background: #0f172a !important;
          border: 1px solid #1e293b !important;
          border-radius: 6px !important;
          padding: 6px 12px !important;
          display: inline-flex !important;
          align-items: center !important;
          gap: 8px !important;
        }
        .tt-fp-label, .tt-fp-ver, .tt-fp-time { color: #facc15 !important; font-weight: 800 !important; font-size: 0.65rem !important; }
        .tt-fp-hash { color: #22c55e !important; font-family: monospace !important; font-weight: 800 !important; text-shadow: 0 0 8px rgba(34,197,94,0.8) !important; font-size: 0.78rem !important; }

        /* Teacher Roster */
        .tt-teacher-roster {
          background: #ffffff !important;
          border: 2px solid #0284c7 !important;
          border-radius: 12px !important;
          padding: 16px !important;
          margin-top: 16px !important;
        }
        .tt-tr-head { font-size: 1rem !important; font-weight: 800 !important; color: #0284c7 !important; margin-bottom: 12px !important; border-bottom: 2px solid #e0f2fe !important; padding-bottom: 8px !important; }
        .tt-tr-grid { display: grid !important; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)) !important; gap: 10px !important; }
        .tt-tr-item { background: #f8fafc !important; border: 1px solid #e2e8f0 !important; border-radius: 6px !important; padding: 8px 12px !important; font-size: 0.85rem !important; color: #334155 !important; }
        .tt-tr-item b { color: #0284c7 !important; font-weight: 800 !important; }
      `}</style>



        

        

      

      

      

      

      

      <style>{`
        /* â”€â”€â”€ 1. BUTTONS & TOOLBAR (Preserved) â”€â”€â”€ */
        .tt-header { background: #ffffff; border: 2px solid #0284c7; padding: 16px; border-radius: 16px; box-shadow: 0 8px 24px rgba(2,132,199,0.15); display: flex; flex-direction: column; gap: 16px; }
        .tt-header > div:first-child { display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px; background: #f0f9ff; padding: 12px; border-radius: 12px; border: 2px solid #bae6fd; overflow: hidden; }
        
        .tt-hard-reload, .tt-dl-png, .tt-dl-pdf, .tt-highlight-toggle, .tt-nuke-cache {
            background: #f97316 !important; color: #431407 !important; border: 3px solid #c2410c !important; 
            font-weight: 900 !important; font-size: 0.75rem !important; border-radius: 8px !important; padding: 8px 12px !important;
            cursor: pointer !important; transition: all 0.2s ease !important; display: flex !important; align-items: center !important; justify-content: center !important;
        }
        .tt-hard-reload, .tt-dl-png, .tt-dl-pdf { grid-column: span 2; }
        .tt-highlight-toggle, .tt-nuke-cache { grid-column: span 3; }
        
        .tt-hard-reload:hover, .tt-dl-png:hover, .tt-dl-pdf:hover, .tt-highlight-toggle:hover, .tt-nuke-cache:hover {
            background: #0284c7 !important; color: #ffffff !important; border-color: #0284c7 !important; 
            transform: translateY(-4px) scale(1.05) !important; box-shadow: 0 10px 20px rgba(2,132,199,0.4) !important;
        }
        
        .tt-fingerprint, .tt-subtitle, .tt-status, .tt-actions, .tt-changes-banner { grid-column: span 6 !important; margin-top: 8px !important; }

        /* â”€â”€â”€ 2. ACTIONS (Refresh & Print) â”€â”€â”€ */
        .tt-actions { display: flex !important; gap: 12px !important; align-items: center !important; width: 100% !important; }
        .tt-button {
            flex: 1 !important; background: #f97316 !important; color: #431407 !important; border: 3px solid #c2410c !important; 
            font-weight: 900 !important; font-size: 0.85rem !important; border-radius: 8px !important; padding: 10px 16px !important;
            cursor: pointer !important; transition: all 0.2s ease !important; display: flex !important; align-items: center !important; justify-content: center !important;
        }
        .tt-button:hover {
            background: #0284c7 !important; color: #ffffff !important; border-color: #0284c7 !important; 
            transform: translateY(-4px) scale(1.05) !important; box-shadow: 0 10px 20px rgba(2,132,199,0.4) !important;
        }

        /* â”€â”€â”€ 3. MARQUEE TEXT (Preserved) â”€â”€â”€ */
        .tt-subtitle {
            display: block !important; width: 100% !important; white-space: nowrap !important; overflow: hidden !important;
            background: #0f172a !important; color: #38bdf8 !important; font-family: 'Consolas', monospace !important; 
            font-size: 1.1rem !important; font-weight: 700 !important; padding: 10px 0 !important; border-radius: 8px !important;
            border: 2px solid #1e293b !important; box-shadow: inset 0 0 15px rgba(0,0,0,0.6) !important;
            animation: marqueeText 40s linear infinite !important; 
        }
        .tt-status {
            display: block !important; width: 100% !important; white-space: nowrap !important; overflow: hidden !important;
            background: #064e3b !important; color: #4ade80 !important; font-family: 'Consolas', monospace !important; 
            font-size: 1.1rem !important; font-weight: 700 !important; padding: 10px 0 !important; border-radius: 8px !important;
            border: 2px solid #065f46 !important; box-shadow: inset 0 0 15px rgba(0,0,0,0.6) !important;
            animation: marqueeText 45s linear infinite !important; animation-delay: -15s !important;
        }
        @keyframes marqueeText { 0% { text-indent: 100%; } 100% { text-indent: -100%; } }

        /* â”€â”€â”€ 4. POWERSHELL TERMINAL â”€â”€â”€ */
        .tt-changes-banner {
            background: #012456 !important; color: #eeedf0 !important; font-family: 'Consolas', monospace !important;
            border: 2px solid #1e3a8a !important; border-radius: 8px !important; padding: 12px 16px !important;
            display: flex !important; flex-direction: column !important; align-items: flex-start !important;
            gap: 8px !important; font-size: 0.9rem !important; box-shadow: inset 0 0 10px rgba(0,0,0,0.5) !important;
        }
        .tt-changes-banner details { width: 100%; margin-top: 8px; }
        .tt-changes-banner summary { cursor: pointer; color: #facc15 !important; font-weight: bold; user-select: none; }
        .tt-changes-banner ul { margin: 8px 0 0 0; padding: 8px; background: #000000 !important; border: 1px solid #1e3a8a; border-radius: 4px; list-style-type: none; max-height: 250px; overflow-y: auto; }
        .tt-changes-banner li { margin-bottom: 6px; color: #22c55e !important; white-space: pre-wrap; font-size: 0.85rem; }
        .tt-cb-label { color: #94a3b8 !important; font-weight: bold; text-transform: uppercase; }
        .tt-cb-count { background: #1e3a8a !important; padding: 2px 6px; border-radius: 4px; color: #facc15 !important; font-weight: bold; }
        .tt-cb-breakdown { display: flex; gap: 8px; flex-wrap: wrap; }
        .tt-cb-day { color: #a78bfa !important; }

        /* â”€â”€â”€ 5. NEW: LIVE SCHEDULE OVERVIEW HEADER â”€â”€â”€ */
        .live-panel-header {
            background: linear-gradient(135deg, #1e293b, #0f172a) !important;
            padding: 24px 16px !important;
            text-align: center !important;
            border-bottom: 3px solid #38bdf8 !important;
            border-radius: 12px 12px 0 0 !important;
        }
        .live-panel-header h2 {
            color: #38bdf8 !important;
            font-size: 1.6rem !important;
            font-weight: 900 !important;
            letter-spacing: 2px !important;
            text-transform: uppercase !important;
            margin-bottom: 8px !important;
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            gap: 12px !important;
        }
        /* Blinking Red LIVE Text */
        .live-panel-header h2::after {
            content: "LIVE";
            color: #ef4444 !important;
            font-size: 1rem !important;
            background: #450a0a !important;
            padding: 2px 8px !important;
            border-radius: 4px !important;
            border: 1px solid #ef4444 !important;
            animation: blinkRed 1s infinite !important;
        }
        .live-panel-header p {
            color: #cbd5e1 !important;
            font-size: 1rem !important;
            font-weight: 500 !important;
            margin: 0 !important;
        }
        @keyframes blinkRed { 0%, 100% { opacity: 1; } 50% { opacity: 0.2; } }

        /* â”€â”€â”€ 6. NEW: TIMETABLE MASTHEAD (CENTERED & BEAMING) â”€â”€â”€ */
        .tt-masthead {
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            text-align: center !important;
            background: #ffffff !important;
            padding: 24px !important;
            border-radius: 16px !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.08) !important;
            margin-bottom: 24px !important;
            border-top: 5px solid #0284c7 !important;
        }
        /* Hide duplicate school name */
        .tt-mast-school {
            display: none !important; 
        }
        .tt-title {
            font-size: 2.4rem !important;
            color: #0f172a !important;
            font-weight: 900 !important;
            margin: 0 !important;
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            gap: 20px !important;
        }
        /* Beaming Green LIVE Text */
        .tt-live {
            background: #10b981 !important;
            color: #ffffff !important;
            padding: 6px 16px !important;
            border-radius: 8px !important;
            font-size: 1.2rem !important;
            font-weight: 900 !important;
            box-shadow: 0 0 20px #10b981 !important;
            animation: pulseGreen 2s infinite !important;
        }
        @keyframes pulseGreen {
            0% { box-shadow: 0 0 10px #10b981; }
            50% { box-shadow: 0 0 25px #10b981, 0 0 40px #10b981; }
            100% { box-shadow: 0 0 10px #10b981; }
        }
        .tt-mast-line {
            font-size: 1.05rem !important;
            color: #475569 !important;
            font-weight: 600 !important;
            margin-top: 12px !important;
            background: #f8fafc !important;
            padding: 6px 16px !important;
            border-radius: 20px !important;
            border: 1px solid #e2e8f0 !important;
        }
      `}</style>

      <style>{`
        /* â”€â”€â”€ 1. BUTTONS & TOOLBAR â”€â”€â”€ */
        .tt-header { background: #ffffff; border: 2px solid #0284c7; padding: 16px; border-radius: 16px; box-shadow: 0 8px 24px rgba(2,132,199,0.15); display: flex; flex-direction: column; gap: 16px; }
        .tt-header > div:first-child { display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px; background: #f0f9ff; padding: 12px; border-radius: 12px; border: 2px solid #bae6fd; overflow: hidden; }
        
        .tt-hard-reload, .tt-dl-png, .tt-dl-pdf, .tt-highlight-toggle, .tt-nuke-cache {
            background: #f97316 !important; color: #431407 !important; border: 3px solid #c2410c !important; 
            font-weight: 900 !important; font-size: 0.75rem !important; border-radius: 8px !important; padding: 8px 12px !important;
            cursor: pointer !important; transition: all 0.2s ease !important; display: flex !important; align-items: center !important; justify-content: center !important;
        }
        .tt-hard-reload, .tt-dl-png, .tt-dl-pdf { grid-column: span 2; }
        .tt-highlight-toggle, .tt-nuke-cache { grid-column: span 3; }
        
        .tt-hard-reload:hover, .tt-dl-png:hover, .tt-dl-pdf:hover, .tt-highlight-toggle:hover, .tt-nuke-cache:hover {
            background: #0284c7 !important; color: #ffffff !important; border-color: #0284c7 !important; 
            transform: translateY(-4px) scale(1.05) !important; box-shadow: 0 10px 20px rgba(2,132,199,0.4) !important;
        }
        
        .tt-fingerprint, .tt-subtitle, .tt-status, .tt-actions, .tt-changes-banner { grid-column: span 6 !important; margin-top: 8px !important; }

        /* â”€â”€â”€ 2. REFRESH & PRINT â”€â”€â”€ */
        .tt-actions { display: flex !important; gap: 12px !important; align-items: center !important; width: 100% !important; }
        .tt-button {
            flex: 1 !important; background: #f97316 !important; color: #431407 !important; border: 3px solid #c2410c !important; 
            font-weight: 900 !important; font-size: 0.85rem !important; border-radius: 8px !important; padding: 10px 16px !important;
            cursor: pointer !important; transition: all 0.2s ease !important; display: flex !important; align-items: center !important; justify-content: center !important;
        }
        .tt-button:hover {
            background: #0284c7 !important; color: #ffffff !important; border-color: #0284c7 !important; 
            transform: translateY(-4px) scale(1.05) !important; box-shadow: 0 10px 20px rgba(2,132,199,0.4) !important;
        }

        /* â”€â”€â”€ 3. MARQUEE TEXT â”€â”€â”€ */
        .tt-subtitle {
            display: block !important; width: 100% !important; white-space: nowrap !important; overflow: hidden !important;
            background: #0f172a !important; color: #38bdf8 !important; font-family: 'Consolas', monospace !important; 
            font-size: 1.1rem !important; font-weight: 700 !important; padding: 10px 0 !important; border-radius: 8px !important;
            border: 2px solid #1e293b !important; box-shadow: inset 0 0 15px rgba(0,0,0,0.6) !important;
            animation: marqueeText 40s linear infinite !important; 
        }
        .tt-status {
            display: block !important; width: 100% !important; white-space: nowrap !important; overflow: hidden !important;
            background: #064e3b !important; color: #4ade80 !important; font-family: 'Consolas', monospace !important; 
            font-size: 1.1rem !important; font-weight: 700 !important; padding: 10px 0 !important; border-radius: 8px !important;
            border: 2px solid #065f46 !important; box-shadow: inset 0 0 15px rgba(0,0,0,0.6) !important;
            animation: marqueeText 45s linear infinite !important; animation-delay: -15s !important;
        }
        @keyframes marqueeText { 0% { text-indent: 100%; } 100% { text-indent: -100%; } }

        /* â”€â”€â”€ 4. POWERSHELL TERMINAL â”€â”€â”€ */
        .tt-changes-banner {
            background: #012456 !important; color: #eeedf0 !important; font-family: 'Consolas', monospace !important;
            border: 2px solid #1e3a8a !important; border-radius: 8px !important; padding: 12px 16px !important;
            display: flex !important; flex-direction: column !important; align-items: flex-start !important;
            gap: 8px !important; font-size: 0.9rem !important; box-shadow: inset 0 0 10px rgba(0,0,0,0.5) !important;
        }
        .tt-changes-banner details { width: 100%; margin-top: 8px; }
        .tt-changes-banner summary { cursor: pointer; color: #facc15 !important; font-weight: bold; user-select: none; }
        .tt-changes-banner ul { margin: 8px 0 0 0; padding: 8px; background: #000000 !important; border: 1px solid #1e3a8a; border-radius: 4px; list-style-type: none; max-height: 250px; overflow-y: auto; }
        .tt-changes-banner li { margin-bottom: 6px; color: #22c55e !important; white-space: pre-wrap; font-size: 0.85rem; }
        .tt-cb-label { color: #94a3b8 !important; font-weight: bold; text-transform: uppercase; }
        .tt-cb-count { background: #1e3a8a !important; padding: 2px 6px; border-radius: 4px; color: #facc15 !important; font-weight: bold; }
        .tt-cb-breakdown { display: flex; gap: 8px; flex-wrap: wrap; }
        .tt-cb-day { color: #a78bfa !important; }

        /* â”€â”€â”€ 5. LIVE SCHEDULE OVERVIEW â”€â”€â”€ */
        .live-panel-header {
            background: linear-gradient(135deg, #1e293b, #0f172a) !important;
            padding: 24px 16px !important;
            text-align: center !important;
            border-bottom: 3px solid #38bdf8 !important;
            border-radius: 12px 12px 0 0 !important;
        }
        .live-panel-header h2 {
            color: #38bdf8 !important; font-size: 1.6rem !important; font-weight: 900 !important;
            letter-spacing: 2px !important; text-transform: uppercase !important; margin-bottom: 8px !important;
            display: flex !important; justify-content: center !important; align-items: center !important; gap: 12px !important;
        }
        .live-panel-header h2::after {
            content: "LIVE"; color: #ef4444 !important; font-size: 1rem !important; background: #450a0a !important;
            padding: 2px 8px !important; border-radius: 4px !important; border: 1px solid #ef4444 !important;
            animation: blinkRed 1s infinite !important;
        }
        .live-panel-header p {
            color: #cbd5e1 !important; font-size: 1rem !important; font-weight: 500 !important; margin: 0 !important;
        }
        @keyframes blinkRed { 0%, 100% { opacity: 1; } 50% { opacity: 0.2; } }

        /* â”€â”€â”€ 6. TIMETABLE MASTHEAD (REORDERED & CENTERED) â”€â”€â”€ */
        .tt-masthead {
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            text-align: center !important;
            background: #ffffff !important;
            padding: 24px !important;
            border-radius: 16px !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.08) !important;
            margin-bottom: 24px !important;
            border-top: 5px solid #0284c7 !important;
        }
        
        /* 1. Title: Master Timetable LIVE */
        .tt-title {
            order: 1 !important;
            font-size: 2.4rem !important;
            color: #0f172a !important;
            font-weight: 900 !important;
            margin: 0 0 12px 0 !important;
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            gap: 20px !important;
        }
        
        /* 2. School Name */
        .tt-mast-school {
            order: 2 !important;
            display: block !important; /* Unhidden */
            font-size: 1.3rem !important;
            font-weight: 700 !important;
            color: #475569 !important;
            text-transform: uppercase !important;
            letter-spacing: 1px !important;
            margin: 0 0 12px 0 !important;
        }
        
        /* 3. Term & Generation Info */
        .tt-mast-line {
            order: 3 !important;
            font-size: 1.05rem !important;
            color: #475569 !important;
            font-weight: 600 !important;
            margin-top: 0 !important;
            background: #f8fafc !important;
            padding: 6px 16px !important;
            border-radius: 20px !important;
            border: 1px solid #e2e8f0 !important;
        }

        /* Beaming Green LIVE */
        .tt-live {
            background: #10b981 !important; color: #ffffff !important; padding: 6px 16px !important;
            border-radius: 8px !important; font-size: 1.2rem !important; font-weight: 900 !important;
            box-shadow: 0 0 20px #10b981 !important; animation: pulseGreen 2s infinite !important;
        }
        @keyframes pulseGreen {
            0% { box-shadow: 0 0 10px #10b981; }
            50% { box-shadow: 0 0 25px #10b981, 0 0 40px #10b981; }
            100% { box-shadow: 0 0 10px #10b981; }
        }
      `}</style>

      <style>{`
        /* â”€â”€â”€ 1. BUTTONS & TOOLBAR â”€â”€â”€ */
        .tt-header { background: #ffffff; border: 2px solid #0284c7; padding: 16px; border-radius: 16px; box-shadow: 0 8px 24px rgba(2,132,199,0.15); display: flex; flex-direction: column; gap: 16px; }
        .tt-header > div:first-child { display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px; background: #f0f9ff; padding: 12px; border-radius: 12px; border: 2px solid #bae6fd; overflow: hidden; }
        .tt-hard-reload, .tt-dl-png, .tt-dl-pdf, .tt-highlight-toggle, .tt-nuke-cache { background: #f97316 !important; color: #431407 !important; border: 3px solid #c2410c !important; font-weight: 900 !important; font-size: 0.75rem !important; border-radius: 8px !important; padding: 8px 12px !important; cursor: pointer !important; transition: all 0.2s ease !important; display: flex !important; align-items: center !important; justify-content: center !important; }
        .tt-hard-reload, .tt-dl-png, .tt-dl-pdf { grid-column: span 2; }
        .tt-highlight-toggle, .tt-nuke-cache { grid-column: span 3; }
        .tt-hard-reload:hover, .tt-dl-png:hover, .tt-dl-pdf:hover, .tt-highlight-toggle:hover, .tt-nuke-cache:hover { background: #0284c7 !important; color: #ffffff !important; border-color: #0284c7 !important; transform: translateY(-4px) scale(1.05) !important; box-shadow: 0 10px 20px rgba(2,132,199,0.4) !important; }
        .tt-fingerprint, .tt-subtitle, .tt-status, .tt-actions, .tt-changes-banner { grid-column: span 6 !important; margin-top: 8px !important; }

        /* â”€â”€â”€ 2. REFRESH & PRINT â”€â”€â”€ */
        .tt-actions { display: flex !important; gap: 12px !important; align-items: center !important; width: 100% !important; }
        .tt-button { flex: 1 !important; background: #f97316 !important; color: #431407 !important; border: 3px solid #c2410c !important; font-weight: 900 !important; font-size: 0.85rem !important; border-radius: 8px !important; padding: 10px 16px !important; cursor: pointer !important; transition: all 0.2s ease !important; display: flex !important; align-items: center !important; justify-content: center !important; }
        .tt-button:hover { background: #0284c7 !important; color: #ffffff !important; border-color: #0284c7 !important; transform: translateY(-4px) scale(1.05) !important; box-shadow: 0 10px 20px rgba(2,132,199,0.4) !important; }

        /* â”€â”€â”€ 3. MARQUEE TEXT â”€â”€â”€ */
        .tt-subtitle { display: block !important; width: 100% !important; white-space: nowrap !important; overflow: hidden !important; background: #0f172a !important; color: #38bdf8 !important; font-family: 'Consolas', monospace !important; font-size: 1.1rem !important; font-weight: 700 !important; padding: 10px 0 !important; border-radius: 8px !important; border: 2px solid #1e293b !important; box-shadow: inset 0 0 15px rgba(0,0,0,0.6) !important; animation: marqueeText 40s linear infinite !important; }
        .tt-status { display: block !important; width: 100% !important; white-space: nowrap !important; overflow: hidden !important; background: #064e3b !important; color: #4ade80 !important; font-family: 'Consolas', monospace !important; font-size: 1.1rem !important; font-weight: 700 !important; padding: 10px 0 !important; border-radius: 8px !important; border: 2px solid #065f46 !important; box-shadow: inset 0 0 15px rgba(0,0,0,0.6) !important; animation: marqueeText 45s linear infinite !important; animation-delay: -15s !important; }
        @keyframes marqueeText { 0% { text-indent: 100%; } 100% { text-indent: -100%; } }

        /* â”€â”€â”€ 4. POWERSHELL TERMINAL â”€â”€â”€ */
        .tt-changes-banner { background: #012456 !important; color: #eeedf0 !important; font-family: 'Consolas', monospace !important; border: 2px solid #1e3a8a !important; border-radius: 8px !important; padding: 12px 16px !important; display: flex !important; flex-direction: column !important; align-items: flex-start !important; gap: 8px !important; font-size: 0.9rem !important; box-shadow: inset 0 0 10px rgba(0,0,0,0.5) !important; }
        .tt-changes-banner details { width: 100%; margin-top: 8px; }
        .tt-changes-banner summary { cursor: pointer; color: #facc15 !important; font-weight: bold; user-select: none; }
        .tt-changes-banner ul { margin: 8px 0 0 0; padding: 8px; background: #000000 !important; border: 1px solid #1e3a8a; border-radius: 4px; list-style-type: none; max-height: 250px; overflow-y: auto; }
        .tt-changes-banner li { margin-bottom: 6px; color: #22c55e !important; white-space: pre-wrap; font-size: 0.85rem; }
        .tt-cb-label { color: #94a3b8 !important; font-weight: bold; text-transform: uppercase; }
        .tt-cb-count { background: #1e3a8a !important; padding: 2px 6px; border-radius: 4px; color: #facc15 !important; font-weight: bold; }
        .tt-cb-breakdown { display: flex; gap: 8px; flex-wrap: wrap; }
        .tt-cb-day { color: #a78bfa !important; }

        /* â”€â”€â”€ 5. LIVE SCHEDULE OVERVIEW â”€â”€â”€ */
        .live-panel-header { background: linear-gradient(135deg, #1e293b, #0f172a) !important; padding: 24px 16px !important; text-align: center !important; border-bottom: 3px solid #38bdf8 !important; border-radius: 12px 12px 0 0 !important; }
        .live-panel-header h2 { color: #38bdf8 !important; font-size: 1.6rem !important; font-weight: 900 !important; letter-spacing: 2px !important; text-transform: uppercase !important; margin-bottom: 8px !important; display: flex !important; justify-content: center !important; align-items: center !important; gap: 12px !important; }
        .live-panel-header h2::after { content: "LIVE"; color: #ef4444 !important; font-size: 1rem !important; background: #450a0a !important; padding: 2px 8px !important; border-radius: 4px !important; border: 1px solid #ef4444 !important; animation: blinkRed 1s infinite !important; }
        .live-panel-header p { color: #cbd5e1 !important; font-size: 1rem !important; font-weight: 500 !important; margin: 0 !important; }
        @keyframes blinkRed { 0%, 100% { opacity: 1; } 50% { opacity: 0.2; } }

        /* â”€â”€â”€ 6. TIMETABLE MASTHEAD â”€â”€â”€ */
        .tt-masthead { display: flex !important; flex-direction: column !important; align-items: center !important; text-align: center !important; background: #ffffff !important; padding: 24px !important; border-radius: 16px !important; box-shadow: 0 10px 30px rgba(0,0,0,0.08) !important; margin-bottom: 24px !important; border-top: 5px solid #0284c7 !important; }
        
        .tt-title { font-size: 2.4rem !important; color: #0f172a !important; font-weight: 900 !important; margin: 0 0 12px 0 !important; display: flex !important; justify-content: center !important; align-items: center !important; gap: 20px !important; }
        .tt-live { background: #10b981 !important; color: #ffffff !important; padding: 6px 16px !important; border-radius: 8px !important; font-size: 1.2rem !important; font-weight: 900 !important; box-shadow: 0 0 20px #10b981 !important; animation: pulseGreen 2s infinite !important; }
        @keyframes pulseGreen { 0% { box-shadow: 0 0 10px #10b981; } 50% { box-shadow: 0 0 25px #10b981, 0 0 40px #10b981; } 100% { box-shadow: 0 0 10px #10b981; } }
        
        .tt-mast-school { font-size: 1.3rem !important; font-weight: 800 !important; color: #475569 !important; text-transform: uppercase !important; letter-spacing: 1px !important; margin: 0 0 12px 0 !important; }
        .tt-mast-line { font-size: 1.1rem !important; color: #475569 !important; font-weight: 700 !important; background: #f8fafc !important; padding: 6px 20px !important; border-radius: 20px !important; border: 1px solid #e2e8f0 !important; margin-bottom: 12px !important; }
        .tt-mast-filter { font-size: 0.95rem !important; color: #0284c7 !important; font-weight: 600 !important; background: #e0f2fe !important; padding: 4px 16px !important; border-radius: 8px !important; border: 1px solid #bae6fd !important; }
      `}</style>

      <style>{`
        /* â”€â”€â”€ BUTTONS & TOOLBAR â”€â”€â”€ */
        .tt-header { background: #ffffff; border: 2px solid #0284c7; padding: 16px; border-radius: 16px; box-shadow: 0 8px 24px rgba(2,132,199,0.15); display: flex; flex-direction: column; gap: 16px; }
        .tt-header > div:first-child { display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px; background: #f0f9ff; padding: 12px; border-radius: 12px; border: 2px solid #bae6fd; overflow: hidden; }
        .tt-hard-reload, .tt-dl-png, .tt-dl-pdf, .tt-highlight-toggle, .tt-nuke-cache { background: #f97316 !important; color: #431407 !important; border: 3px solid #c2410c !important; font-weight: 900 !important; font-size: 0.75rem !important; border-radius: 8px !important; padding: 8px 12px !important; cursor: pointer !important; transition: all 0.2s ease !important; display: flex !important; align-items: center !important; justify-content: center !important; }
        .tt-hard-reload, .tt-dl-png, .tt-dl-pdf { grid-column: span 2; }
        .tt-highlight-toggle, .tt-nuke-cache { grid-column: span 3; }
        .tt-hard-reload:hover, .tt-dl-png:hover, .tt-dl-pdf:hover, .tt-highlight-toggle:hover, .tt-nuke-cache:hover { background: #0284c7 !important; color: #ffffff !important; border-color: #0284c7 !important; transform: translateY(-4px) scale(1.05) !important; box-shadow: 0 10px 20px rgba(2,132,199,0.4) !important; }
        .tt-fingerprint, .tt-subtitle, .tt-status, .tt-actions, .tt-changes-banner { grid-column: span 6 !important; margin-top: 8px !important; }

        .tt-actions { display: flex !important; gap: 12px !important; align-items: center !important; width: 100% !important; }
        .tt-button { flex: 1 !important; background: #f97316 !important; color: #431407 !important; border: 3px solid #c2410c !important; font-weight: 900 !important; font-size: 0.85rem !important; border-radius: 8px !important; padding: 10px 16px !important; cursor: pointer !important; transition: all 0.2s ease !important; display: flex !important; align-items: center !important; justify-content: center !important; }
        .tt-button:hover { background: #0284c7 !important; color: #ffffff !important; border-color: #0284c7 !important; transform: translateY(-4px) scale(1.05) !important; box-shadow: 0 10px 20px rgba(2,132,199,0.4) !important; }

        /* â”€â”€â”€ MARQUEE TEXT â”€â”€â”€ */
        .tt-subtitle { display: block !important; width: 100% !important; white-space: nowrap !important; overflow: hidden !important; background: #0f172a !important; color: #38bdf8 !important; font-family: 'Consolas', monospace !important; font-size: 1.1rem !important; font-weight: 700 !important; padding: 10px 0 !important; border-radius: 8px !important; border: 2px solid #1e293b !important; box-shadow: inset 0 0 15px rgba(0,0,0,0.6) !important; animation: marqueeText 40s linear infinite !important; }
        .tt-status { display: block !important; width: 100% !important; white-space: nowrap !important; overflow: hidden !important; background: #064e3b !important; color: #4ade80 !important; font-family: 'Consolas', monospace !important; font-size: 1.1rem !important; font-weight: 700 !important; padding: 10px 0 !important; border-radius: 8px !important; border: 2px solid #065f46 !important; box-shadow: inset 0 0 15px rgba(0,0,0,0.6) !important; animation: marqueeText 45s linear infinite !important; animation-delay: -15s !important; }
        @keyframes marqueeText { 0% { text-indent: 100%; } 100% { text-indent: -100%; } }

        /* â”€â”€â”€ POWERSHELL TERMINAL â”€â”€â”€ */
        .tt-changes-banner { background: #012456 !important; color: #eeedf0 !important; font-family: 'Consolas', monospace !important; border: 2px solid #1e3a8a !important; border-radius: 8px !important; padding: 12px 16px !important; display: flex !important; flex-direction: column !important; align-items: flex-start !important; gap: 8px !important; font-size: 0.9rem !important; box-shadow: inset 0 0 10px rgba(0,0,0,0.5) !important; }
        .tt-changes-banner details { width: 100%; margin-top: 8px; }
        .tt-changes-banner summary { cursor: pointer; color: #facc15 !important; font-weight: bold; user-select: none; }
        .tt-changes-banner ul { margin: 8px 0 0 0; padding: 8px; background: #000000 !important; border: 1px solid #1e3a8a; border-radius: 4px; list-style-type: none; max-height: 250px; overflow-y: auto; }
        .tt-changes-banner li { margin-bottom: 6px; color: #22c55e !important; white-space: pre-wrap; font-size: 0.85rem; }
        .tt-cb-label { color: #94a3b8 !important; font-weight: bold; text-transform: uppercase; }
        .tt-cb-count { background: #1e3a8a !important; padding: 2px 6px; border-radius: 4px; color: #facc15 !important; font-weight: bold; }
        .tt-cb-breakdown { display: flex; gap: 8px; flex-wrap: wrap; }
        .tt-cb-day { color: #a78bfa !important; }

        /* â”€â”€â”€ LIVE SCHEDULE OVERVIEW â”€â”€â”€ */
        .live-panel-header { background: linear-gradient(135deg, #1e293b, #0f172a) !important; padding: 24px 16px !important; text-align: center !important; border-bottom: 3px solid #38bdf8 !important; border-radius: 12px 12px 0 0 !important; }
        .live-panel-header h2 { color: #38bdf8 !important; font-size: 1.6rem !important; font-weight: 900 !important; letter-spacing: 2px !important; text-transform: uppercase !important; margin-bottom: 8px !important; display: flex !important; justify-content: center !important; align-items: center !important; gap: 12px !important; }
        .live-panel-header h2::after { content: "LIVE"; color: #ef4444 !important; font-size: 1rem !important; background: #450a0a !important; padding: 2px 8px !important; border-radius: 4px !important; border: 1px solid #ef4444 !important; animation: blinkRed 1s infinite !important; }
        .live-panel-header p { color: #cbd5e1 !important; font-size: 1rem !important; font-weight: 500 !important; margin: 0 !important; }
        @keyframes blinkRed { 0%, 100% { opacity: 1; } 50% { opacity: 0.2; } }

        /* â”€â”€â”€ TIMETABLE MASTHEAD (CENTERED & ORDERED) â”€â”€â”€ */
        .tt-masthead { display: flex !important; flex-direction: column !important; align-items: center !important; text-align: center !important; background: #ffffff !important; padding: 24px !important; border-radius: 16px !important; box-shadow: 0 10px 30px rgba(0,0,0,0.08) !important; margin-bottom: 24px !important; border-top: 5px solid #0284c7 !important; }
        
        /* 1. Master Timetable LIVE */
        .tt-title { font-size: 2.4rem !important; color: #0f172a !important; font-weight: 900 !important; margin: 0 0 12px 0 !important; display: flex !important; justify-content: center !important; align-items: center !important; gap: 20px !important; }
        .tt-live { background: #10b981 !important; color: #ffffff !important; padding: 6px 16px !important; border-radius: 8px !important; font-size: 1.2rem !important; font-weight: 900 !important; box-shadow: 0 0 20px #10b981 !important; animation: pulseGreen 2s infinite !important; }
        @keyframes pulseGreen { 0% { box-shadow: 0 0 10px #10b981; } 50% { box-shadow: 0 0 25px #10b981, 0 0 40px #10b981; } 100% { box-shadow: 0 0 10px #10b981; } }
        
        /* 2. School Name */
        .tt-mast-school { font-size: 1.3rem !important; font-weight: 800 !important; color: #475569 !important; text-transform: uppercase !important; letter-spacing: 1px !important; margin: 0 0 12px 0 !important; }
        
        /* 3. Term & Date */
        .tt-mast-line { font-size: 1.1rem !important; color: #475569 !important; font-weight: 700 !important; background: #f8fafc !important; padding: 6px 20px !important; border-radius: 20px !important; border: 1px solid #e2e8f0 !important; margin-bottom: 12px !important; }
        
        /* 4. Filter Info */
        .tt-mast-filter { font-size: 0.95rem !important; color: #0284c7 !important; font-weight: 600 !important; background: #e0f2fe !important; padding: 4px 16px !important; border-radius: 8px !important; border: 1px solid #bae6fd !important; }
      `}</style>

      <header className="tt-header">
          <div>
            <button type="button" className="tt-hard-reload" onClick={() => window.location.reload()} title="Hard reload the whole page">&#x21BB; Hard Reload</button>
        <button type="button" className="tt-dl-png" onClick={() => void downloadTimetablePNG()} title="Download visible timetable as PNG">ðŸ“· PNG</button>
        <button type="button" className="tt-dl-pdf" onClick={() => void downloadTimetablePDF()} title="Download visible timetable as PDF">ðŸ“„ PDF</button>
        <button type="button" className="tt-highlight-toggle" onClick={() => setHighlightOn((v) => !v)} title="Toggle highlight of cells that differ from the previous load"> {highlightOn ? "âœ¦ Highlight ON" : "âœ¦ Highlight OFF"}</button>
        <button type="button" className="tt-nuke-cache" onClick={() => { localStorage.clear(); sessionStorage.clear();  if ("caches" in window) { caches.keys().then((ks) => ks.forEach((k) => caches.delete(k))); }  window.location.reload(); }} title="Clear all caches and reload"> ðŸ§¨ Nuke Cache</button><div className="tt-fingerprint"><span className="tt-fp-label">FINGERPRINT</span><span className="tt-fp-hash">{entrySignature || "--------"}</span><span className="tt-fp-ver">{version}</span>{loadedAt ? <span className="tt-fp-time">{loadedAt.toLocaleTimeString()}</span> : null}</div>
        {changesSummary ? (
          <div className="tt-changes-banner">
            <span className="tt-cb-label">CHANGES vs previous load</span>
            <span className={"tt-cb-count" + (changesSummary.total > 0 ? " has-changes" : "")}>
              {changesSummary.total} cell{changesSummary.total === 1 ? "" : "s"}
            </span>
            <span className="tt-cb-breakdown">
              {Object.entries(changesSummary.byDay)
                .sort()
                .map(([d, n]) => (
                  <span key={d} className="tt-cb-day">{d} <b>{n}</b></span>
                ))}
            </span>
            {changesSummary.samples.length > 0 ? (
              <details className="tt-cb-details">
                <summary>Show first {changesSummary.samples.length}</summary>
                <ul>
                  {changesSummary.samples.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </details>
            ) : null}
          </div>
        ) : null}

            <p className="tt-subtitle">
              {version} â€¢ 5 Days â€¢ {CLASSES.length} Classes â€¢ Backend-defined Learning Periods
            </p>
          </div>

          <div className="tt-actions">
            <div className="tt-status">
              <span className="tt-status-dot" />

              {loading
                ? "Loading timetable..."
                : `${scheduledEntries} backend entries loaded`}
            </div>

            <button
              type="button"
              className="tt-button"
              onClick={() => void loadTimetable()}
              disabled={refreshing}
            >
              <RefreshCw size={16} />
              Refresh
            </button>

            <button
              type="button"
              className="tt-button"
              onClick={() => window.print()}
            >
              <Printer size={16} />
              Print
            </button>
          </div>
        </header>

        {error ? <div className="tt-error">{error}</div> : null}

        <div style={{
          display: "flex", alignItems: "center", gap: "10px",
          padding: "10px 12px", marginBottom: "8px",
          background: "#f8fafc", border: "1px solid #d3dfeb",
          borderRadius: "6px", flexWrap: "wrap",
        }} className="no-print">
          <span style={{ fontSize: "12px", fontWeight: 800, color: "#244b72", letterSpacing: "0.06em" }}>VIEW:</span>
          <select value={filterMode} onChange={(e) => {
            const m = e.target.value as
              | "master" | "class" | "teacher" | "grade" | "subject";
            setFilterMode(m);
            if (m === "master") setFilterValue("");
            else if (m === "grade") setFilterValue("");
            else if (m === "class") setFilterValue(CLASSES[0]?.label ?? "");
            else if (m === "teacher") setFilterValue(allTeachers[0] ?? "");
            else if (m === "subject") {
              setSubjectValue((prev) => prev || allSubjects[0] || "");
            }
          }} style={{
            padding: "6px 10px", border: "1px solid #2878dc", borderRadius: "6px",
            fontWeight: 700, color: "#1262bd", background: "#fff", minWidth: "140px",
          }}>
            <option value="master">Master (all classes)</option>
            <option value="grade">Grade (E + W streams)</option>
            <option value="class">Single class</option>
            <option value="teacher">Single teacher</option>
            <option value="subject">Single subject</option>
          </select>
          {filterMode === "class" && (
            <select value={filterValue} onChange={(e) => setFilterValue(e.target.value)}
              style={{ padding: "6px 10px", border: "1px solid #2878dc", borderRadius: "6px", fontWeight: 700, color: "#1262bd", background: "#fff", minWidth: "160px" }}>
              {CLASSES.map((c) => <option key={c.label} value={c.label}>{c.label}</option>)}
            </select>
          )}
          {filterMode === "grade" && (
            <select value={selectedGrade} onChange={(e) => setSelectedGrade(e.target.value)}
              style={{ padding: "6px 10px", border: "1px solid #2878dc", borderRadius: "6px", fontWeight: 700, color: "#1262bd", background: "#fff", minWidth: "160px" }}>
              <option value="Grade 9">Grade 9</option>
              <option value="Grade 10">Grade 10</option>
              <option value="Grade 11">Grade 11</option>
              <option value="Form 4">Form 4</option>
            </select>
          )}
          {filterMode === "teacher" && (
            <select value={filterValue} onChange={(e) => setFilterValue(e.target.value)}
              style={{ padding: "6px 10px", border: "1px solid #2878dc", borderRadius: "6px", fontWeight: 700, color: "#1262bd", background: "#fff", minWidth: "160px" }}>
              {allTeachers.length === 0
                ? <option value="">(no teachers in timetable)</option>
                : allTeachers.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          )}
          {filterMode === "subject" && (
            <select value={subjectValue} onChange={(e) => setSubjectValue(e.target.value)}
              style={{ padding: "6px 10px", border: "1px solid #2878dc", borderRadius: "6px", fontWeight: 700, color: "#1262bd", background: "#fff", minWidth: "160px" }}>
              {allSubjects.length === 0
                ? <option value="">(no subjects in timetable)</option>
                : allSubjects.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          )}
          {filterMode === "grade" && (
            <button
              type="button"
              onClick={handleRegenScope}
              disabled={regenerating}
              style={{
                padding: "6px 10px",
                border: "1px solid #059669",
                borderRadius: "6px",
                fontWeight: 700,
                color: "#fff",
                background: regenerating ? "#94a3b8" : "#10b981",
                cursor: regenerating ? "not-allowed" : "pointer",
                marginLeft: "8px",
              }}
            >
              {regenerating ? "Regenerating..." : `Regenerate ${selectedGrade}`}
            </button>
          )}
          <span style={{ marginLeft: "auto", fontSize: "12px", color: "#64748b" }}>
            Showing {visibleClasses.length} of {CLASSES.length} classes Â· {scheduledEntries} of {entries.length} lessons
          </span>
        </div>
                <div className="live-panel-top-wrapper">
              <div className="live-panel-header">
                <h2>LIVE SCHEDULE OVERVIEW</h2>
                <p>Real-time active classes, teachers, and rooms.</p>
              </div>
              <ActiveSessionsPanel entriesBySlot={entriesBySlot} days={DAYS} periods={uniquePeriods} />
            </div>
            <div className="tt-masthead">
              <h1 className="tt-title">
                <span>{viewTitle.toUpperCase()}</span>
                <span className="tt-live">LIVE</span>
              </h1>
              <div className="tt-mast-school">{schoolName}</div>
              <div className="tt-mast-line">
                {termDisplay || "Current Term"} {runCompletedAt ? ` â€¢ Generated: ${new Date(runCompletedAt).toLocaleString()}` : ""}
              </div>
              <div className="tt-mast-filter">
                Showing: {viewTitle}
              </div>
            </div>

<div className="tt-table-wrap" data-tt-capture>
          

<table className="tt-table">
            <thead>
              <tr>
                <th className="tt-day-head">DAY</th>
                <th className="tt-class-head">CLASS</th>

                {COLUMNS_SAFE.map((column) => (
                  <th
                    key={column.key}
                    className={[
                      "tt-period-head",
                      column.kind === "tea" ? "tt-tea" : "",
                      column.kind === "lunch" ? "tt-lunch" : "",
                      column.kind === "prayers" ? "tt-prayers" : "",
                      column.kind === "activities" ? "tt-activities" : "",
                    ].join(" ")}
                  >
                    <span className="tt-period-label" style={{ display: "block", width: "100%", textAlign: "center", fontSize: "0.85rem", fontWeight: 800, color: "#ffffff", lineHeight: 1.1, whiteSpace: "nowrap" }}>
                      {column.label}
                    </span>

                    <span className="tt-period-time" style={{ display: "block", width: "100%", textAlign: "center", fontSize: "0.55rem", color: "#94a3b8", lineHeight: 1.1, whiteSpace: "nowrap" }}>
                      {column.time}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>

            <tbody>
              {DAYS.map((day) =>
                visibleClasses.map((classDefinition, classIndex) => (
                  <tr
                    key={`${day.code}-${shortClassLabel(classDefinition.label)}`}
                    onMouseEnter={() => setHoveredRow(day.code)}
                    onMouseLeave={() => setHoveredRow(null)}
                    className={hoveredRow === day.code ? "tt-row-hover" : ""}
                  >
                    {classIndex === 0 ? (
                      <th
                        rowSpan={visibleClasses.length}
                        className="tt-day"
                      >
                        {day.code}
                      </th>
                    ) : null}

                    <th className="tt-class">
                      {shortClassLabel(classDefinition.label)}
                    </th>

                    {COLUMNS_SAFE.map((column) => {
                      if (column.kind === "tea") {
                        return (
                          <td
                            key={column.key}
                            onMouseEnter={() => setHoveredCol(column.period || null)}
                            onMouseLeave={() => setHoveredCol(null)}
                            className={cellClass(column) + (hoveredCol === column.period ? " tt-col-hover" : "")} data-ttcell-key={(day?.code || "") + ":" + (classDefinition?.code || classDefinition?.name || "") + ":" + (column.period || 0)}
                          >
                            TEA BREAK
                          </td>
                        );
                      }

                      if (column.kind === "lunch") {
                        return (
                          <td
                            key={column.key}
                            onMouseEnter={() => setHoveredCol(column.period || null)}
                            onMouseLeave={() => setHoveredCol(null)}
                            className={cellClass(column) + (hoveredCol === column.period ? " tt-col-hover" : "")}
                          >
                            LUNCH
                          </td>
                        );
                      }

                      if (column.kind === "prayers") {
                        return (
                          <td
                            key={column.key}
                            onMouseEnter={() => setHoveredCol(column.period || null)}
                            onMouseLeave={() => setHoveredCol(null)}
                            className={cellClass(column) + (hoveredCol === column.period ? " tt-col-hover" : "")}
                          >
                            PRAYERS
                          </td>
                        );
                      }

                      if (column.kind === "activities") {
                        return (
                          <td
                            key={column.key}
                            onMouseEnter={() => setHoveredCol(column.period || null)}
                            onMouseLeave={() => setHoveredCol(null)}
                            className={cellClass(column) + (hoveredCol === column.period ? " tt-col-hover" : "")}
                          >
                            ACTIVITIES
                          </td>
                        );
                      }

                      const period = column.period || 0;

                      const rawSlotEntries = getSlotEntries(
                        day.code,
                        classDefinition,
                        period,
                      );
                      // In teacher mode, strip the block DTO so
                      // formatLesson() renders the entry's own
                      // subject instead of the whole-block label.
                      const slotEntries =
                        filterMode === "teacher"
                          ? rawSlotEntries.map((e) => ({
                              ...(e as any),
                              block: null,
                            }))
                          : rawSlotEntries;

                      const isMondayAssembly =
                        day.code === "MON" && period === 1;

                      return (
                        <td
                          key={column.key}
                          className={cellClass(column)}
                        >
                          {isMondayAssembly ? (
                            <div className="tt-lesson">
                              <span className="tt-subject">
                                ASSEMBLY
                              </span>
                            </div>
                          ) : slotEntries.length > 0 ? (
                            (() => {
                              // S1: the API supplies an authoritative `block` DTO on every
                              // entry belonging to a synchronized Grade 10 option block or a
                              // Senior School elective block. When present it is the sole
                              // display for that physical timetable cell.
                              // In teacher mode, skip the block DTO so
                              // each of the teacher's own subjects renders
                              // individually rather than being folded into
                              // the block label (which lists ALL block
                              // members, not just this teacher's).
                              const blockEntry =
                                filterMode === "teacher"
                                  ? null
                                  : slotEntries.find((e) => e.block) ?? null;
                            
                                if (blockEntry && blockEntry.block) {
                                  const blk: any = blockEntry.block;
                                  const blkMembers: any[] = Array.isArray(blk?.members) ? blk.members : [];

                                  const subjectLine =
                                    (typeof blk?.display === "string" && blk.display) ||
                                    blkMembers
                                      .map((m: any) => String(m?.subject_code ?? "").trim())
                                      .filter(Boolean)
                                      .join(" / ");

                                  const teacherLine = blkMembers
                                    .map((m: any) => String(m?.teacher_code ?? "-").trim() || "-")
                                    .join(" / ");

                                  const blkSlotKey = `${(blockEntry as any)?.day ?? day?.code ?? ""}:${(blockEntry as any)?.period_number ?? period ?? 0}`;
                                  const blkSlot = entriesBySlot?.get(blkSlotKey) || [];
                                  const roomByTeacher = new Map<string, string>();
                                  for (const e of blkSlot) {
                                    const tc = String((e as any)?.teacher_code ?? (e as any)?.teacherCode ?? "").trim();
                                    const r = roomCode(e);
                                    if (tc && r && r !== "\u2014") roomByTeacher.set(tc, r);
                                  }

                                  const roomLine = blkMembers
                                    .map((m: any) => {
                                      const tc = String(m?.teacher_code ?? "").trim();
                                      return tc ? (roomByTeacher.get(tc) ?? "") : "";
                                    })
                                    .filter(Boolean)
                                    .join(" / ");

                                  return (
                                    <div className="tt-lesson">
                                      <span className="tt-subject">{subjectLine}</span>
                                      {blk?.has_any_teacher ? (
                                        <span className="tt-teacher">{teacherLine}</span>
                                      ) : null}
                                      {roomLine ? (
                                        <span className="tt-room">{roomLine}</span>
                                      ) : null}
                                    </div>
                                  );
                                }
                            
                              return (
                                <>
                                  {slotEntries.map((entry) => {
                                    const lesson = formatLesson(entry);
                                    const rc = roomCode(entry);
                            
                                    return (
                                      <div className="tt-lesson" key={entry.id}>
                                        <span className="tt-subject">
                                          {lesson.code || lesson.name || "SUBJECT"}
                                        </span>
                            
                                        {lesson.teacher ? (
                                          <span className="tt-teacher">
                                            {displayTeacherCode(entry)}
                                          </span>
                                        ) : null}
                                        {rc ? (
                                          <span className="tt-room">{rc}</span>
                                        ) : null}
                                      </div>
                                    );
                                  })}
                                </>
                              );
                            })()
                          ) : (
                            "â€”"
                          )}
                        </td>
                      );
                    })}
                  </tr>
                )),
              )}
            </tbody>
          </table>
</div>


        {teacherRoster.length > 0 && (
          <section className="tt-teacher-roster">
            <div className="tt-tr-head">TEACHER ROSTER ({teacherRoster.length})</div>
            <div className="tt-tr-grid">
              {teacherRoster.map((t) => (
                <div key={t.code} className="tt-tr-item">
                  <b>{t.code}</b>{t.name ? ` Â· ${t.name}` : ""}
                </div>
              ))}
            </div>
          </section>
        )}


        <footer className="tt-footer">
          {/* Fresh-load badge */}
          <div className="tt-fresh-badge" title="Version currently displayed">
          <select
            className="tt-run-picker"
            value={selectedRunId}
            onChange={(e) => {
              const v = e.target.value;
              userPickedRef.current = !!v;
              // eslint-disable-next-line no-console
              console.log("[Timetable] user picked run:", v || "(auto)", "explicit:", userPickedRef.current);
              setSelectedRunId(v);
            }}
            title="Choose which generation to display"
          >
            <option value="">Newest completed (auto)</option>
            {availableRuns.map((r) => (
              <option key={r.id} value={r.id}>
                {String(r.id).slice(0, 8)} Â· {r.completed_at ? new Date(r.completed_at).toLocaleTimeString() : "-"}
              </option>
            ))}
          </select>
          <button
            className="tt-force-btn"
            type="button"
            onClick={() => void loadTimetable()}
            title="Force reload from backend"
          >
            âŸ³
          </button>
            <span className="tt-fresh-dot" />
            <span className="tt-fresh-v">{version}</span>
            {loadedAt ? (
              <span className="tt-fresh-t">
                {runCompletedAt ? `generated ${new Date(runCompletedAt).toLocaleString()}` : (loadedAt ? `loaded ${loadedAt.toLocaleTimeString()}` : "")}
              </span>
            ) : null}
          </div>
          {/* Live Now - active sessions */}
          
          <span>Subject Code Â· Teacher Code Â· Room</span>

          <span>âœ“ {scheduledEntries} backend entries</span>

          <span>All times are local time</span>
        </footer>
        </main>
    </>
  );
}

export default Timetable;