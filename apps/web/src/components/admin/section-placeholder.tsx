import type { LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

type Props = {
  icon: LucideIcon;
  title: string;
  description: string;
  /** The user stories this surface will satisfy — kept visible so the scaffold maps to the spec. */
  stories?: string[];
  /** Bullet points describing what will live here. */
  capabilities?: string[];
};

/** A consistent "not-built-yet" surface for back-office sections. It documents intent (spec
 *  stories + planned capabilities) rather than faking data, so the shell reads honestly. */
export function SectionPlaceholder({ icon: Icon, title, description, stories, capabilities }: Props) {
  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6 flex items-start gap-4">
        <div className="flex size-11 shrink-0 items-center justify-center rounded-[var(--radius)] bg-accent text-accent-foreground">
          <Icon className="size-5" />
        </div>
        <div>
          <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        </div>
      </div>

      {capabilities && capabilities.length > 0 && (
        <Card className="mb-4">
          <CardContent className="pt-5">
            <ul className="space-y-2 text-sm">
              {capabilities.map((c) => (
                <li key={c} className="flex gap-2">
                  <span className="mt-2 size-1.5 shrink-0 rounded-full bg-primary" />
                  <span>{c}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="muted">Scaffold</Badge>
        {stories?.map((s) => (
          <Badge key={s} tone="default">
            {s}
          </Badge>
        ))}
      </div>
    </div>
  );
}
