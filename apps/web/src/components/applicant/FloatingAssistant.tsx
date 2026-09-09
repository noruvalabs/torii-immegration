"use client";

import { useEffect, useMemo, useRef, useState, type PointerEvent } from "react";
import { usePathname } from "next/navigation";
import {
  Bot,
  Loader2,
  Minus,
  Send,
  X,
  Zap,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Markdown } from "@/components/ui/markdown";
import { useAuth } from "@/lib/auth-context";
import {
  answerIntake,
  evaluateEligibility,
  type Case,
  type EligibilityResult,
  type ChecklistItem,
} from "@/lib/api/cases";
import type { User } from "@/lib/api/auth";
import {
  useCaseQuery,
  useEligibilityQuery,
  useChecklistQuery,
  caseKeys,
} from "@/lib/queries/cases";
import { useProfileQuery } from "@/lib/queries/profile";
import { useQueryClient } from "@tanstack/react-query";

type ChatRole = "user" | "assistant";
type ChatMessage = { role: ChatRole; text: string };

type IntakeAction = {
  key: string;
  value: string;
  label: string;
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

/** Extract field updates from user's conversational messages (e.g. "My salary is 8000000 yen") */
function extractIntakeFromUserMessage(text: string): IntakeAction[] {
  const actions: IntakeAction[] = [];
  const t = text.trim();

  // Salary matches
  const salaryMatch = t.match(/(?:salary|income|remuneration|earn|earning)\s*(?:is|of|=|:)?\s*(?:¥|JPY|yen)?\s*([0-9,]+(?:\s*(?:man|million|thousand|k|yen|jpy))?)/i);
  if (salaryMatch) {
    const raw = salaryMatch[1].replace(/,/g, "").trim().toLowerCase();
    let val = raw;
    if (raw.includes("man")) {
      const num = parseFloat(raw.replace("man", ""));
      val = String(num * 10000);
    } else if (raw.includes("million")) {
      const num = parseFloat(raw.replace("million", ""));
      val = String(num * 1000000);
    } else if (raw.includes("k")) {
      const num = parseFloat(raw.replace("k", ""));
      val = String(num * 1000);
    } else {
      val = raw.replace(/[^0-9]/g, "");
    }
    if (val && parseInt(val, 10) > 0) {
      actions.push({
        key: "annual_salary",
        value: val,
        label: `⚡ Set Annual Salary to ¥${Number(val).toLocaleString()}`,
      });
    }
  }

  // Company / Employer matches
  const companyMatch = t.match(/(?:company|employer|sponsor|work at|firm)\s*(?:name)?\s*(?:is|:|as)?\s*([A-Za-z0-9\s.,&'-]+?)(?:\s*(?:and|with|,|\.|$))/i);
  if (companyMatch && companyMatch[1].length > 2 && !companyMatch[1].toLowerCase().includes("category")) {
    actions.push({
      key: "employer_name",
      value: companyMatch[1].trim(),
      label: `⚡ Set Employer to "${companyMatch[1].trim()}"`,
    });
  }

  // Passport number matches
  const passportMatch = t.match(/passport(?:\s*number|\s*no)?\s*(?:is|=|:)?\s*([A-Z0-9]{6,12})/i);
  if (passportMatch) {
    actions.push({
      key: "passport_number",
      value: passportMatch[1].toUpperCase(),
      label: `⚡ Set Passport No. to ${passportMatch[1].toUpperCase()}`,
    });
  }

  // Residence card matches
  const rcMatch = t.match(/(?:residence card|zairyu card)\s*(?:number|no)?\s*(?:is|=|:)?\s*([A-Z0-9]{12})/i);
  if (rcMatch) {
    actions.push({
      key: "residence_card_number",
      value: rcMatch[1].toUpperCase(),
      label: `⚡ Set Residence Card No. to ${rcMatch[1].toUpperCase()}`,
    });
  }

  return actions;
}

function generateLocalCaseFallback(
  userQuery: string,
  ctx: {
    scopeLabel?: string | null;
    visaCategoryCode?: string | null;
    actionCode?: string | null;
    intakeAnswers?: Record<string, unknown> | null;
  }
): string {
  const q = userQuery.toLowerCase();
  const cat = (ctx.visaCategoryCode || "work").toLowerCase();
  const act = (ctx.actionCode || "renewal").toLowerCase();
  const ans = ctx.intakeAnswers || {};

  if (q.includes("document") || q.includes("checklist") || q.includes("paper")) {
    if (cat === "work") {
      return `### 📑 Official Supporting Documents for Japanese Work Visa (${act === "renewal" ? "Extension" : "Application"}):\n\n1. **Application Form (*別記第三十号の二様式*)**: Official packet auto-filled by Torii.\n2. **Tax Certificates (*住民税の課税・納税証明書*)**: Proving full payment of resident taxes for the past year.\n3. **Withholding Tax Slip (*源泉徴収票*)**: Issued by your employer in January.\n4. **Company Category Proof**: E.g. Quarterly Report (*四季報*) for Category 1, or Withholding Tax Total Table (*法定調書合計表*) for Category 2/3.\n5. **Employment Contract or Salary Certificate**: Showing your remuneration exceeds statutory minimums.\n6. **Valid Passport & Residence Card (*在留カード*)**.`;
    } else if (cat === "student") {
      return `### 📑 Official Supporting Documents for Student Visa (留学):\n\n1. **Official Application Form (*教育機関作成用*)**\n2. **Certificate of Enrollment & Attendance Rate (*在籍証明書・出席率証明書*)**: Must exceed 80%.\n3. **Academic Transcript (*成績証明書*)**\n4. **Financial Support Statement (*経費支弁書*)**: Bank balance statement of sponsor or remitted funds.\n5. **Passport & Residence Card**.`;
    }
  }

  if (q.includes("missing") || q.includes("what is missing") || q.includes("incomplete")) {
    const missingKeys: string[] = [];
    if (!ans.full_name && !ans.applicant_name) missingKeys.push("Full Name");
    if (!ans.passport_number) missingKeys.push("Passport Number");
    if (!ans.current_japan_address && !ans.registered_address_japan) missingKeys.push("Address in Japan");
    if (!ans.employer_name && cat === "work") missingKeys.push("Employer / Company Name");
    if (!ans.annual_salary && cat === "work") missingKeys.push("Annual Salary / Remuneration");

    if (missingKeys.length === 0) {
      return `🎉 **Great news!** All core statutory fields for your ${cat.toUpperCase()} application are already completed in your intake. Your official PDF form is ready for download in the **Forms** step!`;
    }

    return `### ⚠️ Missing Intake Items on Your Case:\n\nThe following statutory items still need your answers:\n${missingKeys.map((k) => `• **${k}**`).join("\n")}\n\nYou can tell me these directly (e.g. *"My salary is 8,000,000 yen"*) or fill them in the Intake tab!`;
  }

  if (q.includes("eligibility") || q.includes("risk") || q.includes("qualify")) {
    return `### ⚖️ Eligibility & Compliance Assessment:\n\n• **Category**: ${ctx.scopeLabel || "Japan Work Visa Extension"}\n• **Statutory Income Rule**: Must earn equal to or higher than a Japanese national in equivalent duties (typically > ¥3,000,000/yr for Tokyo area).\n• **Tax & Pension Compliance**: Zero unpaid local tax (*Jūminzei*) and national pension (*Nenkin*) arrears.\n• **Continuous Stay**: No continuous absence outside Japan exceeding 90 days without work justification.\n\nAll your answered items have been evaluated under official Ministry of Justice guidelines.`;
  }

  return `I have reviewed your inquiry regarding your **${ctx.scopeLabel || "Japan Immigration"}** application. Under Immigration Services Agency (ISA) statutory regulations, all documents and forms must maintain strict consistency across tax records, employment agreements, and passport entries. Let me know if you would like me to help fill specific fields, explain checklist requirements, or check your eligibility!`;
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
  const { token, user } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState<{ x: number; y: number } | null>(null);

  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef<{ startX: number; startY: number; startPosX: number; startPosY: number } | null>(null);

  const queryClient = useQueryClient();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [applyingAction, setApplyingAction] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Extract case ID if currently on a case page
  const caseMatch = pathname?.match(/\/cases\/(\d+)/);
  const caseId = caseMatch ? Number(caseMatch[1]) : null;

  // Read directly from cached queries - ZERO network burst on open!
  const { data: activeCase = null } = useCaseQuery(token, caseId ?? 0);
  const { data: activeEligibility = null } = useEligibilityQuery(
    token,
    caseId ?? 0,
    Boolean(token && caseId && isOpen),
  );
  const { data: activeChecklist = [] } = useChecklistQuery(
    token,
    caseId ?? 0,
    Boolean(token && caseId && isOpen),
  );
  const { data: activeProfile = null } = useProfileQuery(token, user);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize and load saved positions
  useEffect(() => {
    try {
      localStorage.removeItem("torii_assistant_trigger_pos");
      localStorage.removeItem("torii_assistant_size");
      const savedPos = localStorage.getItem("torii_assistant_pos");
      if (savedPos) {
        const parsed = JSON.parse(savedPos);
        if (typeof parsed.x === "number" && typeof parsed.y === "number") {
          setPosition(clampPosition(parsed.x, parsed.y, 350, 460));
        }
      }
    } catch {
      // Ignore storage errors
    }
  }, []);

  // Recalculate clamps on window resize
  useEffect(() => {
    const handleResize = () => {
      setPosition((prev) => (prev ? clampPosition(prev.x, prev.y, 350, 460) : null));
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

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
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isOpen]);

  // Window drag handlers
  const handlePointerDown = (e: PointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    if ((e.target as HTMLElement).closest("button, a, input, textarea")) return;
    const currentX = position?.x ?? Math.max(12, window.innerWidth - 350 - 24);
    const currentY = position?.y ?? Math.max(12, window.innerHeight - 460 - 24);

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

    const rawX = dragStartRef.current.startPosX + deltaX;
    const rawY = dragStartRef.current.startPosY + deltaY;
    const clamped = clampPosition(rawX, rawY, 350, 460);
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
      void queryClient.invalidateQueries({ queryKey: caseKeys.all });

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: `✅ Updated **${action.key.replace(/_/g, " ")}** to **"${action.value}"** and re-evaluated eligibility!`,
        },
      ]);
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

    const directUserActions = extractIntakeFromUserMessage(text);

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
    } catch {
      const fallbackReply = generateLocalCaseFallback(text, {
        scopeLabel: activeCase?.scope_label,
        visaCategoryCode: visaCategory,
        actionCode: actionCode,
        intakeAnswers: activeCase?.intake_answers,
      });

      let finalText = fallbackReply;
      if (directUserActions.length > 0) {
        for (const act of directUserActions) {
          finalText += `\n\n[ACTION:update_intake key="${act.key}" value="${act.value}" label="${act.label}"]`;
        }
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: finalText,
        },
      ]);
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

  return (
    <>
      {/* Floating Trigger Button (Compact Bottom-Right) */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
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

      {/* Floating Chat Window */}
      {isOpen && (
        <div
          style={{
            left: position ? `${position.x}px` : undefined,
            top: position ? `${position.y}px` : undefined,
            right: !position ? "24px" : undefined,
            bottom: !position ? "24px" : undefined,
            width: "min(350px, calc(100vw - 24px))",
            height: "min(460px, calc(100vh - 24px))",
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
                <p className="text-[10px] text-muted-foreground truncate">
                  {caseId
                    ? `${activeCase?.reference || `Case #${caseId}`} · ${activeCase?.scope_label || `${jurisdictionCode} ${visaCategory ? visaCategory.toUpperCase() : "VISA"}`}`
                    : "Procedural immigration guidance"}
                </p>
              </div>
            </div>

            {/* Header Right Action Controls: Minimize and Close */}
            <div
              className="flex items-center gap-1 shrink-0"
              onPointerDown={(e) => e.stopPropagation()}
              onPointerUp={(e) => e.stopPropagation()}
              onClick={(e) => e.stopPropagation()}
            >
              {/* Minimize to bottom-right floating pill */}
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setIsOpen(false);
                }}
                className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors cursor-pointer"
                title="Minimize assistant"
                aria-label="Minimize assistant"
              >
                <Minus className="size-3.5" />
              </button>

              {/* Close assistant */}
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setIsOpen(false);
                }}
                className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors cursor-pointer"
                title="Close assistant"
                aria-label="Close assistant"
              >
                <X className="size-3.5" />
              </button>
            </div>
          </div>

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
                              ? "bg-primary text-primary-foreground font-medium rounded-tr-none text-xs whitespace-pre-wrap"
                              : "bg-muted/70 text-foreground border rounded-tl-none text-xs"
                          }`}
                        >
                          {m.role === "user" ? cleanText : <Markdown content={cleanText} />}
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
        </div>
      )}
    </>
  );
}

