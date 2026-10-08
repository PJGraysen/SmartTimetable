import { useEffect, useState } from "react";
import {
  AlertCircle, BookOpen, Calendar, CheckCircle2, Clock, TrendingUp,
} from "lucide-react";
import http from "../services/http";

type LoanRow = {
  id: number | string;
  book_title: string;
  book_author: string;
  borrowed_at: string | null;
  due_at: string | null;
  returned_at: string | null;
  status: string;
  fine_amount?: number;
};

type Stats = {
  total_borrowed: number;
  active: number;
  overdue: number;
  returned: number;
  fines_pending: number;
  fines_paid: number;
};

const EMPTY_STATS: Stats = {
  total_borrowed: 0, active: 0, overdue: 0, returned: 0,
  fines_pending: 0, fines_paid: 0,
};

function fmt(s: string | null | undefined): string {
  if (!s) return "—";
  try { return new Date(s).toLocaleDateString(); } catch { return "—"; }
}

export default function MyReportsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [loans, setLoans] = useState<LoanRow[]>([]);
  const [stats, setStats] = useState<Stats>(EMPTY_STATS);

  useEffect(() => {
    let alive = true;
    const fetchAll = async () => {
      try {
        // Try dedicated "my loans" endpoint first
        let data: any = null;
        try {
          const r = await http.get("/library/loans/mine/");
          data = r.data;
        } catch {
          // Fallback to general loans endpoint
          try {
            const r = await http.get("/library/loans/");
            data = r.data;
          } catch {
            data = null;
          }
        }

        if (!alive) return;

        if (!data) {
          setError("Reports will appear here once you've borrowed a book.");
          setLoading(false);
          return;
        }

        // Normalize — support both { loans, stats } and array response
        const list: LoanRow[] = Array.isArray(data)
          ? data
          : Array.isArray(data?.loans)
          ? data.loans
          : Array.isArray(data?.results)
          ? data.results
          : [];

        setLoans(list);

        if (data?.stats && typeof data.stats === "object") {
          setStats({ ...EMPTY_STATS, ...data.stats });
        } else {
          // Derive stats client-side
          const active = list.filter((l) => l.status === "ACTIVE").length;
          const overdue = list.filter((l) => l.status === "OVERDUE").length;
          const returned = list.filter((l) => l.status === "RETURNED").length;
          const fines = list.reduce((s, l) => s + (Number(l.fine_amount) || 0), 0);
          setStats({
            total_borrowed: list.length,
            active, overdue, returned,
            fines_pending: overdue > 0 ? fines : 0,
            fines_paid: overdue === 0 ? fines : 0,
          });
        }
      } catch (e: any) {
        if (alive) {
          setError(e?.response?.data?.detail || "Could not load reports.");
        }
      } finally {
        if (alive) setLoading(false);
      }
    };
    fetchAll();
    return () => { alive = false; };
  }, []);

  if (loading) {
    return (
      <div className="mr-page">
        <div className="mr-empty">Loading your reports…</div>
      </div>
    );
  }

  return (
    <div className="mr-page">
      <header className="mr-head">
        <h1>My Library Reports</h1>
        <p className="mr-sub">Your borrowing history, active loans, and fines.</p>
      </header>

      {error && (
        <div className="mr-empty" style={{ marginBottom: "1rem" }}>
          <AlertCircle size={24} />
          <p style={{ margin: "6px 0 0" }}>{error}</p>
        </div>
      )}

      <section className="mr-stats">
        <div className="mr-stat-card">
          <BookOpen size={18} />
          <div><span>Total borrowed</span><b>{stats.total_borrowed}</b></div>
        </div>
        <div className="mr-stat-card">
          <Clock size={18} />
          <div><span>Active</span><b>{stats.active}</b></div>
        </div>
        <div className="mr-stat-card mr-stat-warn">
          <AlertCircle size={18} />
          <div><span>Overdue</span><b>{stats.overdue}</b></div>
        </div>
        <div className="mr-stat-card mr-stat-good">
          <CheckCircle2 size={18} />
          <div><span>Returned</span><b>{stats.returned}</b></div>
        </div>
      </section>

      <section className="mr-fines">
        <div className="mr-fine">
          <span>Fines pending</span>
          <b className={stats.fines_pending > 0 ? "mr-bad" : ""}>
            KES {Number(stats.fines_pending || 0).toLocaleString()}
          </b>
        </div>
        <div className="mr-fine">
          <span>Fines paid</span>
          <b className="mr-good">
            KES {Number(stats.fines_paid || 0).toLocaleString()}
          </b>
        </div>
      </section>

      <h2 className="mr-section">Loan history</h2>
      {loans.length === 0 ? (
        <div className="mr-empty">
          <Calendar size={26} />
          <p style={{ margin: "6px 0 0" }}>No loans on record yet.</p>
        </div>
      ) : (
        <div className="mr-table-wrap">
          <table className="mr-table">
            <thead>
              <tr>
                <th>Book</th>
                <th>Borrowed</th>
                <th>Due</th>
                <th>Returned</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {loans.map((l) => (
                <tr key={String(l.id)}>
                  <td>
                    <div className="mr-book-title">{l.book_title || "Untitled"}</div>
                    <div className="mr-book-author">{l.book_author || "—"}</div>
                  </td>
                  <td>{fmt(l.borrowed_at)}</td>
                  <td>{fmt(l.due_at)}</td>
                  <td>{fmt(l.returned_at)}</td>
                  <td>
                    <span className={"mr-status mr-status-" + String(l.status || "").toLowerCase()}>
                      {l.status || "—"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
