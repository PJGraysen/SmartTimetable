import { useState } from "react";
import { LoaderCircle, Play, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";
import api from "../services/api";

export default function SchedulingRuns() {
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState(
    "Ready to create a scheduling run."
  );

  async function generateTimetable() {
    setRunning(true);
    setMessage("Connecting to the scheduling API...");

    try {
      const response = await api.get("/scheduling/runs/");
      setMessage(
        `Scheduling API connected. ${response.data.count ?? response.data.length ?? 0} run(s) currently available.`
      );
    } catch {
      setMessage(
        "The frontend is ready, but the Django API is not currently reachable."
      );
    } finally {
      setRunning(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <span className="eyebrow">SCHEDULING ENGINE</span>
          <h1>Scheduling Runs</h1>
          <p>Create, execute and monitor automated timetable generation runs.</p>
        </div>
        <button
          className="primary-button"
          onClick={generateTimetable}
          disabled={running}
        >
          {running ? (
            <LoaderCircle className="spin" size={17} />
          ) : (
            <Play size={17} />
          )}
          {running ? "Connecting..." : "Generate Timetable"}
        </button>
      </div>

      <div className="section-card">
        <div className="empty-state">
          <div className="empty-icon">
            <RefreshCw size={28} />
          </div>
          <h2>Scheduling control centre</h2>
          <p>{message}</p>
          <Link className="secondary-button" to="/timetable">
            View Timetable
          </Link>
        </div>
      </div>
    </>
  );
}
