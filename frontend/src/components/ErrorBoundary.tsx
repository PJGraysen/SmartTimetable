import { Component, ReactNode, ErrorInfo } from "react";

type Props = { children: ReactNode };
type State = { error: Error | null; info: ErrorInfo | null };

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null, info: null };

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error("ErrorBoundary caught:", error, info);
    this.setState({ info });
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: "2rem", fontFamily: "system-ui, sans-serif", background: "#fff", minHeight: "100vh" }}>
          <div style={{ maxWidth: "760px", margin: "0 auto", background: "#fee2e2", border: "1px solid #ef4444", borderRadius: "12px", padding: "1.5rem" }}>
            <h1 style={{ color: "#991b1b", margin: "0 0 0.5rem", fontSize: "1.3rem" }}>
              Something crashed while rendering
            </h1>
            <p style={{ color: "#7f1d1d", margin: "0 0 1rem", fontSize: "0.9rem" }}>
              This message is shown instead of a blank screen so the error is visible. Copy the text below if you need help.
            </p>
            <pre style={{ background: "#fff", padding: "0.9rem", borderRadius: "8px", overflow: "auto", fontSize: "0.85rem", color: "#7f1d1d", border: "1px solid #fecaca", margin: 0 }}>
              {String(this.state.error?.message || this.state.error)}
            </pre>
            {this.state.info?.componentStack && (
              <details style={{ marginTop: "0.8rem" }}>
                <summary style={{ cursor: "pointer", fontSize: "0.8rem", color: "#7f1d1d", fontWeight: 600 }}>
                  Show component stack
                </summary>
                <pre style={{ background: "#fff", padding: "0.9rem", borderRadius: "8px", overflow: "auto", fontSize: "0.72rem", color: "#7f1d1d", border: "1px solid #fecaca", marginTop: "0.5rem" }}>
                  {this.state.info.componentStack}
                </pre>
              </details>
            )}
            <button
              type="button"
              onClick={() => { this.setState({ error: null, info: null }); window.location.href = "/"; }}
              style={{ marginTop: "1rem", background: "#ef4444", color: "#fff", border: "none", padding: "0.55rem 1.1rem", borderRadius: "8px", cursor: "pointer", fontWeight: 700 }}
            >
              Go to Home
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}