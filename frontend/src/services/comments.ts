import http from "./http";

export type ReportComment = {
  id: string;
  student: string;
  student_name: string;
  student_admission: string;
  academic_year: string;
  term: string;
  term_name: string;
  conduct: string;
  class_teacher_comment: string;
  rector_comment: string;
  mission_comment: string;
  created_at: string;
  updated_at: string;
};

export async function listAllComments(): Promise<ReportComment[]> {
  const { data } = await http.get<ReportComment[]>("/academics/report-comments/?page_size=500");
  return data;
}

export async function upsertComment(payload: {
  student: string;
  academic_year: string;
  term: string;
  conduct: string;
  class_teacher_comment: string;
  rector_comment: string;
  mission_comment: string;
}): Promise<ReportComment> {
  const { data } = await http.post<ReportComment>("/academics/report-comments/upsert/", payload);
  return data;
}