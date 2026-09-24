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

export async function deleteTeacher(id: string): Promise<void> {
  await http.delete(`/platform/admin/teachers/${id}/`);
}

export async function teacherAction(id: string, action: "freeze" | "unfreeze" | "activate" | "deactivate"): Promise<TeacherRow> {
  const { data } = await http.post<TeacherRow>(`/platform/admin/teachers/${id}/${action}/`);
  return data;
}