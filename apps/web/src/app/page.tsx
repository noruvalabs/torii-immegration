import Link from "next/link";
import { ArrowRight, ShieldCheck, FileCheck2, Languages } from "lucide-react";
import { LandingAuthLink } from "@/components/landing-auth-link";

const PILLARS = [
  {
    icon: FileCheck2,
    title: "Guided, not guesswork",
    body: "A branching intake, a personalized document checklist, and auto-filled government forms — only what your case needs.",
  },
  {
    icon: ShieldCheck,
    title: "Sourced, not asserted",
    body: "Every instruction links to the official government page it came from. If it can't be sourced, we don't show it.",
  },
  {
    icon: Languages,
    title: "In your language",
    body: "Every step in your language and the host country's, with the exact official term always kept alongside.",
  },
];

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col px-6">
      <header className="flex h-16 items-center gap-2">
        <span className="text-xl" aria-hidden>
          ⛩️
        </span>
        <span className="text-lg font-semibold tracking-tight">Torii</span>
        <div className="ml-auto">
          <LandingAuthLink />
        </div>
      </header>

      <section className="flex flex-1 flex-col justify-center py-16">
        <p className="text-sm font-medium text-primary">Guided form preparation for immigration</p>
        <h1 className="mt-3 max-w-2xl text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
          Renew, change, or file your visa — correctly, in your language, for a fraction of a
          lawyer&apos;s fee.
        </h1>
        <p className="mt-5 max-w-2xl text-lg text-muted-foreground">
          Torii walks you from &ldquo;which forms do I even need?&rdquo; to a submission-ready
          packet. It helps you prepare your own filing — it is{" "}
          <strong className="font-medium text-foreground">not a legal advisor</strong>, and it
          routes you to a licensed professional the moment your case needs one.
        </p>

        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/scope"
            className="inline-flex items-center gap-2 rounded-[var(--radius)] bg-primary px-5 py-3 text-sm font-medium text-primary-foreground hover:opacity-90"
          >
            Start your case <ArrowRight className="size-4" />
          </Link>
          <Link
            href="/admin"
            className="inline-flex items-center gap-2 rounded-[var(--radius)] border px-5 py-3 text-sm font-medium hover:bg-accent"
          >
            Admin dashboard
          </Link>
        </div>

        <div className="mt-16 grid gap-6 sm:grid-cols-3">
          {PILLARS.map((p) => {
            const Icon = p.icon;
            return (
              <div key={p.title}>
                <Icon className="size-5 text-primary" />
                <h2 className="mt-3 text-sm font-semibold">{p.title}</h2>
                <p className="mt-1 text-sm text-muted-foreground">{p.body}</p>
              </div>
            );
          })}
        </div>
      </section>

      <footer className="border-t py-6 text-xs text-muted-foreground">
        Torii is a working codename. Guided form preparation — not legal advice.
      </footer>
    </main>
  );
}
