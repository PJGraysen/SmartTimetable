import {
  CalendarCheck,
  CheckCircle2,
  Clock3,
  Play,
  Sparkles,
} from "lucide-react";
import { Link } from "react-router-dom";

const stats = [
  {
    label: "Active Timetable",
    value: "—",
    description: "No published timetable yet",
    icon: CalendarCheck,
  },
  {
    label: "Scheduling Runs",
    value: "—",
    description: "Connects to Django API",
    icon: Clock3,
  },
  {
    label: "System Status",
    value: "Ready",
    description: "Scheduling engine operational",
    icon: CheckCircle2,
  },
];

export default function Dashboard() {
  return (
    <>
      <div className="page-header">
        <div>
          <span className="eyebrow">OVERVIEW</span>
          <h1>Dashboard</h1>
          <p>
            Manage academic scheduling and generate optimized school
            timetables.
          </p>
        </div>
        <Link className="primary-button" to="/scheduling">
          <Play size={17} />
          Generate Timetable
        </Link>
      </div>

      <div className="hero-card">
        <div className="hero-icon">
          <Sparkles size={28} />
        </div>
        <div>
          <span className="hero-label">SMART SCHEDULING ENGINE</span>
          <h2>Build a conflict-free timetable automatically.</h2>
          <p>
            SmartTimetable Pro combines hard scheduling constraints with
            optimization objectives to produce practical school timetables.
          </p>
        </div>
      </div>

      <div className="stats-grid">
        {stats.map(({ label, value, description, icon: Icon }) => (
          <div className="stat-card" key={label}>
            <div className="stat-icon">
              <Icon size={21} />
            </div>
            <div>
              <span>{label}</span>
              <strong>{value}</strong>
              <small>{description}</small>
            </div>
          </div>
        ))}
      </div>

      <div className="section-card">
        <div className="section-heading">
          <div>
            <span className="eyebrow">WORKFLOW</span>
            <h2>Scheduling workflow</h2>
          </div>
        </div>

        <div className="workflow-grid">
          <div className="workflow-step">
            <span>01</span>
            <h3>Prepare data</h3>
            <p>Configure teachers, subjects, groups, rooms and requirements.</p>
          </div>
          <div className="workflow-step">
            <span>02</span>
            <h3>Generate</h3>
            <p>Run the constraint-based scheduling engine.</p>
          </div>
          <div className="workflow-step">
            <span>03</span>
            <h3>Validate</h3>
            <p>Check the generated timetable against school rules.</p>
          </div>
          <div className="workflow-step">
            <span>04</span>
            <h3>Publish</h3>
            <p>Review and publish the completed timetable.</p>
          </div>
        </div>
      </div>
    </>
  );
}
