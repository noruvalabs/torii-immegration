"use client";

import { useEffect, useMemo, useRef, useState, type PointerEvent } from "react";
import { usePathname } from "next/navigation";
import {
  Bot,
  ChevronUp,
  Loader2,
  Minus,
  Send,
  X,
  Zap,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import {
  answerIntake,
  evaluateEligibility,
  getEligibility,
  getCase,
  refreshChecklist,
  type Case,
  type EligibilityResult,
  type ChecklistItem,
} from "@/lib/api/cases";
import { getProfile, type User } from "@/lib/api/auth";

type ChatRole = "user" | "assistant";
type ChatMessage = { role: ChatRole; text: string };

type IntakeAction = {
  key: string;
  value: string;
  label: string;
};

type SizeMode = "compact" | "standard" | "expanded";

const SIZE_CONFIG: Record<SizeMode, { width: number; height: number; label: string }> = {
  compact: { width: 340, height: 420, label: "Compact" },
  standard: { width: 380, height: 490, label: "Standard" },
  expanded: { width: 480, height: 580, label: "Expanded" },
};

const CATEGORY_PROMPTS: Record<string, string[]> = {
  student: [
    "How do I fix my eligibility warnings?",
    "What is my current progress and next step?",
    "What documents are required for COE / Student Visa?",
    "What are the rules for part-time work (28 hrs/week)?",
  ],
  work: [
    "How do I fix my eligibility warnings?",
    "What is my current progress and next step?",
    "What documents are required for Work Visa (技人国)?",
    "What are the Resident Tax and Pension renewal rules?",
  ],
  tourist: [
    "How do I fix my eligibility warnings?",
    "What is my current progress and next step?",
    "What documents do I need for a Temporary Visitor visa?",
    "What should be included in the itinerary (滞在予定表)?",
  ],
};

const DEFAULT_PROMPTS = [
  "How do I fix my eligibility warnings?",
  "What is my current progress and next step?",
  "Which documents do I need to gather?",
  "Can you review my intake answers?",
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

function clampPosition(x: number, y: number, width: number, height: number): { x: number; y: number } {
  if (typeof window === "undefined") return { x, y };
  const pad = 12;
  const minX = pad;
  const maxX = Math.max(pad, window.innerWidth - width - pad);
  const minY = pad;
  const maxY = Math.max(pad, window.innerHeight - height - pad);
  return {
    x: Math.min(Math.max(minX, x), maxX),
    y: Math.min(Math.max(minY, y), maxY),
  };
}

export function FloatingAssistant() {
  const pathname = usePathname();
  const { token } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [sizeMode, setSizeMode] = useState<SizeMode>("standard");
  const [position, setPosition] = useState<{ x: number; y: number } | null>(null);

  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef<{ startX: number; startY: number; startPosX: number; startPosY: number } | null>(null);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [applyingAction, setApplyingAction] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeCase, setActiveCase] = useState<Case | null>(null);
  const [activeEligibility, setActiveEligibility] = useState<EligibilityResult | null>(null);
  const [activeChecklist, setActiveChecklist] = useState<ChecklistItem[]>([]);
  const [activeProfile, setActiveProfile] = useState<User | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize and load saved positions & sizes
  useEffect(() => {
    try {
      localStorage.removeItem("torii_assistant_trigger_pos");
      const savedPos = localStorage.getItem("torii_assistant_pos");
      if (savedPos) {
        const parsed = JSON.parse(savedPos);
        if (typeof parsed.x === "number" && typeof parsed.y === "number") {
          setPosition(clampPosition(parsed.x, parsed.y, 350, 460));
        }
      }
      const savedSize = localStorage.getItem("torii_assistant_size") as SizeMode;
      if (savedSize && SIZE_CONFIG[savedSize]) {
        setSizeMode(savedSize);
      }
    } catch {
      // Ignore storage errors
    }
  }, []);

  // Recalculate clamps on window resize
  useEffect(() => {
    const handleResize = () => {
      const w = isMinimized ? 280 : 350;
      const h = isMinimized ? 48 : 460;
      setPosition((prev) => (prev ? clampPosition(prev.x, prev.y, w, h) : null));
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [isMinimized]);

  // Extract case ID if currently on a case page
  const caseMatch = pathname?.match(/\/cases\/(\d+)/);
  const caseId = caseMatch ? Number(caseMatch[1]) : null;

  // Fetch complete real-time case context (Case, Eligibility findings, Checklist, Profile)
  useEffect(() => {
    if (!token || !caseId) {
      setActiveCase(null);
      setActiveEligibility(null);
      setActiveChecklist([]);
      setActiveProfile(null);
      return;
    }
    void (async () => {
      try {
        const [c, elig, chk, prof] = await Promise.all([
          getCase(token, caseId),
          getEligibility(token, caseId).catch(() => evaluateEligibility(token, caseId).catch(() => null)),
          refreshChecklist(token, caseId).catch(() => []),
          getProfile(token).catch(() => null),
        ]);
        setActiveCase(c);
        if (elig) setActiveEligibility(elig);
        if (chk) setActiveChecklist(chk);
        if (prof) setActiveProfile(prof);
      } catch {
        // Fallback gracefully
      }
    })();
  }, [token, caseId, isOpen]);

  const visaCategory = (activeCase?.visa_category_code || "").toLowerCase();
  const jurisdictionCode = activeCase?.jurisdiction_code || "JP";
  const actionCode = activeCase?.case_action_code || "new";

  const quickPrompts = useMemo(() => {
    if (visaCategory && CATEGORY_PROMPTS[visaCategory]) {
      return CATEGORY_PROMPTS[visaCategory];
    }
    return DEFAULT_PROMPTS;
  }, [visaCategory]);

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
          let welcome = "Hello! I am your Torii AI Immigration Assistant. How can I help you with your visa application today?";
          if (visaCategory === "student") {
            welcome = "Hello! I am your Torii AI Assistant for your Student Visa. Ask me about school admission, COE requirements, sponsor proofs, or eligibility!";
          } else if (visaCategory === "work") {
            welcome = "Hello! I am your Torii AI Assistant for your Work Visa. Ask me about employer categories, employment contracts, tax certificates, or extension rules!";
          } else if (visaCategory === "tourist") {
            welcome = "Hello! I am your Torii AI Assistant for your Temporary Visitor Visa. Ask me about itineraries, flight/hotel bookings, financial proofs, or eligibility!";
          }
          setMessages([
            {
              role: "assistant",
              text: welcome,
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
  }, [isOpen, caseId, visaCategory]);

  useEffect(() => {
    if (isOpen && !isMinimized) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isOpen, isMinimized]);

  // Window drag handlers
  const handlePointerDown = (e: PointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    const w = isMinimized ? 280 : 350;
    const h = isMinimized ? 48 : 460;
    const currentX = position?.x ?? Math.max(12, window.innerWidth - w - 24);
    const currentY = position?.y ?? Math.max(12, window.innerHeight - h - 24);

    dragStartRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      startPosX: currentX,
      startPosY: currentY,
    };
    setIsDragging(true);
    e.currentTarget.setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e: PointerEvent<HTMLDivElement>) => {
    if (!isDragging || !dragStartRef.current) return;
    const deltaX = e.clientX - dragStartRef.current.startX;
    const deltaY = e.clientY - dragStartRef.current.startY;
    const w = isMinimized ? 280 : 350;
    const h = isMinimized ? 48 : 460;

    const rawX = dragStartRef.current.startPosX + deltaX;
    const rawY = dragStartRef.current.startPosY + deltaY;
    const clamped = clampPosition(rawX, rawY, w, h);
    setPosition(clamped);
  };

  const handlePointerUp = (e: PointerEvent<HTMLDivElement>) => {
    if (!isDragging) return;
    setIsDragging(false);
    dragStartRef.current = null;
    try {
      e.currentTarget.releasePointerCapture(e.pointerId);
    } catch {
      // Ignore pointer capture error
    }
    if (position) {
      try {
        localStorage.setItem("torii_assistant_pos", JSON.stringify(position));
      } catch {
        // Ignore
      }
    }
  };

  const handleResetPosition = () => {
    setPosition(null);
    try {
      localStorage.removeItem("torii_assistant_pos");
    } catch {
      // Ignore
    }
  };

  const toggleSizeMode = () => {
    const nextMode: SizeMode =
      sizeMode === "compact" ? "standard" : sizeMode === "standard" ? "expanded" : "compact";
    setSizeMode(nextMode);
    try {
      localStorage.setItem("torii_assistant_size", nextMode);
    } catch {
      // Ignore
    }
    if (position) {
      const nextConf = SIZE_CONFIG[nextMode];
      setPosition((prev) => (prev ? clampPosition(prev.x, prev.y, nextConf.width, nextConf.height) : null));
    }
  };

  async function handleApplyIntakeAction(action: IntakeAction) {
    if (!token || !caseId || applyingAction) return;
    setApplyingAction(action.key);
    setError(null);
    try {
      try {
        await answerIntake(token, caseId, action.key, action.value);
      } catch {
        if (action.key === "main_purpose") {
          await answerIntake(token, caseId, "purpose_of_visit", action.value);
        } else if (action.key === "purpose_of_visit") {
          await answerIntake(token, caseId, "main_purpose", action.value);
        }
      }

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
          case_reference: activeCase?.reference || (caseId ? `Case #${caseId}` : null),
          scope_label: activeCase?.scope_label || null,
          case_status: activeCase?.status || null,
          current_step: activeCase?.status || null,
          jurisdiction_code: jurisdictionCode,
          visa_category_code: visaCategory || null,
          action_code: actionCode || null,
          intake_answers: activeCase?.intake_answers || null,
          eligibility_findings: activeEligibility?.findings || null,
          checklist: activeChecklist || null,
          user_profile: activeProfile || null,
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
            const newText = data.text ?? "";
            if (!newText) continue;

            assistantText += (assistantText ? "\n\n" : "") + newText;
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

  const disqualifiedFindings = (activeEligibility?.findings || []).filter(
    (f) =>
      (f.status as string) === "disqualified" ||
      f.status === "fail" ||
      f.status === "at_risk" ||
      (f.status as string) === "incomplete",
  );

  const activeConf = SIZE_CONFIG[sizeMode];

  return (
    <>
      {/* Draggable Floating Trigger Button (Compact) */}
      {/* Floating Trigger Button (Compact Bottom-Right) */}
      {!isOpen && (
        <button
          onClick={() => {
            setIsOpen(true);
            setIsMinimized(false);
          }}
          className="fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-full bg-primary px-3.5 py-2 text-xs font-semibold text-primary-foreground shadow-2xl transition-all duration-150 hover:scale-105 hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
          aria-label="Open AI Assistant"
          title="Click to open AI Assistant"
        >
          <div className="relative">
            <Bot className="size-4" />
            <span className="absolute -top-0.5 -right-0.5 flex size-2">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex size-2 rounded-full bg-emerald-500"></span>
            </span>
          </div>
          <span>Ask AI</span>
        </button>
      )}

      {/* Floating Chat Window (Full or Minimized) */}
      {isOpen && (
        <div
          style={{
            left: position ? `${position.x}px` : undefined,
            top: position ? `${position.y}px` : undefined,
            right: !position ? "24px" : undefined,
            bottom: !position ? "24px" : undefined,
            width: isMinimized ? "min(280px, calc(100vw - 24px))" : "min(350px, calc(100vw - 24px))",
            height: isMinimized ? "auto" : "min(460px, calc(100vh - 24px))",
          }}
          className={`fixed z-50 flex flex-col overflow-hidden rounded-2xl border bg-card/95 backdrop-blur-md shadow-2xl transition-[width,height] duration-200 animate-in fade-in ${
            isDragging ? "ring-2 ring-primary/60 shadow-primary/20" : ""
          }`}
        >
          {/* Draggable Header Bar */}
          <div
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            onDoubleClick={handleResetPosition}
            className={`flex items-center justify-between border-b bg-muted/70 px-3 py-2 select-none touch-none ${
              isDragging ? "cursor-grabbing bg-muted/90" : "cursor-grab hover:bg-muted/80"
            }`}
            title="Drag to move · Double-click to reset position"
          >
            {/* Header Left: Bot Icon + Title */}
            <div className="flex items-center gap-2 min-w-0 flex-1">
              <div className="flex size-6 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
                <Bot className="size-3.5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <h3 className="text-xs font-bold text-foreground truncate">Ask AI Assistant</h3>
                  <span className="size-1.5 rounded-full bg-emerald-500" title="Online" />
                </div>
                {!isMinimized && (
                  <p className="text-[10px] text-muted-foreground truncate">
                    {caseId
                      ? `${activeCase?.reference || `Case #${caseId}`} · ${activeCase?.scope_label || `${jurisdictionCode} ${visaCategory ? visaCategory.toUpperCase() : "VISA"}`}`
                      : "Procedural immigration guidance"}
                  </p>
                )}
              </div>
            </div>

            {/* Header Right Action Controls: Only Minimize & Close */}
            <div
              className="flex items-center gap-1"
              onPointerDown={(e) => e.stopPropagation()}
              onClick={(e) => e.stopPropagation()}
            >
              {/* Minimize / Expand Bar toggle */}
              <button
                onClick={() => setIsMinimized(!isMinimized)}
                className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
                title={isMinimized ? "Restore chat window" : "Minimize to floating bar"}
              >
                {isMinimized ? <ChevronUp className="size-3.5" /> : <Minus className="size-3.5" />}
              </button>

              {/* Close window */}
              <button
                onClick={() => {
                  setIsOpen(false);
                  setIsMinimized(false);
                }}
                className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
                title="Close assistant"
              >
                <X className="size-3.5" />
              </button>
            </div>
          </div>

          {/* Minimized Content: None (slim bar). Full Content: Body + Input */}
          {!isMinimized && (
            <>
              {/* Live Issue Banner if case has disqualified findings */}
              {disqualifiedFindings.length > 0 && (
                <div className="bg-amber-500/10 border-b border-amber-500/20 px-3 py-1.5 flex items-center justify-between gap-2 text-[11px] shrink-0">
                  <span className="text-amber-800 dark:text-amber-300 font-medium truncate">
                    ⚠️ {disqualifiedFindings.length} eligibility warning(s) detected
                  </span>
                  <button
                    onClick={() => handleSend("how to fix this")}
                    className="text-primary hover:underline font-semibold text-[11px] shrink-0"
                  >
                    Fix with AI &rarr;
                  </button>
                </div>
              )}

              {/* Chat Messages */}
              <div className="flex-1 overflow-y-auto p-3.5 space-y-3 text-xs overscroll-contain">
                {messages.map((m, idx) => {
                  const { cleanText, actions } = parseMessageWithActions(m.text);

                  return (
                    <div
                      key={idx}
                      className={`flex flex-col gap-1.5 ${m.role === "user" ? "items-end" : "items-start"}`}
                    >
                      <div className={`flex gap-2 ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                        {m.role === "assistant" && (
                          <div className="size-5 shrink-0 rounded-full bg-primary/10 flex items-center justify-center text-primary mt-0.5">
                            <Bot className="size-3" />
                          </div>
                        )}
                        <div
                          className={`max-w-[88%] rounded-xl px-3 py-2 leading-relaxed ${
                            m.role === "user"
                              ? "bg-primary text-primary-foreground font-medium rounded-tr-none text-xs"
                              : "bg-muted/70 text-foreground border rounded-tl-none whitespace-pre-wrap text-xs"
                          }`}
                        >
                          {cleanText}
                        </div>
                      </div>

                      {/* One-Click Action Buttons if available */}
                      {actions.length > 0 && (
                        <div className="ml-7 mt-1 space-y-1.5">
                          {actions.map((act, aIdx) => (
                            <Button
                              key={aIdx}
                              onClick={() => void handleApplyIntakeAction(act)}
                              disabled={Boolean(applyingAction)}
                              className="h-7 text-[11px] font-semibold bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-1.5 shadow-sm"
                            >
                              {applyingAction === act.key ? (
                                <Loader2 className="size-3 animate-spin" />
                              ) : (
                                <Zap className="size-3 fill-current" />
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
                  <div className="flex gap-2 items-center text-muted-foreground text-[11px] pl-1">
                    <Loader2 className="size-3 animate-spin text-primary" />
                    <span>AI assistant is formulating response...</span>
                  </div>
                )}

                {error && (
                  <div className="rounded-lg bg-rose-500/10 border border-rose-500/20 p-2 text-rose-600 text-[11px]">
                    {error}
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Quick Prompts Suggestions */}
              {messages.length <= 2 && (
                <div className="px-2.5 py-1.5 border-t bg-muted/20 flex flex-wrap gap-1 shrink-0">
                  {quickPrompts.slice(0, 3).map((prompt) => (
                    <button
                      key={prompt}
                      onClick={() => void handleSend(prompt)}
                      disabled={sending || Boolean(applyingAction)}
                      className="rounded-full border bg-background px-2 py-0.5 text-[10px] text-muted-foreground hover:border-primary hover:text-primary transition-colors text-left truncate max-w-full"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              )}

              {/* Footer Input Form */}
              <div className="border-t bg-background p-2.5 shrink-0">
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    void handleSend();
                  }}
                  className="flex items-center gap-1.5"
                >
                  <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={
                      visaCategory === "student"
                        ? "Ask about COE, admission, part-time work..."
                        : visaCategory === "work"
                        ? "Ask about employer category, tax proof..."
                        : visaCategory === "tourist"
                        ? "Ask about itinerary, financial proof..."
                        : "Ask any visa or checklist question..."
                    }
                    className="flex-1 rounded-lg border bg-muted/30 px-2.5 py-1.5 text-xs outline-none focus:border-primary focus:bg-background focus:ring-1 focus:ring-primary"
                    disabled={sending || Boolean(applyingAction)}
                  />
                  <Button
                    type="submit"
                    disabled={sending || !input.trim() || Boolean(applyingAction)}
                    className="h-7 px-2.5 text-xs shrink-0"
                  >
                    {sending ? <Loader2 className="size-3 animate-spin" /> : <Send className="size-3" />}
                  </Button>
                </form>
                <div className="mt-1 flex items-center justify-between text-[9px] text-muted-foreground/70 px-0.5">
                  <span>💡 Drag header to move anywhere</span>
                  <span>Official immigration grounded</span>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </>
  );
}

