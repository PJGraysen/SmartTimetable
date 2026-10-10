import { useState, type FormEvent } from "react";
import http from "../services/http";
import { useNavigate } from "react-router-dom";
import { PlayCircle, ShieldCheck, RefreshCw, Lock } from "lucide-react";
import { useAuth } from "../auth/AuthContext";

type Step = "creds" | "verify";

function LoginPage() {
  const [step, setStep] = useState<Step>("creds");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [resending, setResending] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [attemptsLeft, setAttemptsLeft] = useState<number | null>(null);
  const [lockMinutes, setLockMinutes] = useState<number | null>(null);
  const [channel, setChannel] = useState<string>("");
  const { refresh } = useAuth();
  const navigate = useNavigate();

  async function gotoLanding() {
    try {
      const { data } = await http.get("/core/me/");
      navigate(data.landing_path || "/home", { replace: true });
    } catch {
      navigate("/home", { replace: true });
    }
  }

  async function handleCredentials(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    setInfo("");
    setLockMinutes(null);
    setAttemptsLeft(null);
    try {
      const { data } = await http.post("/platform/auth/login/", { username, password });
      if (data?.code === "VERIFICATION_REQUIRED") {
        setChannel(data.channel || "");
        setInfo(
          data.channel === "email"
            ? "A 6-digit code was emailed to you. Enter it below to finish signing in."
            : "A 6-digit code was generated. Ask your administrator for it, then enter it below."
        );
        setStep("verify");
        return;
      }
      await refresh?.();
      await gotoLanding();
    } catch (err: any) {
      const resp = err?.response;
      const data = resp?.data || {};
      if (resp?.status === 423 || data?.code === "LOCKED") {
        setLockMinutes(data?.retry_after_minutes ?? 15);
        setError(data?.detail || "Account is temporarily locked.");
      } else if (resp?.status === 401) {
        setAttemptsLeft(data?.attempts_left ?? null);
        setError(data?.detail || "Invalid credentials.");
      } else if (resp?.status === 429) {
        setError("Too many attempts. Please wait a moment and try again.");
      } else {
        setError(data?.detail || err?.message || "Unable to sign in.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function handleVerify(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    setInfo("");
    try {
      await http.post("/platform/auth/verify/", { username, code });
      await refresh?.();
      await gotoLanding();
    } catch (err: any) {
      const data = err?.response?.data || {};
      setError(data?.detail || "Verification failed.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleResend() {
    setResending(true);
    setError("");
    setInfo("");
    try {
      const { data } = await http.post("/platform/auth/resend-code/", { username });
      setInfo(`New code sent (${data?.channel || "console"}).`);
    } catch (err: any) {
      const data = err?.response?.data || {};
      setError(data?.detail || "Could not resend the code.");
    } finally {
      setResending(false);
    }
  }

  function backToCreds() {
    setStep("creds");
    setCode("");
    setPassword("");
    setError("");
    setInfo("");
    setChannel("");
  }

  const cardStyle: React.CSSProperties = {
    background: "#fff",
    padding: "2.5rem",
    borderRadius: "12px",
    boxShadow: "0 4px 24px rgba(0,0,0,0.06)",
    minWidth: "360px",
    maxWidth: "420px",
    width: "100%",
  };

  const inputStyle: React.CSSProperties = {
    width: "100%",
    padding: "0.65rem 0.75rem",
    borderRadius: "6px",
    border: "1px solid #d1d5db",
    fontSize: "0.95rem",
    boxSizing: "border-box",
  };

  const lblStyle: React.CSSProperties = {
    display: "block",
    fontSize: "0.75rem",
    fontWeight: 700,
    color: "#748095",
    marginBottom: "0.35rem",
  };

  const header = (
    <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1.75rem" }}>
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
        <div style={{ fontWeight: 700, fontSize: "1.05rem" }}>SmartSchoolPro</div>
        <div style={{ color: "#748095", fontSize: "0.8rem" }}>School Management Platform</div>
      </div>
    </div>
  );

  const errorBox = error ? (
    <div
      style={{
        color: "#b91c1c",
        fontSize: "0.85rem",
        marginBottom: "1rem",
        padding: "0.6rem 0.75rem",
        background: "#fef2f2",
        borderRadius: "6px",
        display: "flex",
        alignItems: "flex-start",
        gap: 8,
      }}
    >
      {lockMinutes != null && <Lock size={15} style={{ flexShrink: 0, marginTop: 2 }} />}
      <span>{error}</span>
    </div>
  ) : null;

  const infoBox = info ? (
    <div
      style={{
        color: "#1e3a8a",
        fontSize: "0.85rem",
        marginBottom: "1rem",
        padding: "0.6rem 0.75rem",
        background: "#eff6ff",
        borderRadius: "6px",
        display: "flex",
        alignItems: "flex-start",
        gap: 8,
      }}
    >
      <ShieldCheck size={15} style={{ flexShrink: 0, marginTop: 2 }} />
      <span>{info}</span>
    </div>
  ) : null;

  const attemptsHint =
    attemptsLeft != null && attemptsLeft > 0 ? (
      <div
        style={{
          fontSize: "0.75rem",
          color: "#b45309",
          marginBottom: "1rem",
        }}
      >
        {attemptsLeft} attempt{attemptsLeft === 1 ? "" : "s"} left before temporary lockout.
      </div>
    ) : null;

  // ---------------- STEP: credentials ----------------
  if (step === "creds") {
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
        <form onSubmit={handleCredentials} style={cardStyle}>
          {header}

          <label style={{ display: "block", marginBottom: "1rem" }}>
            <span style={lblStyle}>USERNAME</span>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              autoFocus
              disabled={submitting}
              style={inputStyle}
            />
          </label>

          <label style={{ display: "block", marginBottom: "1.25rem" }}>
            <span style={lblStyle}>PASSWORD</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              disabled={submitting}
              style={inputStyle}
            />
          </label>

          {errorBox}
          {attemptsHint}

          <button
            type="submit"
            disabled={submitting || !username || !password || lockMinutes != null}
            style={{
              width: "100%",
              padding: "0.75rem",
              borderRadius: "6px",
              border: "none",
              background:
                submitting || !username || !password || lockMinutes != null
                  ? "#93a4c0"
                  : "#1e3a8a",
              color: "#fff",
              fontSize: "0.95rem",
              fontWeight: 600,
              cursor:
                submitting || !username || !password || lockMinutes != null
                  ? "not-allowed"
                  : "pointer",
            }}
          >
            {submitting ? "Signing in..." : lockMinutes != null ? "Locked" : "Sign in"}
          </button>
        </form>
      </div>
    );
  }

  // ---------------- STEP: verification ----------------
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
      <form onSubmit={handleVerify} style={cardStyle}>
        {header}

        <div
          style={{
            fontSize: "0.8rem",
            color: "#748095",
            marginBottom: "1.25rem",
            lineHeight: 1.5,
          }}
        >
          Signing in as <b>{username}</b>. Enter the 6-digit verification code to continue.
        </div>

        <label style={{ display: "block", marginBottom: "1.25rem" }}>
          <span style={lblStyle}>VERIFICATION CODE</span>
          <input
            type="text"
            inputMode="numeric"
            pattern="[0-9]*"
            maxLength={6}
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
            autoComplete="one-time-code"
            autoFocus
            disabled={submitting}
            style={{
              ...inputStyle,
              fontSize: "1.5rem",
              letterSpacing: "0.4em",
              textAlign: "center",
              fontWeight: 700,
            }}
          />
        </label>

        {infoBox}
        {errorBox}

        <button
          type="submit"
          disabled={submitting || code.length !== 6}
          style={{
            width: "100%",
            padding: "0.75rem",
            borderRadius: "6px",
            border: "none",
            background: submitting || code.length !== 6 ? "#93a4c0" : "#1e3a8a",
            color: "#fff",
            fontSize: "0.95rem",
            fontWeight: 600,
            cursor: submitting || code.length !== 6 ? "not-allowed" : "pointer",
          }}
        >
          {submitting ? "Verifying..." : "Verify and sign in"}
        </button>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginTop: "1rem",
          }}
        >
          <button
            type="button"
            onClick={backToCreds}
            disabled={submitting}
            style={{
              background: "transparent",
              border: "none",
              color: "#748095",
              fontSize: "0.8rem",
              cursor: "pointer",
              padding: 0,
            }}
          >
            Back
          </button>
          <button
            type="button"
            onClick={handleResend}
            disabled={resending || submitting}
            style={{
              background: "transparent",
              border: "none",
              color: "#1e3a8a",
              fontSize: "0.8rem",
              fontWeight: 600,
              cursor: resending ? "wait" : "pointer",
              padding: 0,
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            <RefreshCw size={12} /> {resending ? "Sending..." : "Resend code"}
          </button>
        </div>
      </form>
    </div>
  );
}

export default LoginPage;
