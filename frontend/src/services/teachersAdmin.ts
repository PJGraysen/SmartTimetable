import http from "./http";

export type TeacherRow = {
  id: string;
  employee_code: string;
  teacher_number: number | null;
  first_name: string;
  last_name: string;
  full_name: string;
  username: string | null;
  email: string | null;
  is_active: boolean;
  is_frozen: boolean;
  lr_count: number;
  assignments: string[];
};

export async function listTeachers(q?: string): Promise<{ count: number; results: TeacherRow[] }> {
  const suffix = q ? `?q=${encodeURIComponent(q)}` : "";
  const { data } = await http.get(`/platform/admin/teachers/${suffix}`);
  return data;
}

export async function updateTeacher(id: string, patch: Partial<TeacherRow>): Promise<TeacherRow> {
  const { data } = await http.patch<TeacherRow>(`/platform/admin/teachers/${id}/`, patch);
  return data;
}

export async function deleteTeacher(id: string): Promise<{ ok: boolean; deleted_assignments?: number }> {
  // Dedicated endpoint avoids router <pk>/ shadowing
  const { data } = await http.delete(`/platform/admin/teachers/${id}/delete/`);
  return data || { ok: true };
}

export async function teacherAction(id: string, action: "freeze" | "unfreeze" | "activate" | "deactivate"): Promise<TeacherRow> {
  const { data } = await http.post<TeacherRow>(`/platform/admin/teachers/${id}/${action}/`);
  return data;
}
// ---------- Phase 2: assignments ----------
export type Assignment = {
  id: string;
  subject_id: number;
  subject_code: string | null;
  subject_name: string | null;
  class_id: string;
  class_name: string | null;
  lessons_per_week: number;
  requirement_type: string | null;
  is_active: boolean;
};

export type AssignmentsResponse = {
  teacher_id: string;
  full_name: string;
  employee_code: string;
  teacher_number: number | null;
  total_lessons: number;
  capacity: number;
  assignments: Assignment[];
};

export async function getTeacherAssignments(id: string): Promise<AssignmentsResponse> {
  const { data } = await http.get<AssignmentsResponse>(`/platform/admin/teachers/${id}/assignments/`);
  return data;
}

export async function assignTeacher(
  id: string,
  payload: { subject_id: number; class_id: string; lessons_per_week: number; requirement_type?: string },
): Promise<{ ok: boolean; assignment: Assignment }> {
  const { data } = await http.post(`/platform/admin/teachers/${id}/assign/`, payload);
  return data;
}

export async function unassignTeacher(id: string, lrId: string): Promise<void> {
  await http.delete(`/platform/admin/teachers/${id}/assign/${lrId}/`);
}

export async function createTeacher(payload: {
  employee_code: string;
  first_name: string;
  last_name: string;
  teacher_number?: number | null;
  email?: string;
  username?: string;
  password?: string;
}): Promise<{ ok: boolean; id: string }> {
  const { data } = await http.post("/platform/admin/teachers/create/", payload);
  return data;
}

export async function listSubjects(): Promise<{ results: { id: number; code: string; name: string }[] }> {
  const { data } = await http.get("/platform/admin/subjects/");
  return data;
}

export async function listClasses(): Promise<{ results: { id: string; name: string; is_active: boolean }[] }> {
  const { data } = await http.get("/platform/admin/classes/");
  return data;
}

// ---------- Stage 2: extended profile + bulk assign ----------
export async function listDepartments(): Promise<{ results: { id: number; code: string; name: string }[] }> {
  const { data } = await http.get("/inventory/departments/");
  const raw = Array.isArray(data) ? data : (data?.results || []);
  return { results: raw.map((d: any) => ({ id: d.id, code: d.code, name: d.name })) };
}

export const ROLE_OPTIONS = [
  { value: "SUPER_ADMIN", label: "Super Admin (full access)" },
  { value: "PRINCIPAL",   label: "Principal / Rector" },
  { value: "SECRETARY",   label: "Secretary" },
  { value: "DEPT_HEAD",   label: "Department Head" },
  { value: "TEACHER",     label: "Teacher" },
  { value: "LAB_TECH",    label: "Lab Technician" },
  { value: "AUDITOR",     label: "Internal Auditor" },
  { value: "PROCUREMENT", label: "Procurement Officer" },
  { value: "LIBRARIAN",   label: "Librarian" },
  { value: "BURSAR",      label: "Bursar" },
  { value: "OTHER",       label: "Other Staff" },
];

export async function updateTeacherProfile(
  id: string,
  patch: {
    first_name?: string;
    last_name?: string;
    employee_code?: string;
    teacher_number?: number | null;
    email?: string;
    phone?: string;
    role?: string;
    department_id?: number | null;
    hire_date?: string | null;
  },
): Promise<{ ok: boolean; updated: string[] }> {
  const { data } = await http.patch(`/platform/admin/teachers/${id}/profile/`, patch);
  return data;
}

export async function bulkAssignTeacher(
  id: string,
  payload: {
    subject_id: number;
    class_ids: string[];
    lessons_per_week: number;
    requirement_type?: string;
  },
): Promise<{
  ok: boolean;
  results: { class_id: string; class_name?: string; status: string; from?: number; to?: number }[];
  teacher_new_load: number;
  capacity: number;
  over_capacity: boolean;
}> {
  const { data } = await http.post(`/platform/admin/teachers/${id}/bulk-assign/`, payload);
  return data;
}


// ---------- Session 1: free afternoon + retire ----------
export type FreeAfternoon = {
  day: "MON" | "TUE" | "WED" | "THU" | "FRI" | null;
  term: string;
  term_id: string;
};

export async function getFreeAfternoon(id: string): Promise<FreeAfternoon> {
  const { data } = await http.get<FreeAfternoon>(
    `/platform/admin/teachers/${id}/free-afternoon/`,
  );
  return data;
}

export async function setFreeAfternoon(
  id: string,
  day: "MON" | "TUE" | "WED" | "THU" | "FRI" | null,
): Promise<{ ok: boolean; day: string | null }> {
  const { data } = await http.put(
    `/platform/admin/teachers/${id}/free-afternoon/`,
    { day },
  );
  return data;
}

export async function retireTeacher(id: string): Promise<{ ok: boolean; retired?: boolean; detail?: string }> {
  const { data } = await http.post(
    `/platform/admin/teachers/${id}/retire/`,
  );
  return data;
}

export async function reactivateTeacher(id: string): Promise<{ ok: boolean; reactivated?: boolean }> {
  const { data } = await http.post(
    `/platform/admin/teachers/${id}/reactivate/`,
  );
  return data;
}


// ---------- Session 4: merge / dedup ----------
export type DupTeacher = {
  id: string;
  code: string;
  name: string;
  role: string;
  is_active: boolean;
  lr_count: number;
  email: string;
};

export type DupCandidate = {
  reason: string;
  a: DupTeacher;
  b: DupTeacher;
};

export async function scanTeacherDuplicates(): Promise<{ count: number; candidates: DupCandidate[] }> {
  const { data } = await http.get("/platform/admin/teachers/duplicates/");
  return data;
}

export async function mergeTeachers(
  keepId: string, dropId: string,
): Promise<{
  ok: boolean;
  kept: { id: string; code: string; name: string };
  dropped: { id: string; code: string; name: string };
  relinked: Record<string, number>;
}> {
  const { data } = await http.post("/platform/admin/teachers/merge/", {
    keep_id: keepId, drop_id: dropId,
  });
  return data;
}
