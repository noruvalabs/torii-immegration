"use client";

import { useEffect, useState } from "react";
import { Loader2, Send } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

type ChatRole = "user" | "assistant";
type ChatMessage = { role: ChatRole; text: string };

type AssistantChatProps = {
  caseId?: number | null;
  locale?: string;
  title?: string;
};

export function AssistantChat({
  caseId = null,
  locale = "en",
  title = "Ask procedural questions",
}: AssistantChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const res = await fetch("/assistant/ai/chat/session", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            case_id: caseId ? String(caseId) : null,
            locale,
          }),
        });
        if (!res.ok) return;
        const data = (await res.json()) as {
          messages?: { role?: string; content?: string }[];
        };
        const hydrated = (data.messages ?? [])
          .filter((m) => m.role === "assistant" || m.role === "user")
          .map((m) => ({ role: m.role as ChatRole, text: m.content ?? "" }));
        setMessages(hydrated);
      } catch {
        // Keep chat optional if AI service is unavailable.
      }
    })();
  }, [caseId, locale]);

  async function sendMessage() {
    const message = input.trim();
    if (!message || sending) return;
    setError(null);
    setSending(true);
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: message }]);
    try {
      const response = await fetch("/assistant/ai/chat/messages", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          message,
          case_id: caseId ? String(caseId) : null,
          locale,
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
          const data = JSON.parse(payload) as { text?: string };
          const text = data.text ?? "";
          if (!text) continue;
          assistantText += (assistantText ? "\n\n" : "") + text;
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
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to send message");
    } finally {
      setSending(false);
    }
  }

  return (
    <Card>
      <CardContent className="space-y-4 pt-5">
        <div>
          <h3 className="text-sm font-medium text-muted-foreground">{title}</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            Assistant provides source-grounded procedural guidance, not legal advice.
          </p>
        </div>
        <div className="max-h-96 space-y-2 overflow-y-auto rounded-[var(--radius)] border p-3">
          {messages.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              Ask things like: &quot;What documents should I gather first?&quot;
            </p>
          ) : (
            messages.map((message, idx) => (
              <div
                key={`${message.role}-${idx}`}
                className={`rounded-[var(--radius)] px-3 py-2 text-sm ${
                  message.role === "user"
                    ? "ml-8 bg-primary/10 text-foreground"
                    : "mr-8 bg-muted text-foreground"
                }`}
              >
                {message.text}
              </div>
            ))
          )}
        </div>
        {error && <p className="text-xs text-[var(--color-danger)]">{error}</p>}
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask what to do next..."
            className="h-9 flex-1 rounded-[var(--radius)] border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void sendMessage();
              }
            }}
          />
          <Button
            onClick={() => void sendMessage()}
            disabled={sending || input.trim().length === 0}
          >
            {sending ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Send className="size-4" />
            )}
            Send
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
