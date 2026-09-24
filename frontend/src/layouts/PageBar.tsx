import { Link, useLocation, useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, Home as HomeIcon } from "lucide-react";

const LABELS: Record<string, string> = {
  home: "Home",
  timetables: "Timetables",
  scheduling: "Scheduling",
  academics: "Academics",
  teachers: "Teachers",
  subjects: "Subjects",
  rooms: "Rooms",
  validation: "Validation",
  settings: "Settings",
  ai: "AI Assistant",
  library: "Library",
  catalogue: "Catalogue",
  members: "Members",
  circulation: "Circulation",
  loans: "Loans",
  reports: "Reports",
  new: "New",
  "academic-analysis": "Academic Analysis",
};

function isUuid(s: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(s);
}

export default function PageBar() {
  const location = useLocation();
  const navigate = useNavigate();
  const path = location.pathname;
  const segments = path.split("/").filter(Boolean);

  let acc = "";
  const crumbs = segments.map((seg, i) => {
    acc += "/" + seg;
    const label = isUuid(seg)
      ? "Detail"
      : LABELS[seg] ?? seg.charAt(0).toUpperCase() + seg.slice(1);
    return { to: acc, label, last: i === segments.length - 1 };
  });

  return (
    <div className="ssp-pagebar">
      <div className="ssp-pagebar-crumbs">
        <Link to="/home" className="ssp-crumb-home" title="Home">
          <HomeIcon size={15} />
        </Link>
        {crumbs.map((c) => (
          <span key={c.to} className="ssp-crumb-group">
            <span className="ssp-crumb-sep">/</span>
            {c.last ? (
              <span className="ssp-crumb-current">{c.label}</span>
            ) : (
              <Link to={c.to} className="ssp-crumb-link">
                {c.label}
              </Link>
            )}
          </span>
        ))}
      </div>
      <div className="ssp-pagebar-nav">
        <button
          type="button"
          className="ssp-nav-btn"
          onClick={() => navigate(-1)}
          title="Back"
        >
          <ArrowLeft size={15} />
        </button>
        <button
          type="button"
          className="ssp-nav-btn"
          onClick={() => navigate(1)}
          title="Forward"
        >
          <ArrowRight size={15} />
        </button>
      </div>
    </div>
  );
}
