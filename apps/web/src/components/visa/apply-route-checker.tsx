"use client";

import { useMemo, useState } from "react";
import {
  BadgeCheck,
  Building2,
  Check,
  Globe,
  Moon,
  Palmtree,
  UserCheck,
  ExternalLink,
  Info,
} from "lucide-react";
import type { Country } from "@/lib/countries";
import {
  detectSaudiRoute,
  type ApplyChannel,
  type ApplyPurpose,
  type TravellerConditions,
} from "@/lib/apply-route";
import { cn } from "@/lib/utils";

const CHANNEL_STYLES: Record<
  ApplyChannel,
  { panel: string; badge: string; Icon: typeof Globe }
> = {
  online: {
    panel: "border-emerald-500/40 bg-emerald-500/10",
    badge: "bg-emerald-500 text-white",
    Icon: Globe,
  },
  in_person: {
    panel: "border-amber-500/40 bg-amber-500/10",
    badge: "bg-amber-500 text-white",
    Icon: Building2,
  },
  agent: {
    panel: "border-violet-500/40 bg-violet-500/10",
    badge: "bg-violet-500 text-white",
    Icon: UserCheck,
  },
  visa_free: {
    panel: "border-teal-500/40 bg-teal-500/10",
    badge: "bg-teal-500 text-white",
    Icon: BadgeCheck,
  },
  citizen: {
    panel: "border-teal-500/40 bg-teal-500/10",
    badge: "bg-teal-500 text-white",
    Icon: BadgeCheck,
  },
};

const CONDITION_OPTIONS: {
  key: keyof TravellerConditions;
  label: string;
  hint: string;
}[] = [
  {
    key: "usedWesternVisa",
    label: "I have a US / UK / Schengen visa",
    hint: "Tourist or business, still valid, already used once",
  },
  {
    key: "westernPermanentResidence",
    label: "I permanently live in the US / UK / EU",
    hint: "Permanent residence permit",
  },
  {
    key: "gccResidence",
    label: "I live in a GCC country",
    hint: "UAE, Bahrain, Kuwait, Oman or Qatar — residence valid 3+ more months",
  },
];

export function ApplyRouteChecker({
  passportCountry,
  onStartApplication,
}: {
  passportCountry: Country | null;
  onStartApplication: () => void;
}) {
  const [purpose, setPurpose] = useState<ApplyPurpose>("tourism");
  const [conditions, setConditions] = useState<TravellerConditions>({
    usedWesternVisa: false,
    westernPermanentResidence: false,
    gccResidence: false,
  });

  const route = useMemo(
    () =>
      passportCountry
        ? detectSaudiRoute({ passportCode: passportCountry.code, purpose, conditions })
        : null,
    [passportCountry, purpose, conditions],
  );

  const styles = route ? CHANNEL_STYLES[route.channel] : null;
  const ResultIcon = styles?.Icon ?? Globe;
  const needsConditions =
    route != null &&
    (route.kind === "online_package" ||
      route.kind === "in_person_consular" ||
      route.kind === "agent_umrah" ||
      route.kind === "online_conditional");

  return (
    <section id="apply-route" className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 pt-8">
      <div className="rounded-2xl border border-border bg-card p-5 sm:p-7 shadow-sm">
        <div className="flex items-start gap-3">
          <span className="mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Globe className="size-5" />
          </span>
          <div>
            <h2 className="text-xl font-bold tracking-tight">
              How can you apply? We detect it from your passport
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Saudi Arabia does not offer the same application route to everyone. The route
              depends on your passport country — online for some, in person for others.
              {passportCountry
                ? " Your route is shown below."
                : " Select your passport country above first, then check here."}
            </p>
          </div>
        </div>

        {/* Purpose toggle */}
        <div className="mt-5 flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium text-muted-foreground">I want to go for:</span>
          <div className="inline-flex rounded-full border border-border bg-background p-1">
            {(
              [
                { value: "tourism", label: "Tourism / Visit", Icon: Palmtree },
                { value: "umrah", label: "Umrah", Icon: Moon },
              ] as const
            ).map(({ value, label, Icon }) => (
              <button
                key={value}
                type="button"
                onClick={() => setPurpose(value)}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-sm font-medium transition",
                  purpose === value
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                <Icon className="size-4" />
                {label}
              </button>
            ))}
          </div>
        </div>

        {!passportCountry && (
          <div className="mt-5 flex items-center gap-2 rounded-xl border border-dashed border-border bg-background/60 px-4 py-3 text-sm text-muted-foreground">
            <Info className="size-4 shrink-0" />
            Select your passport country in the hero above — your personal application route
            will appear here instantly.
          </div>
        )}

        {passportCountry && route && styles && (
          <>
            {needsConditions && (
              <div className="mt-5">
                <p className="text-sm font-medium">
                  Do any of these apply to you?{" "}
                  <span className="font-normal text-muted-foreground">
                    (They can unlock the fully online eVisa for {passportCountry.name} passport
                    holders.)
                  </span>
                </p>
                <div className="mt-2.5 grid gap-2 sm:grid-cols-3">
                  {CONDITION_OPTIONS.map(({ key, label, hint }) => {
                    const active = conditions[key];
                    return (
                      <button
                        key={key}
                        type="button"
                        aria-pressed={active}
                        onClick={() =>
                          setConditions((c) => ({ ...c, [key]: !c[key] }))
                        }
                        className={cn(
                          "rounded-xl border px-3.5 py-3 text-left transition",
                          active
                            ? "border-primary bg-primary/10"
                            : "border-border bg-background hover:border-primary/50",
                        )}
                      >
                        <span className="flex items-center gap-2 text-sm font-semibold">
                          <span
                            className={cn(
                              "flex size-4.5 shrink-0 items-center justify-center rounded border",
                              active
                                ? "border-primary bg-primary text-primary-foreground"
                                : "border-muted-foreground/40",
                            )}
                          >
                            {active && <Check className="size-3" />}
                          </span>
                          {label}
                        </span>
                        <span className="mt-1 block pl-6.5 text-xs text-muted-foreground">
                          {hint}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            <div className={cn("mt-5 rounded-2xl border p-5", styles.panel)}>
              <div className="flex flex-wrap items-center gap-2.5">
                <span
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold tracking-wide",
                    styles.badge,
                  )}
                >
                  <ResultIcon className="size-3.5" />
                  {route.badge}
                </span>
                <h3 className="text-lg font-bold">{route.title}</h3>
              </div>
              <p className="mt-2 text-sm leading-relaxed text-foreground/90">{route.summary}</p>
              <ul className="mt-3 space-y-1.5">
                {route.facts.map((fact) => (
                  <li key={fact.slice(0, 32)} className="flex gap-2 text-sm">
                    <Check className="mt-0.5 size-4 shrink-0 text-primary" />
                    <span>{fact}</span>
                  </li>
                ))}
              </ul>
              {route.feeNote && (
                <p className="mt-3 text-sm font-medium">💰 {route.feeNote}</p>
              )}
              {route.warning && (
                <p className="mt-3 rounded-lg bg-amber-500/15 px-3 py-2 text-sm font-medium text-amber-700 dark:text-amber-300">
                  ⚠️ {route.warning}
                </p>
              )}
              <div className="mt-4 flex flex-wrap items-center gap-3">
                {route.channel !== "citizen" && route.channel !== "visa_free" && (
                  <button
                    type="button"
                    onClick={onStartApplication}
                    className="inline-flex items-center gap-2 rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow-sm transition hover:opacity-90"
                  >
                    Start my application with Torii
                  </button>
                )}
                <a
                  href={route.sourceUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground underline-offset-2 hover:underline"
                >
                  {route.sourceName}
                  <ExternalLink className="size-3" />
                </a>
              </div>
            </div>
          </>
        )}
      </div>
    </section>
  );
}
