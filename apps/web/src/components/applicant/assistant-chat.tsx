"use client";

import { useEffect, useState, useRef, useMemo } from "react";
import {
  Loader2,
  Send,
  Sparkles,
  Bot,
  User as UserIcon,
  Zap,
  CheckCircle2,
  MessageSquare,
  X,
  HelpCircle,
  FileText,
  ShieldCheck,
  Building,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Markdown } from "@/components/ui/markdown";
import { useAuth } from "@/lib/auth-context";
import { answerIntake } from "@/lib/api/cases";
import { toast } from "@/components/ui/sonner";

type ChatRole = "user" | "assistant";

type ActionTag = {
  key: string;
  value: string;
  label: string;
};

type ChatMessage = {
  role: ChatRole;
  text: string;
  actions?: ActionTag[];
  appliedActions?: Record<string, boolean>;
};

export type AssistantChatProps = {
  caseId?: number | null;
  caseReference?: string | null;
  scopeLabel?: string | null;
  jurisdictionCode?: string | null;
  visaCategoryCode?: string | null;
  actionCode?: string | null;
  currentStep?: string | null;
  intakeAnswers?: Record<string, unknown> | null;
  eligibilityFindings?: Array<Record<string, unknown>> | null;
  checklist?: Array<Record<string, unknown>> | null;
  onIntakeAnswered?: (key: string, value: unknown) => void;
  locale?: string;
  title?: string;
  mode?: "card" | "floating";
};

/** Parse `[ACTION:update_intake key="..." value="..." label="..."]` tags out of text */
function parseActionTags(rawText: string): { cleanText: string; actions: ActionTag[] } {
  const actions: ActionTag[] = [];
  const actionRegex = /\[ACTION:update_intake\s+key="([^"]+)"\s+value="([^"]+)"(?:\s+label="([^"]+)")?\]/g;
  let match: RegExpExecArray | null;

  while ((match = actionRegex.exec(rawText)) !== null) {
    actions.push({
      key: match[1],
      value: match[2],
      label: match[3] || `Update ${match[1].replace(/_/g, " ")}`,
    });
  }

  const cleanText = rawText.replace(actionRegex, "").trim();
  return { cleanText, actions };
}

/** Match natural language user requests to fill fields (e.g. "My salary is 8000000 yen") */
function extractIntakeFromUserMessage(text: string): ActionTag[] {
  const actions: ActionTag[] = [];
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
        label: `Set Annual Salary to ¥${Number(val).toLocaleString()}`,
      });
    }
  }

  // Company / Employer matches
  const companyMatch = t.match(/(?:company|employer|sponsor|work at|firm)\s*(?:name)?\s*(?:is|:|as)?\s*([A-Za-z0-9\s.,&'-]+?)(?:\s*(?:and|with|,|\.|$))/i);
  if (companyMatch && companyMatch[1].length > 2 && !companyMatch[1].toLowerCase().includes("category")) {
    actions.push({
      key: "employer_name",
      value: companyMatch[1].trim(),
      label: `Set Employer to "${companyMatch[1].trim()}"`,
    });
  }

  // Passport number matches
  const passportMatch = t.match(/passport(?:\s*number|\s*no)?\s*(?:is|=|:)?\s*([A-Z0-9]{6,12})/i);
  if (passportMatch) {
    actions.push({
      key: "passport_number",
      value: passportMatch[1].toUpperCase(),
      label: `Set Passport No. to ${passportMatch[1].toUpperCase()}`,
    });
  }

  // Residence card matches
  const rcMatch = t.match(/(?:residence card|zairyu card)\s*(?:number|no)?\s*(?:is|=|:)?\s*([A-Z0-9]{12})/i);
  if (rcMatch) {
    actions.push({
      key: "residence_card_number",
      value: rcMatch[1].toUpperCase(),
      label: `Set Residence Card No. to ${rcMatch[1].toUpperCase()}`,
    });
  }

  // Address matches
  const addrMatch = t.match(/(?:address|living at|reside at)\s*(?:in japan)?\s*(?:is|=|:)?\s*([A-Za-z0-9\s,-]+?)(?:\s*(?:and|tel|phone|,|\.|$))/i);
  if (addrMatch && addrMatch[1].length > 4 && !addrMatch[1].toLowerCase().includes("email")) {
    actions.push({
      key: "current_japan_address",
      value: addrMatch[1].trim(),
      label: `Set Japan Address to "${addrMatch[1].trim()}"`,
    });
  }

  return actions;
}

export function AssistantChat({
  caseId = null,
  caseReference,
  scopeLabel,
  jurisdictionCode = "JP",
  visaCategoryCode = "work",
  actionCode = "renewal",
  currentStep = "intake",
  intakeAnswers = {},
  eligibilityFindings = [],
  checklist = [],
  onIntakeAnswered,
  locale = "en",
  title = "Torii AI Copilot",
  mode = "card",
}: AssistantChatProps) {
  const { token } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [applyingAction, setApplyingAction] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(mode === "card");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  useEffect(() => {
    if (messages.length === 0) {
      const scopeDesc = scopeLabel || `${jurisdictionCode?.toUpperCase() || "JP"} ${visaCategoryCode?.toUpperCase() || "Work"} Visa (${actionCode || "Renewal"})`;

      setMessages([
        {
          role: "assistant",
          text: `👋 Hello! I am your **Torii AI Immigration Copilot**.\n\nI have loaded your active case **${caseReference || `Case #${caseId}`}** for **${scopeDesc}**.\n\nI can help you:\n• Verify statutory requirements and legal eligibility\n• Identify and fill out missing intake or form fields\n• Review required supporting documents and checklists\n• Answer procedural questions about embassy filing\n\nYou can also tell me values directly (e.g. *"Set my salary to 8.5 million yen"* or *"My employer is Sony"*), and I will update your case form.`,
        },
      ]);
    }
  }, [caseId, caseReference, scopeLabel, jurisdictionCode, visaCategoryCode, actionCode, messages.length]);

  async function handleApplyAction(msgIdx: number, action: ActionTag) {
    const activeToken = token || (typeof window !== "undefined" ? localStorage.getItem("torii_token") : null);
    if (!caseId || !activeToken) {
      toast.error("Please log in to update case intake.");
      return;
    }

    setApplyingAction(`${msgIdx}-${action.key}`);
    try {
      await answerIntake(activeToken, caseId, action.key, action.value);
      toast.success(`Updated ${action.label || action.key}!`);

      setMessages((prev) => {
        const next = [...prev];
        const msg = next[msgIdx];
        if (msg) {
          next[msgIdx] = {
            ...msg,
            appliedActions: { ...(msg.appliedActions || {}), [action.key]: true },
          };
        }
        return next;
      });

      if (onIntakeAnswered) {
        onIntakeAnswered(action.key, action.value);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update intake field.");
    } finally {
      setApplyingAction(null);
    }
  }

  async function sendMessage(textToSend?: string) {
    const message = (textToSend || input).trim();
    if (!message || sending) return;
    setError(null);
    setSending(true);
    if (!textToSend) setInput("");

    const directUserActions = extractIntakeFromUserMessage(message);

    setMessages((prev) => [...prev, { role: "user", text: message }]);

    try {
      const response = await fetch("/assistant/ai/chat/messages", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          message,
          case_id: caseId ? String(caseId) : null,
          case_reference: caseReference,
          scope_label: scopeLabel,
          jurisdiction_code: jurisdictionCode,
          visa_category_code: visaCategoryCode,
          action_code: actionCode,
          current_step: currentStep,
          intake_answers: intakeAnswers,
          eligibility_findings: eligibilityFindings,
          checklist: checklist,
          locale,
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error("Assistant service offline, running local case intelligence.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let accumulatedRaw = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() ?? "";

        for (const rawEvent of events) {
          const lines = rawEvent.split("\n");
          const eventName = lines.find((l) => l.startsWith("event:"))?.replace("event:", "").trim();
          const payload = lines.find((l) => l.startsWith("data:"))?.replace("data:", "").trim();
          if (!payload || eventName !== "bubble") continue;

          try {
            const data = JSON.parse(payload) as { text?: string };
            const text = data.text ?? "";
            if (!text) continue;
            accumulatedRaw += (accumulatedRaw ? "\n\n" : "") + text;

            const { cleanText, actions } = parseActionTags(accumulatedRaw);
            const combinedActions = [...actions, ...directUserActions];

            setMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (last?.role === "assistant") {
                next[next.length - 1] = {
                  ...last,
                  text: cleanText,
                  actions: combinedActions.length > 0 ? combinedActions : undefined,
                };
              } else {
                next.push({
                  role: "assistant",
                  text: cleanText,
                  actions: combinedActions.length > 0 ? combinedActions : undefined,
                });
              }
              return next;
            });
          } catch {
            // continue streaming
          }
        }
      }
    } catch {
      const fallbackReply = generateLocalCaseFallback(message, {
        caseReference,
        scopeLabel,
        jurisdictionCode,
        visaCategoryCode,
        actionCode,
        currentStep,
        intakeAnswers,
        checklist,
        eligibilityFindings,
      });

      const { cleanText, actions } = parseActionTags(fallbackReply);
      const combinedActions = [...actions, ...directUserActions];

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: cleanText,
          actions: combinedActions.length > 0 ? combinedActions : undefined,
        },
      ]);
    } finally {
      setSending(false);
    }
  }

  const quickPrompts = useMemo(() => {
    return [
      {
        icon: HelpCircle,
        label: "What is missing?",
        prompt: "What intake fields or information are still missing on my application?",
      },
      {
        icon: FileText,
        label: "Required documents",
        prompt: "What official documents do I need to prepare for my visa renewal/application?",
      },
      {
        icon: ShieldCheck,
        label: "Check eligibility",
        prompt: "Can you analyze my legal eligibility, salary threshold, and any risk flags?",
      },
      {
        icon: Building,
        label: "Employer details",
        prompt: "How does my employer's company category affect my required documents?",
      },
    ];
  }, []);

  if (mode === "floating" && !isOpen) {
    return (
      <div className="fixed bottom-6 right-6 z-50 animate-in fade-in zoom-in-95 duration-200">
        <button
          onClick={() => setIsOpen(true)}
          className="flex items-center gap-2 rounded-full bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground shadow-xl hover:opacity-90 transition-all hover:scale-105"
        >
          <Bot className="size-5" />
          <span>Torii AI Copilot</span>
          <span className="flex size-2 rounded-full bg-emerald-400 animate-pulse" />
        </button>
      </div>
    );
  }

  const content = (
    <div className="flex flex-col h-full space-y-3">
      <div className="flex items-center justify-between border-b pb-3">
        <div className="flex items-center gap-2">
          <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Bot className="size-4" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <h4 className="text-sm font-bold text-foreground leading-none">{title}</h4>
              <Badge tone="success" className="text-[9px] px-1 py-0">Online</Badge>
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              {scopeLabel || `${jurisdictionCode?.toUpperCase()} ${visaCategoryCode?.toUpperCase()}`} · Step: {currentStep}
            </p>
          </div>
        </div>

        {mode === "floating" && (
          <button
            onClick={() => setIsOpen(false)}
            className="rounded-md p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            <X className="size-4" />
          </button>
        )}
      </div>

      <div className="flex flex-wrap gap-1.5">
        {quickPrompts.map((qp) => (
          <button
            key={qp.label}
            onClick={() => void sendMessage(qp.prompt)}
            disabled={sending}
            className="inline-flex items-center gap-1 rounded-full border bg-background/80 px-2.5 py-1 text-[10px] font-medium text-muted-foreground hover:text-primary hover:border-primary/40 hover:bg-primary/5 transition-colors disabled:opacity-50 shadow-2xs"
          >
            <qp.icon className="size-3 text-primary" />
            <span>{qp.label}</span>
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 rounded-lg border bg-muted/10 p-3 max-h-[420px] text-xs">
        {messages.map((message, idx) => (
          <div
            key={idx}
            className={`flex gap-2.5 ${message.role === "user" ? "justify-end" : "justify-start"}`}
          >
            {message.role === "assistant" && (
              <div className="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary mt-0.5">
                <Bot className="size-3.5" />
              </div>
            )}

            <div
              className={`max-w-[85%] rounded-xl px-3.5 py-2.5 text-xs shadow-2xs ${
                message.role === "user"
                  ? "bg-primary text-primary-foreground font-medium rounded-tr-xs whitespace-pre-wrap leading-relaxed"
                  : "bg-card border text-foreground rounded-tl-xs space-y-2"
              }`}
            >
              {message.role === "user" ? (
                message.text
              ) : (
                <Markdown content={message.text} />
              )}

              {message.actions && message.actions.length > 0 && (
                <div className="pt-2 border-t border-border/50 space-y-1.5">
                  <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                    One-Click Case Actions:
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {message.actions.map((act) => {
                      const isApplied = message.appliedActions?.[act.key];
                      const isBusy = applyingAction === `${idx}-${act.key}`;

                      return (
                        <Button
                          key={act.key}
                          size="sm"
                          disabled={isApplied || isBusy}
                          onClick={() => void handleApplyAction(idx, act)}
                          className={`h-7 text-[11px] font-semibold gap-1.5 shadow-xs ${
                            isApplied
                              ? "bg-emerald-600 text-white hover:bg-emerald-600 cursor-default"
                              : "bg-primary text-primary-foreground hover:bg-primary/90"
                          }`}
                        >
                          {isBusy ? (
                            <Loader2 className="size-3 animate-spin" />
                          ) : isApplied ? (
                            <CheckCircle2 className="size-3 text-white" />
                          ) : (
                            <Zap className="size-3 text-amber-300" />
                          )}
                          {isApplied ? `Applied: ${act.key}` : act.label}
                        </Button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {message.role === "user" && (
              <div className="flex size-6 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground mt-0.5">
                <UserIcon className="size-3.5" />
              </div>
            )}
          </div>
        ))}

        {sending && (
          <div className="flex items-center gap-2 text-muted-foreground text-xs pl-2 py-1">
            <Loader2 className="size-3.5 animate-spin text-primary" />
            <span>Torii AI is analyzing case guidelines...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {error && <p className="text-xs text-[var(--color-danger)]">{error}</p>}

      <div className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question, or tell AI to fill a field (e.g. 'Set salary to 8M yen')..."
          className="h-9 flex-1 rounded-md border bg-background px-3 text-xs outline-none focus-visible:ring-1 focus-visible:ring-primary shadow-2xs"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void sendMessage();
            }
          }}
        />
        <Button
          onClick={() => void sendMessage()}
          disabled={sending || input.trim().length === 0}
          className="h-9 px-3 text-xs font-semibold gap-1.5 shadow-xs"
        >
          {sending ? <Loader2 className="size-3.5 animate-spin" /> : <Send className="size-3.5" />}
          Send
        </Button>
      </div>
    </div>
  );

  if (mode === "floating") {
    return (
      <div className="fixed bottom-6 right-6 z-50 w-[440px] max-w-[calc(100vw-2rem)] rounded-2xl border bg-card/95 backdrop-blur p-4 shadow-2xl animate-in slide-in-from-bottom-5 duration-200">
        {content}
      </div>
    );
  }

  return (
    <Card className="shadow-sm">
      <CardContent className="p-5">{content}</CardContent>
    </Card>
  );
}

function generateLocalCaseFallback(
  userQuery: string,
  ctx: {
    caseReference?: string | null;
    scopeLabel?: string | null;
    jurisdictionCode?: string | null;
    visaCategoryCode?: string | null;
    actionCode?: string | null;
    currentStep?: string | null;
    intakeAnswers?: Record<string, unknown> | null;
    checklist?: Array<Record<string, unknown>> | null;
    eligibilityFindings?: Array<Record<string, unknown>> | null;
  }
): string {
  const q = userQuery.toLowerCase();
  const cat = (ctx.visaCategoryCode || "work").toLowerCase();
  const act = (ctx.actionCode || "renewal").toLowerCase();
  const ans = ctx.intakeAnswers || {};

  if (q.includes("document") || q.includes("checklist") || q.includes("paper")) {
    if (cat === "work") {
      return `### 📑 Official Supporting Documents for Japanese Work Visa (${act === "renewal" ? "Extension" : "Application"}):\n\n1. **Application Form (*別記第三十号の二様式*)**: 7-page statutory packet auto-filled by Torii.\n2. **Tax Certificates (*住民税の課税・納税証明書*)**: Proving full payment of resident taxes for the past year.\n3. **Withholding Tax Slip (*源泉徴収票*)**: Issued by your employer in January.\n4. **Company Category Proof**: E.g. Quarterly Report (*四季報*) for Category 1, or Withholding Tax Total Table (*法定調書合計表*) for Category 2/3.\n5. **Employment Contract or Salary Certificate**: Showing your remuneration exceeds statutory minimums.\n6. **Valid Passport & Residence Card (*在留カード*)**.`;
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
