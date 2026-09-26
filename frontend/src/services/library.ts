import http from "./http";

export type Author = { id: string; name: string; sort_name: string };
export type Publisher = {
  id: string; name: string; address: string;
  contact_email: string; contact_phone: string;
};
export type Category = { id: string; name: string; code: string; description: string };
export type Shelf = {
  id: string; code: string; name: string; description: string; location_hint: string;
};

export type Book = {
  id: string;
  isbn: string;
  title: string;
  subtitle: string;
  edition: string;
  language: string;
  description: string;
  publisher: Publisher | null;
  published_year: number | null;
  cover_url: string;
  authors: Author[];
    subjects?: Subject[];
  categories: Category[];
  is_active: boolean;
  copy_count: number;
  available_copy_count: number;
};

export type CopyStatus =
  | "AVAILABLE" | "ISSUED" | "RESERVED" | "LOST" | "DAMAGED" | "REPAIR";
export type CopyCondition = "NEW" | "GOOD" | "FAIR" | "WORN";

export type Copy = {
  id: string;
  book: string;
  book_title: string;
  barcode: string;
  accession_number: string;
  shelf: string | null;
  status: CopyStatus;
  condition: CopyCondition;
  acquired_at: string | null;
  acquisition_cost: string | null;
  replacement_cost: string | null;
  notes: string;
};

export type MemberType = "STUDENT" | "TEACHER" | "STAFF" | "EXTERNAL";

export type Member = {
  id: string;
  member_number: string;
  user: number | null;
  full_name: string;
  email: string;
  phone: string;
  member_type: MemberType;
  is_active: boolean;
  joined_at: string;
  notes: string;
};

export type LoanStatus = "ACTIVE" | "RETURNED" | "LOST";

export type Loan = {
  id: string;
  copy: string;
  copy_barcode: string;
  book_title: string;
  member: string;
  member_number: string;
  member_name: string;
  issued_at: string;
  due_at: string;
  returned_at: string | null;
  status: LoanStatus;
  renewal_count: number;
  fine_accrued: string;
  fine_paid: string;
  is_overdue: boolean;
  overdue_days: number;
  notes: string;
};

export type LoanRule = {
  id: string;
  member_type: MemberType;
  max_concurrent_loans: number;
  loan_days: number;
  max_renewals: number;
  fine_per_day: string;
  grace_days: number;
  max_fine: string | null;
};

export type LibraryDashboard = {
  total_books: number;
  total_copies: number;
  available_copies: number;
  issued_copies: number;
  active_loans: number;
  overdue_loans: number;
  active_members: number;
};

const base = "/library";

// ---------- dashboard ----------
export async function getDashboard() {
  return (await http.get<LibraryDashboard>(`${base}/dashboard/`)).data;
}

// ---------- books ----------
export async function listBooks(params: { q?: string; subject?: string } = {}) {
  const query: Record<string, string> = {};
  if (params.q) query.q = params.q;
  if (params.subject) query.subject = params.subject;
  const r = await http.get(`${base}/books/`, { params: query });
  const data: any = r.data;
  return Array.isArray(data) ? data : (data.results ?? []) as Book[];
}
export async function getBook(id: string) {
  return (await http.get<Book>(`${base}/books/${id}/`)).data;
}
export async function createBook(payload: Partial<Book>) {
  return (await http.post<Book>(`${base}/books/`, payload)).data;
}
export async function updateBook(id: string, payload: Partial<Book>) {
  return (await http.patch<Book>(`${base}/books/${id}/`, payload)).data;
}
export async function listBookCopies(bookId: string) {
  return (await http.get<Copy[]>(`${base}/books/${bookId}/copies/`)).data;
}
export async function createCopy(bookId: string, payload: Partial<Copy>) {
  return (await http.post<Copy>(`${base}/books/${bookId}/copies/`, payload)).data;
}

// ---------- copies ----------
export async function listCopies(params: { status?: string; book?: string } = {}) {
  const query: Record<string, string> = {};
  if (params.status) query.status = params.status;
  if (params.book) query.book = params.book;
  const r = await http.get(`${base}/copies/`, { params: query });
  const data: any = r.data;
  return Array.isArray(data) ? data : (data.results ?? []) as Copy[];
}
export async function getCopyByBarcode(barcode: string) {
  return (await http.get<Copy>(`${base}/copies/by-barcode/${encodeURIComponent(barcode)}/`)).data;
}

// ---------- authors / publishers / categories / shelves ----------
export async function listAuthors() {
  const r = await http.get(`${base}/authors/`);
  const d: any = r.data; return Array.isArray(d) ? d : d.results ?? [];
}
export async function listPublishers() {
  const r = await http.get(`${base}/publishers/`);
  const d: any = r.data; return Array.isArray(d) ? d : d.results ?? [];
}
export async function listCategories() {
  const r = await http.get(`${base}/categories/`);
  const d: any = r.data; return Array.isArray(d) ? d : d.results ?? [];
}
export async function listShelves() {
  const r = await http.get(`${base}/shelves/`);
  const d: any = r.data; return Array.isArray(d) ? d : d.results ?? [];
}

// ---------- members ----------
export async function listMembers(params: { q?: string; type?: string } = {}) {
  const query: Record<string, string> = {};
  if (params.q) query.q = params.q;
  if (params.type) query.type = params.type;
  const r = await http.get(`${base}/members/`, { params: query });
  const d: any = r.data; return Array.isArray(d) ? d : d.results ?? [] as Member[];
}
export async function getMember(id: string) {
  return (await http.get<Member>(`${base}/members/${id}/`)).data;
}
export async function createMember(payload: Partial<Member>) {
  return (await http.post<Member>(`${base}/members/`, payload)).data;
}
export async function updateMember(id: string, payload: Partial<Member>) {
  return (await http.patch<Member>(`${base}/members/${id}/`, payload)).data;
}
export async function memberLoans(id: string) {
  return (await http.get<Loan[]>(`${base}/members/${id}/loans/`)).data;
}

// ---------- loans ----------
export async function listLoans(params: { status?: string; member?: string } = {}) {
  const query: Record<string, string> = {};
  if (params.status) query.status = params.status;
  if (params.member) query.member = params.member;
  const r = await http.get(`${base}/loans/`, { params: query });
  const d: any = r.data; return Array.isArray(d) ? d : d.results ?? [] as Loan[];
}
export async function issueLoan(payload: { copy: string; member: string }) {
  return (await http.post<Loan>(`${base}/loans/issue/`, payload)).data;
}
export async function returnLoan(id: string) {
  return (await http.post<Loan>(`${base}/loans/${id}/return/`, {})).data;
}
export async function renewLoan(id: string) {
  return (await http.post<Loan>(`${base}/loans/${id}/renew/`, {})).data;
}

// ---------- rules ----------
export async function listRules() {
  const r = await http.get(`${base}/rules/`);
  const d: any = r.data; return Array.isArray(d) ? d : d.results ?? [];
}
export async function updateRule(id: string, payload: Partial<LoanRule>) {
  return (await http.patch<LoanRule>(`${base}/rules/${id}/`, payload)).data;
}

// ---------- reports ----------
export async function reportCirculation() {
  return (await http.get(`${base}/reports/circulation/`)).data;
}
export async function reportOverdue() {
  return (await http.get<Loan[]>(`${base}/reports/overdue/`)).data;
}
export async function reportInventory() {
  return (await http.get<{ by_status: { status: string; count: number }[] }>(
    `${base}/reports/inventory/`,
  )).data;
}
export async function reportTopBorrowers() {
  return (await http.get<{
    id: string; member_number: string; full_name: string; loan_count: number;
  }[]>(`${base}/reports/top-borrowers/`)).data;
}


// --- Cataloguing: ISBN metadata lookup (L1) ---
export type BookLookupResult = {
  found: boolean;
  isbn: string;
  title?: string;
  subtitle?: string;
  authors?: string[];
  publisher?: string;
  published_year?: number | null;
  edition?: string;
  language?: string;
  description?: string;
  cover_url?: string;
  page_count?: number | null;
  ddc?: string;
  lcc?: string;
  toc?: string;
  source?: string;
  source_id?: string;
};

export async function lookupBookByIsbn(isbn: string): Promise<BookLookupResult> {
  const { data } = await http.get("/library/catalogue/lookup/", {
    params: { isbn },
  });
  return data as BookLookupResult;
}


// --- L1 subjects (learning categories) ---
export type Subject = { id: string; name: string; code: string };

export type SubjectSummaryRow = {
  id: string;
  name: string;
  code: string;
  book_count: number;
  available_copies: number;
};

export async function getSubjects(): Promise<Subject[]> {
  const { data } = await http.get("/library/catalogue/subjects/");
  return (data?.subjects ?? []) as Subject[];
}

export async function getSubjectSummary(): Promise<SubjectSummaryRow[]> {
  const { data } = await http.get("/library/catalogue/subject-summary/");
  return (data?.subjects ?? []) as SubjectSummaryRow[];
}


// ================================================================
// L2 — Circulation quick actions
// ================================================================
export async function selfCheckout(payload: { barcode: string; member_number: string }) {
  const { data } = await http.post("/library/circulation/self-checkout/", payload);
  return data as { ok: boolean; loan_id: string; book_title: string; member_name: string; due_at: string };
}

export async function bulkReturn(barcodes: string[]) {
  const { data } = await http.post("/library/circulation/bulk-return/", { barcodes });
  return data as {
    processed: number;
    succeeded: number;
    results: { barcode: string; ok: boolean; error: string }[];
  };
}

// ================================================================
// L5 — Faceted catalogue search
// ================================================================
export type CatalogueSearchRow = {
  id: string;
  title: string;
  subtitle: string;
  isbn: string;
  published_year: number | null;
  cover_url: string;
  authors: { id: string; name: string }[];
  subjects: { id: string; name: string; code: string }[];
  publisher: string;
  copy_count: number;
  available_copy_count: number;
};

export type CatalogueSearchParams = {
  q?: string;
  subject?: string;
  author?: string;
  year_from?: string | number;
  year_to?: string | number;
  availability?: "available" | "";
};

export async function catalogueSearch(params: CatalogueSearchParams = {}) {
  const { data } = await http.get("/library/catalogue/search/", { params });
  return data as { results: CatalogueSearchRow[]; count: number };
}

// ================================================================
// L7 — Report export
// ================================================================
export function reportExportUrl(reportName: string, format: "csv" | "json" = "csv"): string {
  const base = (http.defaults?.baseURL || "/api").replace(/\/$/, "");
  return `${base}/library/reports/${reportName}/export/?format=${format}`;
}

export async function downloadReport(reportName: string, format: "csv" | "json" = "csv") {
  const { data } = await http.get(`/library/reports/${reportName}/export/`, {
    params: { format },
    responseType: format === "csv" ? "blob" : "json",
  });
  return data;
}
