import { useState, type FormEvent } from "react";
import http from "../services/http";
import { useNavigate } from "react-router-dom";
import { PlayCircle } from "lucide-react";
import { useAuth } from "../auth/AuthContext";

function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await login(username, password);
      try {
        const { data: me } = await http.get("/core/me/");
        navigate(me.landing_path || "/home", { replace: true });
      } catch {
        navigate("/home", { replace: true });
      }
    } catch (err: any) {
      const detail =
        err?.response?.data?.detail ||
        err?.detail ||
        err?.message ||
        "Unable to sign in.";
      setError(String(detail));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#f5f7fb",
        padding: "1rem",
      }}
    >
      <form
        onSubmit={handleSubmit}
        style={{
          background: "#fff",
          padding: "2.5rem",
          borderRadius: "12px",
          boxShadow: "0 4px 24px rgba(0,0,0,0.06)",
          minWidth: "360px",
          maxWidth: "420px",
          width: "100%",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
            marginBottom: "1.75rem",
          }}
        >
          <div
            style={{
              width: "44px",
              height: "44px",
              borderRadius: "10px",
              background: "#1e3a8a",
              color: "#fff",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <PlayCircle size={24} />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: "1.05rem" }}>
              SmartSchoolPro
            </div>
            <div style={{ color: "#748095", fontSize: "0.8rem" }}>
              School Management Platform
            </div>
          </div>
        </div>

        <label style={{ display: "block", marginBottom: "1rem" }}>
          <span
            style={{
              display: "block",
              fontSize: "0.75rem",
              fontWeight: 700,
              color: "#748095",
              marginBottom: "0.35rem",
            }}
          >
            USERNAME
          </span>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            autoFocus
            disabled={submitting}
            style={{
              width: "100%",
              padding: "0.65rem 0.75rem",
              borderRadius: "6px",
              border: "1px solid #d1d5db",
              fontSize: "0.95rem",
              boxSizing: "border-box",
            }}
          />
        </label>

        <label style={{ display: "block", marginBottom: "1.25rem" }}>
          <span
            style={{
              display: "block",
              fontSize: "0.75rem",
              fontWeight: 700,
              color: "#748095",
              marginBottom: "0.35rem",
            }}
          >
            PASSWORD
          </span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            disabled={submitting}
            style={{
              width: "100%",
              padding: "0.65rem 0.75rem",
              borderRadius: "6px",
              border: "1px solid #d1d5db",
              fontSize: "0.95rem",
              boxSizing: "border-box",
            }}
          />
        </label>

        {error ? (
          <div
            style={{
              color: "#b91c1c",
              fontSize: "0.85rem",
              marginBottom: "1rem",
              padding: "0.6rem 0.75rem",
              background: "#fef2f2",
              borderRadius: "6px",
            }}
          >
            {error}
          </div>
        ) : null}

        <button
          type="submit"
          disabled={submitting || !username || !password}
          style={{
            width: "100%",
            padding: "0.75rem",
            borderRadius: "6px",
            border: "none",
            background: submitting || !username || !password ? "#93a4c0" : "#1e3a8a",
            color: "#fff",
            fontSize: "0.95rem",
            fontWeight: 600,
            cursor:
              submitting || !username || !password ? "not-allowed" : "pointer",
          }}
        >
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}

export default LoginPage;
