import http from "./http";

export type AssessmentFull = {
  id: string;
  name: string;
  assessment_type: string;
  date: string;
  max_mark: number;
  status: string;
};

export type SubjectLite = {
  id: string;
  name: string;
  code: string;
  is_active: boolean;
};

export type RosterEntry = {
  student_id: string;
  admission_number: string;
  name: string;
  raw_mark: number | null;
  status: string;
};

export async function listAssessments(): Promise<AssessmentFull[]> {
  const { data } = await http.get<AssessmentFull[]>("/academics/assessments/");
  return data;
}

export async function createAssessment(payload: {
  name: string;
  assessment_type: string;
  date: string;
  max_mark: number;
}): Promise<AssessmentFull> {
  const { data } = await http.post<AssessmentFull>("/academics/assessments/", payload);
  return data;
}

export async function updateAssessment(
  id: string,
  patch: Partial<AssessmentFull>,
): Promise<AssessmentFull> {
  const { data } = await http.patch<AssessmentFull>(`/academics/assessments/${id}/`, patch);
  return data;
}

export async function deleteAssessment(id: string): Promise<void> {
  await http.delete(`/academics/assessments/${id}/`);
}

export async function setAssessmentStatus(
  id: string,
  action: "publish" | "archive" | "draft" | "open-marks",
): Promise<AssessmentFull> {
  const { data } = await http.post<AssessmentFull>(`/academics/assessments/${id}/${action}/`);
  return data;
}

export async function listSubjects(): Promise<SubjectLite[]> {
  const { data } = await http.get<SubjectLite[]>("/academics/subjects/");
  return data;
}

export async function fetchRoster(assessmentId: string, subjectId: string): Promise<RosterEntry[]> {
  const { data } = await http.get<RosterEntry[]>(
    `/academics/results/roster/?assessment=${assessmentId}&subject=${subjectId}`,
  );
  return data;
}

export async function saveBulkMarks(payload: {
  assessment: string;
  subject: string;
  marks: Array<{ student_id: string; raw_mark: number | null; status: string }>;
}): Promise<{ created: number; updated: number }> {
  const { data } = await http.post<{ created: number; updated: number }>(
    "/academics/results/bulk/",
    payload,
  );
  return data;
}


export type MarksContext = {
  is_admin: boolean;
  teacher_name: string | null;
  classes: Array<{ id: string; name: string }>;
  subjects_by_class: Record<string, Array<{ id: string; name: string; code: string }>>;
};

export async function fetchMarksContext(): Promise<MarksContext> {
  const { data } = await http.get<MarksContext>("/academics/marks-entry/context/");
  return data;
}

// roster with optional class filter
export async function fetchRosterForClass(
  assessmentId: string,
  subjectId: string,
  teachingGroupId: string,
): Promise<RosterEntry[]> {
  const qs = new URLSearchParams({
    assessment: assessmentId,
    subject: subjectId,
    teaching_group: teachingGroupId,
  });
  const { data } = await http.get<RosterEntry[]>(`/academics/results/roster/?${qs.toString()}`);
  return data;
}
