import http from "./http";

export type DutyShiftKind = "DAY" | "NIGHT";

export type DutyTeacher = {
  id: string;
  code: string;
  name: string;
  preference: "ANY" | "DAY_ONLY";
  day_ok: boolean;
  night_ok: boolean;
};

export type DutyCell = {
  id: string;
  week_start: string;
  week_end: string;
  shift: DutyShiftKind;
  teacher_id: string;
  teacher_name: string;
  teacher_code: string;
  notes: string;
  is_active: boolean;
} | null;

export type DutyWeek = {
  week_start: string;
  week_end: string;
  day: DutyCell;
  night: DutyCell;
};

export type DutyRoster = {
  week_start: string;
  week_end: string;
  weeks: DutyWeek[];
  eligible_teachers: DutyTeacher[];
};

export async function getDutyRoster(weekStart?: string, weeks?: number): Promise<DutyRoster> {
  const qs = new URLSearchParams();
  if (weekStart) qs.append("week_start", weekStart);
  if (weeks) qs.append("weeks", String(weeks));
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  const { data } = await http.get<DutyRoster>(`/scheduling/duty-roster/${suffix}`);
  return data;
}

export async function assignDuty(payload: {
  week_start: string; shift: DutyShiftKind; teacher_id: string; notes?: string;
}): Promise<{ ok: boolean; assignment: any }> {
  const { data } = await http.post("/scheduling/duty-roster/assign/", payload);
  return data;
}

export async function unassignDuty(id: string): Promise<void> {
  await http.delete(`/scheduling/duty-roster/${id}/`);
}

export async function setDutyPreference(teacherId: string, preference: "ANY" | "DAY_ONLY"): Promise<void> {
  await http.put(`/scheduling/duty-roster/preference/${teacherId}/`, { preference });
}

export async function autoRotateDuty(payload: {
  start: string; weeks: number; apply?: boolean;
}): Promise<{ plan: any[]; counts: Record<string, number>; applied: boolean }> {
  const { data } = await http.post("/scheduling/duty-roster/auto-rotate/", payload);
  return data;
}
