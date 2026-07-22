import { BarChart3 } from "lucide-react";
import { SectionPlaceholder } from "@/components/admin/section-placeholder";

export default function ReportsPage() {
  return (
    <SectionPlaceholder
      icon={BarChart3}
      title="Reports"
      description="Run the platform on evidence — especially the accuracy and source-freshness numbers the whole promise rests on."
      capabilities={[
        "Case throughput: started, completed, submitted, escalated over a date range",
        "Accuracy signals: review-flag rates, regenerations, reported rejections",
        "Source freshness: what's flagged as changed and how long it has waited",
        "Business metrics: conversion to paid, subscription/employer coverage, referrals",
      ]}
      stories={["US-31", "C18"]}
    />
  );
}
