import { useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
import {
  Bot, Code2, Copy, Check, Loader2, MessageSquare, Send, Shield, Sparkles, User, X,
} from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import "../styles/analysis.css";

type Mode = "chat" | "code";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  mode?: Mode;
};

type ChatResponse = {
  success?: boolean;
  content?: string;
  error?: string;
  model?: string;
  mode?: Mode;
};

const BROWN = "#2b1a0f", BROWN2 = "#5a3a1e", SKY = "#22b4f0", CREAM = "#f5eee2";

const cardStyle: React.CSSProperties = {
  background: "#fff", border: "1px solid #e5e7eb", borderRadius: "14px",
  boxShadow: "0 4px 14px rgba(10,18,29,0.05)",
};

async function sendAIMessage(mode: Mode, messages: ChatMessage[]): Promise<ChatResponse> {
  const response = await fetch("/api/ai/chat/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      mode,
      messages: messages.map((m) => ({ role: m.role, content: m.content })),
    }),
  });

  let data: ChatResponse;
  try {
    data = (await response.json()) as ChatResponse;
  } catch {
    throw new Error(`AI gateway returned an invalid response (HTTP ${response.status}).`);
  }
  if (!response.ok || data.success !== true) {
    throw new Error(data.error || `AI gateway request failed with HTTP ${response.status}.`);
  }
  return data;
}

function CodeBlock({ children }: { children: string }) {
  const [copied, setCopied] = useState(false);
  const hasFence = children.includes("```");
  if (!hasFence) {
    return <div style={{ whiteSpace: "pre-wrap" }}>{children}</div>;
  }
  // Split into segments: text and fenced code
  const parts: Array<{ type: "text" | "code"; lang?: string; body: string }> = [];
  const regex = /```([a-zA-Z0-9_+\-]*)\n([\s\S]*?)```/g;
  let lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = regex.exec(children)) !== null) {
    if (m.index > lastIndex) {
      parts.push({ type: "text", body: children.slice(lastIndex, m.index) });
    }
    parts.push({ type: "code", lang: m[1], body: m[2] });
    lastIndex = m.index + m[0].length;
  }
  if (lastIndex < children.length) {
    parts.push({ type: "text", body: children.slice(lastIndex) });
  }

  function copy(text: string) {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    });
  }

  return (
    <div>
      {parts.map((p, i) => {
        if (p.type === "text") {
          return <div key={i} style={{ whiteSpace: "pre-wrap" }}>{p.body}</div>;
        }
        return (
          <div key={i} style={{ position: "relative", margin: "0.5rem 0" }}>
            <pre style={{
              background: "#1e293b", color: "#e2e8f0", padding: "0.85rem 1rem",
              borderRadius: "8px", overflow: "auto", fontSize: "0.82rem",
              fontFamily: "ui-monospace, Consolas, monospace", margin: 0,
            }}>
              <code>{p.body}</code>
            </pre>
            <button
              type="button"
              onClick={() => copy(p.body)}
              style={{
                position: "absolute", top: "6px", right: "6px",
                display: "inline-flex", alignItems: "center", gap: "4px",
                background: copied ? "#10b981" : "rgba(255,255,255,0.1)",
                color: "#fff", border: "none", padding: "3px 8px",
                borderRadius: "5px", cursor: "pointer", fontSize: "0.7rem",
                fontWeight: 600,
              }}
              title="Copy code"
            >
              {copied ? <><Check size={11} /> Copied</> : <><Copy size={11} /> Copy</>}
            </button>
          </div>
        );
      })}
    </div>
  );
}

export default function AIAssistant() {
  const { user } = useAuth();
  const u = user as { is_staff?: boolean; is_superuser?: boolean; display_name?: string; username?: string } | null;
  const isAdmin = !!(u && (u.is_staff || u.is_superuser));

  const [mode, setMode] = useState<Mode>("chat");
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: "Hello. I am the SmartTimetable AI Assistant. Ask me about timetable generation, scheduling, classes, teachers, subjects, constraints, or school timetable data.",
      mode: "chat",
    },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sending]);

  const placeholder = useMemo(() => {
    return mode === "code"
      ? "Ask about code — e.g. 'write a helper that formats a phone number'"
      : "Ask anything about your school's data or how to use the app…";
  }, [mode]);

  function switchMode(next: Mode) {
    if (next === mode) return;
    if (next === "code" && !isAdmin) return;
    setMode(next);
    setMessages([
      {
        role: "assistant",
        content: next === "code"
          ? "Code mode active. I'm using the deepseek-coder model. Paste code or ask for a function; I'll return formatted snippets with copy buttons."
          : "Chat mode active. I'm using the qwen2.5 chat model. Ask me anything about the school or the app.",
        mode: next,
      },
    ]);
    setError("");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = input.trim();
    if (!message || sending) return;

    setError("");
    const conversation: ChatMessage[] = [...messages, { role: "user", content: message, mode }];
    setMessages(conversation);
    setInput("");
    setSending(true);

    try {
      const data = await sendAIMessage(mode, conversation);
      setMessages([
        ...conversation,
        { role: "assistant", content: data.content || "(no reply)", mode },
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setSending(false);
    }
  }

  function clearChat() {
    setMessages([
      {
        role: "assistant",
        content: mode === "code"
          ? "Code mode reset. What would you like to build?"
          : "Chat reset. What would you like to know?",
        mode,
      },
    ]);
    setError("");
  }

  return (
    <div style={{ padding: "2rem", maxWidth: "1100px", margin: "0 auto", display: "flex", flexDirection: "column", height: "calc(100vh - 2rem)" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: "14px", marginBottom: "1.25rem", flexWrap: "wrap" }}>
        <div style={{
          width: "52px", height: "52px", borderRadius: "14px",
          background: `linear-gradient(135deg, ${SKY}, #0b5d8c)`,
          color: "#fff", display: "flex", alignItems: "center", justifyContent: "center",
          boxShadow: "0 6px 18px rgba(34,180,240,0.35)",
        }}>
          {mode === "code" ? <Code2 size={26} /> : <Bot size={26} />}
        </div>
        <div style={{ flex: 1, minWidth: "200px" }}>
          <h1 style={{ margin: 0, fontSize: "1.7rem", color: "#1e2e40", fontWeight: 800 }}>
            AI Assistant
          </h1>
          <p style={{ margin: "2px 0 0", color: "#748095", fontSize: "0.9rem" }}>
            Local models via Ollama — nothing leaves the school network.
          </p>
        </div>

        {/* Mode tabs */}
        <div style={{ display: "flex", gap: "6px", background: "#f1f5f9", borderRadius: "10px", padding: "4px" }}>
          <button
            type="button"
            onClick={() => switchMode("chat")}
            style={{
              display: "inline-flex", alignItems: "center", gap: "6px",
              background: mode === "chat" ? "#fff" : "transparent",
              color: mode === "chat" ? BROWN2 : "#64748b",
              border: "none", padding: "7px 14px", borderRadius: "7px",
              cursor: "pointer", fontWeight: 700, fontSize: "0.85rem",
              boxShadow: mode === "chat" ? "0 1px 3px rgba(0,0,0,0.08)" : "none",
            }}
          >
            <MessageSquare size={15} /> Chat
          </button>
          {isAdmin && (
            <button
              type="button"
              onClick={() => switchMode("code")}
              style={{
                display: "inline-flex", alignItems: "center", gap: "6px",
                background: mode === "code" ? "#fff" : "transparent",
                color: mode === "code" ? BROWN2 : "#64748b",
                border: "none", padding: "7px 14px", borderRadius: "7px",
                cursor: "pointer", fontWeight: 700, fontSize: "0.85rem",
                boxShadow: mode === "code" ? "0 1px 3px rgba(0,0,0,0.08)" : "none",
              }}
            >
              <Code2 size={15} /> Code
              <span style={{
                fontSize: "0.62rem", background: "#fef3c7", color: "#92400e",
                padding: "1px 6px", borderRadius: "999px", fontWeight: 800,
                letterSpacing: "0.04em",
              }}>ADMIN</span>
            </button>
          )}
        </div>

        <button
          type="button"
          onClick={clearChat}
          style={{
            display: "inline-flex", alignItems: "center", gap: "6px",
            background: "transparent", border: "1px solid #cbd5e1",
            color: "#64748b", padding: "7px 12px", borderRadius: "9px",
            cursor: "pointer", fontWeight: 600, fontSize: "0.82rem",
          }}
        >
          <X size={13} /> Clear
        </button>
      </div>

      {/* Banner for code mode */}
      {mode === "code" && (
        <div style={{
          display: "flex", alignItems: "center", gap: "10px",
          padding: "0.7rem 1rem", borderRadius: "10px",
          background: "#fef3c7", color: "#92400e",
          border: "1px solid #fde68a", marginBottom: "1rem",
          fontSize: "0.85rem", fontWeight: 600,
        }}>
          <Shield size={16} />
          Code mode · administrator only. Every request is logged to the audit trail.
        </div>
      )}

      {/* Messages */}
      <div
        ref={scrollRef}
        style={{
          ...cardStyle,
          flex: 1, overflowY: "auto",
          padding: "1.25rem", marginBottom: "1rem",
          display: "flex", flexDirection: "column", gap: "12px",
        }}
      >
        {messages.map((m, i) => {
          const isUser = m.role === "user";
          return (
            <div key={i} className="anim-rise" style={{
              display: "flex", gap: "10px", alignItems: "flex-start",
              flexDirection: isUser ? "row-reverse" : "row",
            }}>
              <div style={{
                width: "34px", height: "34px", borderRadius: "10px", flexShrink: 0,
                background: isUser ? "#f1f5f9" : `linear-gradient(135deg, ${SKY}, #0b5d8c)`,
                color: isUser ? "#475569" : "#fff",
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                {isUser ? <User size={17} /> : (m.mode === "code" ? <Code2 size={17} /> : <Bot size={17} />)}
              </div>
              <div style={{
                flex: "0 1 auto", maxWidth: "78%",
                background: isUser ? "#f1f5f9" : "#fff",
                border: isUser ? "1px solid #e2e8f0" : `1px solid #e5e7eb`,
                borderRadius: "12px", padding: "0.75rem 1rem",
                fontSize: "0.9rem", color: "#1e2e40", lineHeight: 1.5,
                fontFamily: !isUser && m.mode === "code"
                  ? "ui-monospace, Consolas, monospace"
                  : "inherit",
              }}>
                {isUser ? (
                  <div style={{ whiteSpace: "pre-wrap" }}>{m.content}</div>
                ) : (
                  <CodeBlock>{m.content}</CodeBlock>
                )}
              </div>
            </div>
          );
        })}
        {sending && (
          <div style={{ display: "flex", gap: "10px", alignItems: "center", paddingLeft: "44px", color: "#94a3b8", fontSize: "0.85rem" }}>
            <Loader2 size={16} className="spin" style={{ animation: "spin 1s linear infinite" }} />
            Thinking…
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div style={{
          padding: "0.7rem 1rem", borderRadius: "10px",
          background: "#fee2e2", color: "#991b1b", marginBottom: "0.75rem",
          fontSize: "0.86rem", fontWeight: 600,
        }}>
          {error}
        </div>
      )}

      {/* Composer */}
      <form onSubmit={handleSubmit} style={{
        ...cardStyle,
        display: "flex", gap: "10px", alignItems: "flex-end",
        padding: "0.75rem",
      }}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={placeholder}
          rows={2}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e as unknown as FormEvent<HTMLFormElement>);
            }
          }}
          style={{
            flex: 1, resize: "none", border: "1px solid #e5e7eb",
            borderRadius: "10px", padding: "0.65rem 0.9rem",
            fontSize: "0.92rem", fontFamily: "inherit",
            outline: "none", color: "#1e2e40",
          }}
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          style={{
            display: "inline-flex", alignItems: "center", gap: "6px",
            background: sending || !input.trim() ? "#cbd5e1" : SKY,
            color: "#fff", border: "none",
            padding: "0.7rem 1.15rem", borderRadius: "10px",
            cursor: sending || !input.trim() ? "not-allowed" : "pointer",
            fontWeight: 700, fontSize: "0.88rem",
          }}
        >
          <Send size={15} /> Send
        </button>
      </form>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}