import http from "./http";

export type AcademicTerm = {
  id: string;
  name: string;
  academic_year: string;
  academic_year_name: string;
  number: number;
  start_date: string;
  end_date: string;
  is_active: boolean;
};

export type InstructionalGroup = {
  id: string;
  teaching_group: string;
  teaching_group_name: string;
  grade_name: string;
  stream_name: string;
  name: string;
  code: string;
  learner_count: number;
  is_active: boolean;
};

export async function getInstructionalGroups() {
  const response = await http.get<InstructionalGroup[]>(
    "/academics/instructional-groups/",
  );
  return response.data;
}

export async function getAcademicTerms() {
  const response = await http.get<AcademicTerm[]>("/core/terms/");
  return response.data;
}
