"use client";

import React, { useState } from "react";
import { HelpCircle, Loader2, MessageSquareText, Send } from "lucide-react";
import { EvidenceChipList } from "./EvidenceChips";
import { ChatResponse } from "@/lib/dossierV2Api";

interface ChatPanelProps {
  onAsk: (question: string) => Promise<ChatResponse>;
  onOpenEvidence: (refId: string) => void;
  disabled?: boolean;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  evidence: string[];
  abstained: boolean;
  pending?: boolean;
}

const SUGGESTIONS = [
  "What is the strongest grounded claim?",
  "What evidence is missing?",
  "Which recommendation is cheapest to test?",
];

export default function ChatPanel({ onAsk, onOpenEvidence, disabled }: ChatPanelProps) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (text: string) => {
    const clean = text.trim();
    if (!clean || busy || disabled) return;
    const userMessage: ChatMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      text: clean,
      evidence: [],
      abstained: false,
    };
    const pendingId = `a-${Date.now()}`;
    setMessages((current) => [
      ...current,
      userMessage,
      { id: pendingId, role: "assistant", text: "", evidence: [], abstained: false, pending: true },
    ]);
    setQuestion("");
    setError("");
    setBusy(true);
    try {
      const response = await onAsk(clean);
      setMessages((current) =>
        current.map((message) =>
          message.id === pendingId
            ? {
                ...message,
                text: response.answer || "",
                evidence: response.evidence || [],
                abstained: Boolean(response.abstained),
                pending: false,
              }
            : message,
        ),
      );
    } catch (err) {
      setMessages((current) => current.filter((message) => message.id !== pendingId));
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <aside className="dv2-paper dv2-chat" aria-label="Ask about this dossier">
      <div className="dv2-chat-head">
        <MessageSquareText size={17} />
        <div>
          <p className="dv2-eyebrow">Grounded Q&amp;A</p>
          <h2 className="dv2-section-title">Ask about this dossier</h2>
        </div>
      </div>
      <p className="dv2-chat-intro">
        Answers come from this run only. When the evidence is insufficient, the assistant abstains.
      </p>

      <div className="dv2-chat-log" aria-live="polite">
        {messages.length === 0 ? (
          <div className="dv2-chat-empty">
            <HelpCircle size={20} />
            <p>Ask a question to test the dossier&apos;s grounding.</p>
          </div>
        ) : (
          messages.map((message) => (
            <div key={message.id} className={`dv2-chat-message is-${message.role}`}>
              <p className="dv2-chat-who">{message.role === "user" ? "You" : "Dossier"}</p>
              {message.pending ? (
                <p className="dv2-chat-pending"><Loader2 size={13} className="dv2-spin" /> Checking evidence…</p>
              ) : message.abstained ? (
                <div className="dv2-abstain">
                  <strong>I don&apos;t know.</strong>
                  {message.text && <p>{message.text}</p>}
                </div>
              ) : (
                <p className="dv2-chat-answer">{message.text || "No answer returned."}</p>
              )}
              {!message.pending && message.evidence.length > 0 && (
                <div className="dv2-chat-evidence">
                  <span>Evidence:</span> <EvidenceChipList refs={message.evidence} onOpen={onOpenEvidence} />
                </div>
              )}
            </div>
          ))
        )}
      </div>

      <div className="dv2-chat-suggestions">
        {SUGGESTIONS.map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            onClick={() => void submit(suggestion)}
            disabled={busy || disabled}
          >
            {suggestion}
          </button>
        ))}
      </div>

      {error && <p className="dv2-chat-error" role="alert">{error}</p>}

      <form
        className="dv2-chat-form"
        onSubmit={(event) => {
          event.preventDefault();
          void submit(question);
        }}
      >
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask a grounded question…"
          disabled={disabled}
          aria-label="Question"
        />
        <button type="submit" disabled={busy || disabled || !question.trim()} aria-label="Send question">
          {busy ? <Loader2 size={15} className="dv2-spin" /> : <Send size={15} />}
        </button>
      </form>
    </aside>
  );
}
