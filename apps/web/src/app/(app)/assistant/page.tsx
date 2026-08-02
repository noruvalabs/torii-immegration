"use client";

import { AssistantChat } from "@/components/applicant/assistant-chat";

export default function AssistantPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Assistant</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Ask procedural immigration questions and get grounded help from official sources.
        </p>
      </div>

      <AssistantChat title="Ask the assistant" locale="en" />
    </div>
  );
}
