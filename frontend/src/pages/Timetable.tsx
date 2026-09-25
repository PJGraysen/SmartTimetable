import { useSearchParams } from "react-router-dom";
import { useCallback, useEffect, useMemo, useState, useRef } from "react";
import { Printer, RefreshCw } from "lucide-react";
import {
  getSchedulingRunResults,
  getSchedulingRuns,
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
    label: "Grade 10E",
    aliases: [
      "grade 10e",
      "grade 10 east",
      "10e",
      "10 east",
      "grade10e",
      "g10e",
    ],
  },
  {
    label: "Grade 10W",
    aliases: [
      "grade 10w",
      "grade 10 west",
      "10w",
      "10 west",
      "grade10w",
      "g10w",
    ],
  },
  {
    label: "Grade 9E",
    aliases: [
      "grade 9e",
      "grade 9 east",
      "9e",
      "9 east",
      "grade9e",
      "g9e",
    ],
  },
  {
    label: "Grade 9W",
    aliases: [
      "grade 9w",
      "grade 9 west",
      "9w",
      "9 west",
      "grade9w",
      "g9w",
    ],
  },
  {
    label: "Grade 8E",
    aliases: [
      "grade 8e",
      "grade 8 east",
      "8e",
      "8 east",
      "grade8e",
      "g8e",
    ],
  },
  {
    label: "Grade 8W",
    aliases: [
      "grade 8w",
      "grade 8 west",
      "8w",
      "8 west",
      "grade8w",
      "g8w",
    ],
  },
];

const COLUMNS: TimetableColumn[] = [
  {
    key: "p1",
    label: "P1",
    time: "08:00–08:40",
    kind: "lesson",
    period: 1,
  },
  {
    key: "p2",
    label: "P2",
    time: "08:40–09:20",
    kind: "lesson",
    period: 2,
  },
  {
    key: "p3",
    label: "P3",
    time: "09:20–10:00",
    kind: "lesson",
    period: 3,
  },
  {
    key: "p4",
    label: "P4",
    time: "10:00–10:40",
    kind: "lesson",
    period: 4,
  },
  {
    key: "tea",
    label: "TEA",
    time: "10:40–11:00",
    kind: "tea",
  },
  {
    key: "p5",
    label: "P5",
    time: "11:00–11:40",
    kind: "lesson",
    period: 6,
  },
  {
    key: "p6",
    label: "P6",
    time: "11:40–12:20",
    kind: "lesson",
    period: 7,
  },
  {
    key: "p7",
    label: "P7",
    time: "12:20–13:00",
    kind: "lesson",
    period: 8,
  },
  {
    key: "lunch",
    label: "LUNCH",
    time: "13:00–14:00",
    kind: "lunch",
  },
  {
    key: "p8",
    label: "P8",
    time: "14:00–14:40",
    kind: "lesson",
    period: 10,
  },
  {
    key: "p9",
    label: "P9",
    time: "14:40–15:20",
    kind: "lesson",
    period: 11,
  },
  {
    key: "p10",
    label: "P10",
    time: "15:20–16:00",
    kind: "lesson",
    period: 12,
  },
  {
    key: "prayers",
    label: "PRAYERS",
    time: "16:00–16:30",
    kind: "prayers",
  },
  {
    key: "activities",
    label: "ACTIVITIES",
    time: "16:30–17:45",
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

function asToMin(s) {
  if (!s && s !== 0) return null;
  const m = String(s).match(/(\d{1,2})[:.](\d{1,2})/);
  if (!m) return null;
  return parseInt(m[1], 10) * 60 + parseInt(m[2], 10);
}

function asPeriodRange(p) {
  if (!p || typeof p !== "object") return [null, null];
  const s = asToMin(p.start ?? p.start_time ?? p.from ?? p.time_start ?? p.begin);
  const e = asToMin(p.end ?? p.end_time ?? p.to ?? p.time_end ?? p.finish);
  return [s, e];
}

function asKeyMatchesDayPeriod(key, di, pi, dayNames, periodLabels) {
  const k = String(key);
  const kl = k.toLowerCase();
  const nums = k.match(/\d+/g) || [];
  if (nums.length >= 2) {
    const a = parseInt(nums[0], 10), b = parseInt(nums[1], 10);
    if ((a === di && b === pi) || (a === pi && b === di)) return true;
  }
  const dn = String(dayNames?.[di] ?? "").toLowerCase().slice(0, 3);
  if (dn && !kl.includes(dn)) return false;
  const pl = String(periodLabels?.[pi] ?? "").toLowerCase();
  if (pl && !kl.includes(pl)) return false;
  return dn.length > 0 || pl.length > 0;
}

function asPullEntryFields(e) {
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
  const block = entry.block ?? null;
  if (block) {
    if (!block.has_any_teacher) return "";
    return block.members
      .map((m) => m.teacher_code ?? "-")
      .join(" / ");
  }
  const raw = entry as unknown as Record<string, unknown>;
  return (
    teacherCode(entry) ||
    text(raw.teacher_number) ||
    text(raw.teacherNumber)
  );
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

function pickRoomName(x) {
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

function roomCode(x) {
  const raw = pickRoomName(x).trim();
  if (!raw) return "\u2014";
  const lower = raw.toLowerCase();
  const JUNK = new Set([
    "0","null","undefined","tba","n/a","na","-","none",
    "unassigned","no room","nan","[object object]"
  ]);
  if (JUNK.has(lower)) return "\u2014";
  if (typeof ROOM_ALIASES !== "undefined" && ROOM_ALIASES[lower]) return ROOM_ALIASES[lower];
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

  return definition.aliases.some((alias) => {
    const candidate = normalise(alias);

    return (
      group === candidate ||
      group.includes(candidate) ||
      candidate.includes(group)
    );
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
      ? block.members.map((m) => m.teacher_code ?? "-").join(" / ")
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
  const [loadedAt, setLoadedAt] = useState<Date | null>(null);
  const [availableRuns, setAvailableRuns] = useState<any[]>([]);
  const [entrySignature, setEntrySignature] = useState<string>("");
  const [changedKeys, setChangedKeys] = useState<Set<string>>(new Set());
  const [highlightOn, setHighlightOn] = useState(true);
  const [changesSummary, setChangesSummary] = useState<{
    total: number;
    byDay: Record<string, number>;
    samples: string[];
  } | null>(null);
  const prevEntryMapRef = useRef<Map<string, string> | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string>("");
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [filterMode, setFilterMode] = useState<"master" | "class" | "teacher">("master");
  const [filterValue, setFilterValue] = useState<string>("");

  const loadTimetable = useCallback(async () => {
    setRefreshing(true);
    setError("");

    try {
      const runsData = await getSchedulingRuns();
      const runs = Array.isArray(runsData) ? runsData : [];
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

      // Honor explicit pick, else newest by completed_at
      let latestRun = completed[0];
      if (selectedRunId) {
        const picked = completed.find((r: any) => r.id === selectedRunId);
        if (picked) latestRun = picked;
      }

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
      const result = await getSchedulingRunResults(latestRun.id);
      const timetableVersion = result.timetable_version;

      if (!timetableVersion) {
        setEntries([]);
        setVersion("Completed run has no timetable version");
        setError(
          "The latest completed scheduling run did not return a timetable version.",
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
        const prev = prevEntryMapRef.current;
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
  }, [selectedRunId]);

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

  async function downloadTimetablePNG() {
    try {
      await waitForRenderFlush();
      const mod = await import("html2canvas");
      const html2canvas = (mod as any).default || (mod as any);
      const el = captureTarget();
      if (!el) {
        alert("Could not find the timetable to capture.");
        return;
      }
      const canvas = await html2canvas(el, {
        scale: 2,
        backgroundColor: "#ffffff",
        useCORS: true,
        logging: false,
        // html2canvas has a bug where table-layout:auto + rowspan explodes
        // into hundreds of columns. onclone forces a stable layout on the
        // cloned DOM before it is rasterized.
        onclone: (clonedDoc: Document) => {
          clonedDoc.querySelectorAll("table").forEach((t) => {
            (t as HTMLElement).style.tableLayout = "fixed";
            (t as HTMLElement).style.width = "100%";
            (t as HTMLElement).style.minWidth = "0";
          });
          clonedDoc.querySelectorAll("th, td").forEach((c) => {
            const el = c as HTMLElement;
            el.style.whiteSpace = "normal";
            el.style.overflow = "hidden";
            el.style.maxWidth = "160px";
          });
        },
      });
      const link = document.createElement("a");
      const safe = String(version || "timetable").replace(/[^a-z0-9_-]+/gi, "_");
      link.download = safe + ".png";
      link.href = canvas.toDataURL("image/png");
      link.click();
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
      if (!el) {
        alert("Could not find the timetable to capture.");
        return;
      }
      const canvas = await html2canvas(el, {
        scale: 2,
        backgroundColor: "#ffffff",
        useCORS: true,
        logging: false,
        windowWidth: el.scrollWidth,
        windowHeight: el.scrollHeight,
        onclone: (clonedDoc: Document) => {
          clonedDoc.querySelectorAll("table").forEach((t) => {
            (t as HTMLElement).style.tableLayout = "fixed";
            (t as HTMLElement).style.width = "100%";
            (t as HTMLElement).style.minWidth = "0";
          });
          clonedDoc.querySelectorAll("th, td").forEach((c) => {
            const el = c as HTMLElement;
            el.style.whiteSpace = "normal";
            el.style.overflow = "hidden";
            el.style.maxWidth = "160px";
          });
        },
      });
      const imgData = canvas.toDataURL("image/png");
      // A3 PORTRAIT — 297 x 420 mm. Full-page fill, no margins.
      const pdf = new jsPDF({
        orientation: "portrait",
        unit: "mm",
        format: "a3",
      });
      const pw = pdf.internal.pageSize.getWidth();
      const ph = pdf.internal.pageSize.getHeight();
      pdf.addImage(imgData, "PNG", 0, 0, pw, ph);
      const safe = String(version || "timetable").replace(/[^a-z0-9_-]+/gi, "_");
      pdf.save(safe + ".pdf");
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

  const visibleEntries = useMemo(() => {
    if (filterMode === "teacher" && filterValue) {
      return entries.filter((e) => displayTeacherCode(e) === filterValue);
    }
    return entries;
  }, [entries, filterMode, filterValue]);

  const visibleClasses = useMemo(() => {
    if (filterMode === "class" && filterValue) {
      return CLASSES.filter((c) => c.label === filterValue);
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
  }, [filterMode, filterValue, visibleEntries]);

  const scheduledEntries = visibleEntries.length;


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
      <style>{`
        .tt-page {
          min-width: 0;
          width: 100%;
          padding: 18px;
          box-sizing: border-box;
          background: #ffffff;
        }

        .tt-header {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 18px;
          margin-bottom: 14px;
        }

        .tt-title {
          margin: 0;
          font-size: 24px;
          line-height: 1.1;
          font-weight: 800;
          letter-spacing: -0.4px;
          color: #12315b;
        }

        .tt-subtitle {
          margin: 5px 0 0;
          color: #718096;
          font-size: 13px;
        }

        .tt-live {
          display: inline-flex;
          align-items: center;
          margin-left: 8px;
          padding: 3px 8px;
          border-radius: 5px;
          background: #22a447;
          color: white;
          font-size: 11px;
          font-weight: 800;
          vertical-align: middle;
        }

        .tt-actions {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .tt-status {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 10px 16px;
          border: 1px solid #cfe5d5;
          border-radius: 5px;
          background: #f5fbf6;
          color: #27783b;
          font-size: 13px;
          white-space: nowrap;
        }

        .tt-status-dot {
          width: 9px;
          height: 9px;
          border-radius: 50%;
          background: #20a347;
        }

        .tt-button {
          display: inline-flex;
          align-items: center;
          gap: 7px;
          height: 40px;
          padding: 0 16px;
          border: 1px solid #2878dc;
          border-radius: 5px;
          background: white;
          color: #1262bd;
          font-weight: 700;
          cursor: pointer;
        }

        .tt-button:disabled {
          opacity: 0.6;
          cursor: wait;
        }

        .tt-table-wrap {
          width: 100%;
          overflow-x: auto;
          border: 1px solid #b9cbe0;
          box-sizing: border-box;
        }

        .tt-table {
          width: 100%;
          min-width: 1760px;
          table-layout: fixed;
          border-collapse: collapse;
          background: white;
        }

        .tt-table th,
        .tt-table td {
          border-right: 1px solid #d3dfeb;
          border-bottom: 1px solid #d3dfeb;
          padding: 0;
          box-sizing: border-box;
        }

        .tt-day-head,
        .tt-class-head {
          height: 54px;
          background: #244b72;
          color: white;
          text-align: center;
          font-size: 14px;
          font-weight: 800;
        }

        .tt-day-head {
          width: 112px;
        }

        .tt-class-head {
          width: 112px;
        }

        .tt-period-head {
          height: 54px;
          background: #edf4fa;
          color: #16263a;
          text-align: center;
          vertical-align: middle;
          font-weight: 800;
        }

        .tt-period-head .tt-period-label {
          display: block;
          font-size: 14px;
          line-height: 18px;
        }

        .tt-period-head .tt-period-time {
          display: block;
          margin-top: 2px;
          font-size: 10px;
          font-weight: 500;
          white-space: nowrap;
        }

        .tt-period-head.tt-tea {
          background: #fff8dd;
        }

        .tt-period-head.tt-lunch {
          background: #eff9e9;
        }

        .tt-period-head.tt-prayers,
        .tt-period-head.tt-activities {
          background: #f0edf9;
        }

        .tt-day {
          width: 112px;
          min-width: 112px;
          text-align: center;
          vertical-align: middle;
          background: #f5f9fd;
          color: #17366a;
          font-size: 16px;
          font-weight: 800;
        }

        .tt-class {
          width: 112px;
          min-width: 112px;
          height: 28px;
          padding-left: 8px !important;
          background: #ffffff;
          color: #1c2735;
          font-size: 12px;
          font-weight: 700;
          text-align: left;
          white-space: nowrap;
        }

        .tt-cell {
          height: 28px;
          min-height: 28px;
          background: #ffffff;
          color: #4b5563;
          text-align: center;
          vertical-align: middle;
          font-size: 10px;
          font-weight: 600;
          white-space: nowrap;
        }

        .tt-cell.tt-tea {
          background: #fff9df;
          color: #1f2937;
          font-weight: 800;
        }

        .tt-cell.tt-lunch {
          background: #eff9e9;
          color: #1f2937;
          font-weight: 800;
        }

        .tt-cell.tt-prayers,
        .tt-cell.tt-activities {
          background: #f2effa;
          color: #1f2937;
          font-weight: 800;
        }

        .tt-lesson {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 28px;
          line-height: 12px;
        }

        .tt-subject {
          font-weight: 800;
          color: #18395f;
        }

        .tt-subject-name {
          max-width: 100%;
          overflow: hidden;
          text-overflow: ellipsis;
          font-size: 8px;
          color: #59697b;
          font-weight: 600;
        }

        .tt-teacher { font-size: 11px; opacity: 0.9; font-weight: 600; }
        .tt-run-picker {
                appearance: none;
                margin: 0 0 10px 8px;
                padding: 5px 10px;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                font-size: 11px; font-weight: 700; color: #0f172a;
                background: #fff;
                cursor: pointer;
                max-width: 320px;
              }
              .tt-force-btn {
                margin: 0 0 10px 6px;
                padding: 5px 10px;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                background: #fff;
                font-size: 13px; font-weight: 800; color: #15803d;
                cursor: pointer;
                transition: all .15s ease;
              }
              .tt-force-btn:hover { background: #f0fdf4; border-color: #86efac; }
              .tt-fresh-badge {
                display: inline-flex; align-items: center; gap: 8px;
                margin: 0 0 10px 0;
                padding: 5px 10px;
                background: #f0fdf4;
                border: 1px solid #bbf7d0;
                border-radius: 999px;
                font-size: 11px; font-weight: 700;
                color: #14532d;
                letter-spacing: .02em;
              }
              .tt-fresh-dot {
                width: 7px; height: 7px; border-radius: 50%;
                background: #16a34a;
                box-shadow: 0 0 0 3px rgba(22,163,74,.18);
              }
              .tt-fresh-v { color: #14532d; }
              .tt-fresh-t { color: #64748b; font-weight: 500; }
                      .tt-fingerprint {
                display: inline-flex; align-items: center; gap: 8px;
                margin: 10px 0;
                padding: 6px 12px;
                background: #eef2ff; border: 1px solid #c7d2fe;
                border-radius: 8px;
                font-size: 11px; font-weight: 700;
                color: #3730a3;
              }
              .tt-fp-label { letter-spacing: .12em; font-size: 9px; opacity: .7; }
              .tt-fp-hash { font-family: ui-monospace, Menlo, monospace; color: #0f172a; font-weight: 800; letter-spacing: .04em; }
              .tt-fp-ver  { color: #15803d; }
              .tt-fp-time { color: #64748b; font-weight: 500; }
              .tt-hard-reload {
                margin: 10px 0 10px 10px;
                padding: 6px 12px; border-radius: 8px;
                border: 1px solid #fdba74; background: #fff7ed;
                color: #c2410c; font-weight: 800; font-size: 11px;
                cursor: pointer; transition: all .15s ease;
              }
              .tt-hard-reload:hover { background: #ffedd5; border-color: #fb923c; }
                      .tt-changes-banner {
                display: flex; align-items: center; flex-wrap: wrap; gap: 10px;
                margin: 6px 0 12px 0;
                padding: 8px 12px;
                background: #fefce8; border: 1px solid #fde68a;
                border-radius: 8px;
                font-size: 11px; font-weight: 700; color: #713f12;
              }
              .tt-cb-label { letter-spacing: .1em; font-size: 9px; opacity: .8; }
              .tt-cb-count {
                padding: 2px 10px; border-radius: 999px;
                background: #f1f5f9; color: #475569; font-weight: 800;
              }
              .tt-cb-count.has-changes { background: #16a34a; color: #fff; }
              .tt-cb-breakdown { display: flex; gap: 8px; }
              .tt-cb-day { color: #64748b; }
              .tt-cb-day b { color: #0f172a; }
              .tt-cb-details {
                margin-left: auto; font-size: 10px;
              }
              .tt-cb-details summary { cursor: pointer; color: #b45309; font-weight: 800; }
              .tt-cb-details ul {
                margin: 6px 0 0; padding: 8px 12px 8px 24px;
                background: #fff; border-radius: 6px; list-style: disc;
                font-family: ui-monospace, Menlo, monospace; font-size: 10px;
                color: #334155; max-height: 220px; overflow-y: auto;
              }
              .tt-cb-details li { margin: 2px 0; }
                      .tt-dl-png,
              .tt-dl-pdf {
                margin-left: 8px;
                padding: 6px 12px; border-radius: 8px;
                border: 1px solid #cbd5e1; background: #fff;
                font-size: 12px; font-weight: 800;
                color: #0f172a; cursor: pointer;
                transition: all .15s ease;
              }
              .tt-dl-png:hover { background: #f0fdf4; border-color: #86efac; color: #15803d; }
              .tt-dl-pdf:hover { background: #fef3c7; border-color: #fcd34d; color: #92400e; }
                      .tt-dl-png,
              .tt-dl-pdf {
                margin: 10px 0 10px 8px;
                padding: 6px 14px; border-radius: 8px;
                border: 1px solid #cbd5e1; background: #fff;
                font-size: 12px; font-weight: 800;
                color: #0f172a; cursor: pointer;
                transition: all .15s ease;
              }
              .tt-dl-png:hover { background: #f0fdf4; border-color: #86efac; color: #15803d; }
              .tt-dl-pdf:hover { background: #fef3c7; border-color: #fcd34d; color: #92400e; }
              .tt-dl-row { display: flex; gap: 8px; margin: 10px 0; }
              .tt-room {
                display: block;
                color: #15803d;
                font-size: 12px;
                font-weight: 800;
                line-height: 1.2;
                letter-spacing: 0.03em;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                max-width: 100%;
                margin-top: 2px;
              }
              .tt-subject,
              .tt-teacher,
              .tt-room {
                display: block;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                max-width: 100%;
              }
              .tt-subject { font-weight: 700; }
              .tt-teacher { font-size: 9px; opacity: 0.85; }
              td, .tt-cell, .lesson-cell { overflow: hidden; }
              .tt-room[data-empty="true"] { color: #cbd5e1; font-weight: 400; }


        .tt-elective {
          margin-top: 1px;
          padding: 1px 4px;
          border-radius: 3px;
          background: #eef3ff;
          color: #35558c;
          font-size: 7px;
          font-weight: 800;
          text-transform: uppercase;
        }

        .tt-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 4px;
          color: #718096;
          font-size: 11px;
        }

        .tt-error {
          margin: 10px 0;
          padding: 10px 12px;
          border: 1px solid #f0b5b5;
          background: #fff5f5;
          color: #a33a3a;
          font-size: 13px;
        }

        @media print {
          .tt-page {
            padding: 0;
          }

          .tt-actions {
            display: none;
          }

          .tt-table-wrap {
            overflow: visible;
            border: 1px solid #9fb4cb;
          }

          .tt-table {
            min-width: 1760px;
          }

          .tt-header {
            margin-bottom: 8px;
          }
        }
      `}</style>

      <main className="tt-page">
        <header className="tt-header">
          <div>
            <h1 className="tt-title">
              SCHOOL TIMETABLE
              <span className="tt-live">LIVE</span>
            </h1><button type="button" className="tt-hard-reload" onClick={() => window.location.reload()} title="Hard reload the whole page">&#x21BB; Hard Reload</button>
        <button type="button" className="tt-dl-png" onClick={() => void downloadTimetablePNG()} title="Download visible timetable as PNG">📷 PNG</button>
        <button type="button" className="tt-dl-pdf" onClick={() => void downloadTimetablePDF()} title="Download visible timetable as PDF">📄 PDF</button>
        <button type="button" className="tt-highlight-toggle" onClick={() => setHighlightOn((v) => !v)} title="Toggle highlight of cells that differ from the previous load"> {highlightOn ? "✦ Highlight ON" : "✦ Highlight OFF"}</button>
        <button type="button" className="tt-nuke-cache" onClick={() => { localStorage.clear(); sessionStorage.clear();  if ("caches" in window) { caches.keys().then((ks) => ks.forEach((k) => caches.delete(k))); }  window.location.reload(); }} title="Clear all caches and reload"> 🧨 Nuke Cache</button><div className="tt-fingerprint"><span className="tt-fp-label">FINGERPRINT</span><span className="tt-fp-hash">{entrySignature || "--------"}</span><span className="tt-fp-ver">{version}</span>{loadedAt ? <span className="tt-fp-time">{loadedAt.toLocaleTimeString()}</span> : null}</div>
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
              {version} • 5 Days • {CLASSES.length} Classes • Backend-defined Learning Periods
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
            const m = e.target.value as "master" | "class" | "teacher";
            setFilterMode(m);
            if (m === "master") setFilterValue("");
            else if (m === "class") setFilterValue(CLASSES[0]?.label ?? "");
            else if (m === "teacher") setFilterValue(allTeachers[0] ?? "");
          }} style={{
            padding: "6px 10px", border: "1px solid #2878dc", borderRadius: "6px",
            fontWeight: 700, color: "#1262bd", background: "#fff", minWidth: "140px",
          }}>
            <option value="master">Master (all classes)</option>
            <option value="class">Single class</option>
            <option value="teacher">Single teacher</option>
          </select>
          {filterMode === "class" && (
            <select value={filterValue} onChange={(e) => setFilterValue(e.target.value)}
              style={{ padding: "6px 10px", border: "1px solid #2878dc", borderRadius: "6px", fontWeight: 700, color: "#1262bd", background: "#fff", minWidth: "160px" }}>
              {CLASSES.map((c) => <option key={c.label} value={c.label}>{c.label}</option>)}
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
          <span style={{ marginLeft: "auto", fontSize: "12px", color: "#64748b" }}>
            Showing {visibleClasses.length} of {CLASSES.length} classes · {scheduledEntries} of {entries.length} lessons
          </span>
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
                    <span className="tt-period-label">
                      {column.label}
                    </span>

                    <span className="tt-period-time">
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
                            className={cellClass(column)} data-ttcell-key={(day?.code || "") + ":" + (classDefinition?.code || classDefinition?.name || "") + ":" + (column.period || 0)}
                          >
                            TEA BREAK
                          </td>
                        );
                      }

                      if (column.kind === "lunch") {
                        return (
                          <td
                            key={column.key}
                            className={cellClass(column)}
                          >
                            LUNCH
                          </td>
                        );
                      }

                      if (column.kind === "prayers") {
                        return (
                          <td
                            key={column.key}
                            className={cellClass(column)}
                          >
                            PRAYERS
                          </td>
                        );
                      }

                      if (column.kind === "activities") {
                        return (
                          <td
                            key={column.key}
                            className={cellClass(column)}
                          >
                            ACTIVITIES
                          </td>
                        );
                      }

                      const period = column.period || 0;

                      const slotEntries = getSlotEntries(
                        day.code,
                        classDefinition,
                        period,
                      );

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
                              const blockEntry = slotEntries.find((e) => e.block) ?? null;
                            
                              if (blockEntry && blockEntry.block) {
                                const block = blockEntry.block;
                                const teacherDisplay = block.has_any_teacher
                                  ? block.members
                                      .map((m) => m.teacher_code ?? "-")
                                      .join(" / ")
                                  : null;
                                const blockRoom = (() => {
    // Build teacher_code -> room map for this slot from all visible entries
    const blockMembers = Array.isArray((block as any)?.members) ? (block as any).members : [];
    const slotKey = `${(blockEntry as any)?.day ?? day?.code ?? ""}:${(blockEntry as any)?.period_number ?? period ?? 0}`;
    const allSlot = entriesBySlot?.get(slotKey) || [];
    const roomForTeacher = new Map<string, string>();
    for (const e of allSlot) {
      const tc = String((e as any)?.teacher_code ?? (e as any)?.teacherCode ?? "").trim();
      const r = roomCode(e);
      if (tc && r && r !== "\u2014") roomForTeacher.set(tc, r);
    }
    // Ordered join: one room per block member, in member order
    const ordered: string[] = [];
    const seen = new Set<string>();
    for (const mb of blockMembers) {
      const tc = String(mb?.teacher_code ?? mb?.teacherCode ?? "").trim();
      const r = tc ? roomForTeacher.get(tc) : "";
      if (r && !seen.has(r)) { seen.add(r); ordered.push(r); }
    }
    if (ordered.length === 0) {
      const single = roomCode(blockEntry);
      if (single && single !== "\u2014") ordered.push(single);
    }
    return ordered.join(" / ");
  })();
                            
                                return (
                                  <div className="tt-lesson">
                                    <span className="tt-subject">{block.display}</span>
                                    {teacherDisplay ? (
                                      <span className="tt-teacher">{teacherDisplay}</span>
                                    ) : null}
                                    {blockRoom ? (
                                      <span className="tt-room">{blockRoom}</span>
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
                            "—"
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

        <footer className="tt-footer">
          {/* Fresh-load badge */}
          <div className="tt-fresh-badge" title="Version currently displayed">
          <select
            className="tt-run-picker"
            value={selectedRunId}
            onChange={(e) => setSelectedRunId(e.target.value)}
            title="Choose which generation to display"
          >
            <option value="">Newest completed (auto)</option>
            {availableRuns.map((r) => (
              <option key={r.id} value={r.id}>
                {String(r.id).slice(0, 8)} · {r.completed_at ? new Date(r.completed_at).toLocaleTimeString() : "-"}
              </option>
            ))}
          </select>
          <button
            className="tt-force-btn"
            type="button"
            onClick={() => void loadTimetable()}
            title="Force reload from backend"
          >
            ⟳
          </button>
            <span className="tt-fresh-dot" />
            <span className="tt-fresh-v">{version}</span>
            {loadedAt ? (
              <span className="tt-fresh-t">
                loaded {loadedAt.toLocaleTimeString()}
              </span>
            ) : null}
          </div>
          {/* Live Now - active sessions */}
          <ActiveSessionsPanel entriesBySlot={entriesBySlot} days={DAYS} />
          <span>Subject Code · Teacher Code · Room</span>

          <span>✓ {scheduledEntries} backend entries</span>

          <span>All times are local time</span>
        </footer>
      </main>
    </>
  );
}

export default Timetable;