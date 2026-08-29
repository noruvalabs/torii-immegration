"use client";

import { AssistantChat } from "@/components/applicant/assistant-chat";
import { AppBreadcrumb } from "@/components/breadcrumb-nav";

export default function AssistantPage() {
  return (
    <div className="w-full max-w-7xl mx-auto space-y-6">
      <AppBreadcrumb />

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
