"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import {
  Bot,
  CheckCircle2,
  ChevronDown,
  ExternalLink,
  HelpCircle,
  Loader2,
  MessageSquare,
  RefreshCw,
  Send,
  Sparkles,
  Wand2,
  X,
  Zap,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import { answerIntake, evaluateEligibility } from "@/lib/api/cases";

type ChatRole = "user" | "assistant";
type ChatMessage = { role: ChatRole; text: string };

type IntakeAction = {
  key: string;
  value: string;
  label: string;
};

const QUICK_PROMPTS = [
  "Fix my Purpose of Stay to Tourism",
  "How do I fix eligibility warnings?",
  "What is required for Purpose of Stay?",
  "Which documents do I need to gather?",
];

function parseMessageWithActions(text: string): { cleanText: string; actions: IntakeAction[] } {
  const actions: IntakeAction[] = [];
  const actionRegex = /\[ACTION:update_intake\s+key="([^"]+)"\s+value="([^"]+)"\s+label="([^"]+)"\]/g;

  let match;
  while ((match = actionRegex.exec(text)) !== null) {
    actions.push({
      key: match[1],
      value: match[2],
      label: match[3],
    });
  }

  const cleanText = text.replace(actionRegex, "").trim();
  return { cleanText, actions };
}

export function FloatingAssistant() {
  const pathname = usePathname();
  const { token } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [applyingAction, setApplyingAction] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Extract case ID if currently on a case page
  const caseMatch = pathname?.match(/\/cases\/(\d+)/);
  const caseId = caseMatch ? Number(caseMatch[1]) : null;

  useEffect(() => {
    if (!isOpen) return;
    void (async () => {
      try {
        const res = await fetch("/assistant/ai/chat/session", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            case_id: caseId ? String(caseId) : null,
            locale: "en",
          }),
        });
        if (!res.ok) return;
        const data = (await res.json()) as {
          messages?: { role?: string; content?: string }[];
        };
        const hydrated = (data.messages ?? [])
          .filter((m) => m.role === "assistant" || m.role === "user")
          .map((m) => ({ role: m.role as ChatRole, text: m.content ?? "" }));
        if (hydrated.length > 0) {
          setMessages(hydrated);
        } else {
          setMessages([
            {
              role: "assistant",
              text: "Hello! I am your Torii AI Immigration Assistant. How can I help you with your visa application, requirements, or eligibility today?",
            },
          ]);
        }
      } catch {
        setMessages([
          {
            role: "assistant",
            text: "Hello! How can I assist you with your visa application steps or questions?",
          },
        ]);
      }
    })();
  }, [isOpen, caseId]);

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isOpen]);

  async function handleApplyIntakeAction(action: IntakeAction) {
    if (!token || !caseId || applyingAction) return;
    setApplyingAction(action.key);
    setError(null);
    try {
      // 1. Update intake answer
      try {
        await answerIntake(token, caseId, action.key, action.value);
      } catch {
        // Fallback key alias check
        if (action.key === "main_purpose") {
          await answerIntake(token, caseId, "purpose_of_visit", action.value);
        } else if (action.key === "purpose_of_visit") {
          await answerIntake(token, caseId, "main_purpose", action.value);
        }
      }

      // 2. Re-evaluate eligibility automatically
      await evaluateEligibility(token, caseId);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: `✅ Updated **${action.key.replace(/_/g, " ")}** to **"${action.value}"** and re-evaluated eligibility! Refreshing page to update status...`,
        },
      ]);

      setTimeout(() => {
        window.location.reload();
      }, 1200);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to apply fix to intake");
    } finally {
      setApplyingAction(null);
    }
  }

  async function handleSend(textToSend?: string) {
    const text = (textToSend || input).trim();
    if (!text || sending) return;
    setError(null);
    setSending(true);
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text }]);

    try {
      const response = await fetch("/assistant/ai/chat/messages", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          message: text,
          case_id: caseId ? String(caseId) : null,
          locale: "en",
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error("Assistant service unavailable");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let assistantText = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() ?? "";

        for (const rawEvent of events) {
          const lines = rawEvent.split("\n");
          const eventName = lines
            .find((l) => l.startsWith("event:"))
            ?.replace("event:", "")
            .trim();
          const payload = lines
            .find((l) => l.startsWith("data:"))
            ?.replace("data:", "")
            .trim();
          if (!payload || eventName !== "bubble") continue;

          try {
            const data = JSON.parse(payload) as { text?: string };
            const chunk = data.text ?? "";
            if (!chunk) continue;
            assistantText += (assistantText ? "\n\n" : "") + chunk;
            setMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (last?.role === "assistant") {
                next[next.length - 1] = { ...last, text: assistantText };
              } else {
                next.push({ role: "assistant", text: assistantText });
              }
              return next;
            });
          } catch {
            // Ignore malformed JSON chunks
          }
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to connect to assistant");
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      {/* Floating Trigger Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 z-50 flex items-center gap-2.5 rounded-full bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground shadow-xl transition-all duration-200 hover:scale-105 hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
          aria-label="Open AI Assistant"
        >
          <div className="relative">
            <Bot className="size-5" />
            <span className="absolute -top-1 -right-1 flex size-2.5">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex size-2.5 rounded-full bg-emerald-500"></span>
            </span>
          </div>
          <span className="font-medium">Need Help? Ask AI</span>
        </button>
      )}

      {/* Floating Chat Drawer / Window */}
      {isOpen && (
        <div className="fixed bottom-4 right-4 z-50 flex h-[600px] w-[390px] sm:w-[440px] flex-col overflow-hidden rounded-2xl border bg-card shadow-2xl transition-all duration-300 animate-in fade-in slide-in-from-bottom-5">
          {/* Header */}
          <div className="flex items-center justify-between border-b bg-muted/40 px-4 py-3">
            <div className="flex items-center gap-2.5">
              <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Bot className="size-5" />
              </div>
              <div>
                <div className="flex items-center gap-1.5">
                  <h3 className="text-sm font-semibold text-foreground">AI Visa Assistant</h3>
                  <Badge tone="success" className="text-[9px] px-1.5 py-0">Online</Badge>
                </div>
                <p className="text-[11px] text-muted-foreground">
                  {caseId ? `Connected to Case #${caseId} · Can fix intake` : "Official guidance helper"}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <button
                onClick={() => setMessages([])}
                title="Clear chat"
                className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground"
              >
                <RefreshCw className="size-3.5" />
              </button>
              <button
                onClick={() => setIsOpen(false)}
                title="Close chat"
                className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground"
              >
                <X className="size-4" />
              </button>
            </div>
          </div>

          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3.5 text-xs">
            {messages.map((m, idx) => {
              const { cleanText, actions } = parseMessageWithActions(m.text);

              return (
                <div
                  key={idx}
                  className={`flex flex-col gap-1.5 ${m.role === "user" ? "items-end" : "items-start"}`}
                >
                  <div className={`flex gap-2.5 ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                    {m.role === "assistant" && (
                      <div className="size-6 shrink-0 rounded-full bg-primary/10 flex items-center justify-center text-primary mt-0.5">
                        <Bot className="size-3.5" />
                      </div>
                    )}
                    <div
                      className={`max-w-[85%] rounded-xl px-3.5 py-2.5 leading-relaxed ${
                        m.role === "user"
                          ? "bg-primary text-primary-foreground font-medium rounded-tr-none"
                          : "bg-muted/70 text-foreground border rounded-tl-none whitespace-pre-wrap"
                      }`}
                    >
                      {cleanText}
                    </div>
                  </div>

                  {/* One-Click Action Buttons if available */}
                  {actions.length > 0 && (
                    <div className="ml-8 mt-1 space-y-1.5">
                      {actions.map((act, aIdx) => (
                        <Button
                          key={aIdx}
                          onClick={() => void handleApplyIntakeAction(act)}
                          disabled={Boolean(applyingAction)}
                          className="h-8 text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-1.5 shadow-sm"
                        >
                          {applyingAction === act.key ? (
                            <Loader2 className="size-3.5 animate-spin" />
                          ) : (
                            <Zap className="size-3.5 fill-current" />
                          )}
                          {act.label}
                        </Button>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}

            {sending && (
              <div className="flex gap-2.5 items-center text-muted-foreground text-xs pl-2">
                <Loader2 className="size-3.5 animate-spin text-primary" />
                <span>AI assistant is formulating response...</span>
              </div>
            )}

            {error && (
              <div className="rounded-lg bg-rose-500/10 border border-rose-500/20 p-2.5 text-rose-600 text-xs">
                {error}
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Prompts Suggestions */}
          {messages.length <= 2 && (
            <div className="px-3 py-2 border-t bg-muted/20 flex flex-wrap gap-1.5">
              {QUICK_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => void handleSend(prompt)}
                  disabled={sending || Boolean(applyingAction)}
                  className="rounded-full border bg-background px-2.5 py-1 text-[11px] text-muted-foreground hover:border-primary hover:text-primary transition-colors text-left"
                >
                  {prompt}
                </button>
              ))}
            </div>
          )}

          {/* Footer Input */}
          <div className="border-t bg-background p-3">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void handleSend();
              }}
              className="flex items-center gap-2"
            >
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask or say 'Fix my purpose of stay to Tourism'..."
                className="flex-1 rounded-lg border bg-muted/30 px-3 py-2 text-xs outline-none focus:border-primary focus:bg-background focus:ring-1 focus:ring-primary"
                disabled={sending || Boolean(applyingAction)}
              />
              <Button
                type="submit"
                disabled={sending || !input.trim() || Boolean(applyingAction)}
                className="h-8 px-3 text-xs"
              >
                {sending ? <Loader2 className="size-3.5 animate-spin" /> : <Send className="size-3.5" />}
              </Button>
            </form>
            <p className="mt-1.5 text-[10px] text-center text-muted-foreground/70">
              Grounded in official immigration manuals · Can update intake answers
            </p>
          </div>
        </div>
      )}
    </>
  );
}

