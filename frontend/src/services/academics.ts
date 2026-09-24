import http from "./http";

export type StudentEnrollmentSummary = {
  id: string;
  teaching_group_id: string;
  teaching_group_name: string;
};

export type Student = {
  id: string;
  admission_number: string;
  first_name: string;
  middle_name: string;
  last_name: string;
  full_name: string;
  gender: "" | "M" | "F";
  date_of_birth: string | null;
  admission_date: string | null;
  status: "ACTIVE" | "GRADUATED" | "TRANSFERRED" | "SUSPENDED" | "WITHDRAWN";
  is_active: boolean;
  current_enrollment: StudentEnrollmentSummary | null;
  created_at: string;
  updated_at: string;
};

export type StudentPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Student[];
};

function normalizePage(raw: unknown): StudentPage {
  if (Array.isArray(raw)) {
    return { count: raw.length, next: null, previous: null, results: raw as Student[] };
  }
  const obj = (raw ?? {}) as Record<string, unknown>;
  const results = Array.isArray(obj.results) ? (obj.results as Student[]) : [];
  return {
    count: typeof obj.count === "number" ? obj.count : results.length,
    next: (obj.next as string | null) ?? null,
    previous: (obj.previous as string | null) ?? null,
    results,
  };
}

export async function listStudents(params?: {
  search?: string;
  page?: number;
  page_size?: number;
}): Promise<StudentPage> {
  const qs = new URLSearchParams();
  if (params?.search) qs.set("search", params.search);
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  const res = await http.get(`/academics/students/${suffix}`);
  return normalizePage(res.data);
}

export async function updateStudent(
  id: string,
  patch: Partial<Pick<Student, "first_name" | "middle_name" | "last_name" | "status" | "is_active">>,
): Promise<Student> {
  const { data } = await http.patch<Student>(`/academics/students/${id}/`, patch);
  return data;
}