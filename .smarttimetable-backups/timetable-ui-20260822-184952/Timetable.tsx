import { CalendarDays } from "lucide-react";

export default function Timetable() {
  const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];

  return (
    <>
      <div className="page-header">
        <div>
          <span className="eyebrow">TIMETABLE</span>
          <h1>Weekly Timetable</h1>
          <p>View the currently selected timetable version.</p>
        </div>
      </div>

      <div className="section-card">
        <div className="empty-state">
          <div className="empty-icon">
            <CalendarDays size={28} />
          </div>
          <h2>No timetable published</h2>
          <p>
            Generate a timetable first. The completed timetable will appear
            here for review.
          </p>
          <div className="day-preview">
            {days.map((day) => (
              <span key={day}>{day}</span>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
