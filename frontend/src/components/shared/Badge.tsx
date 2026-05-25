import { cn } from "@/lib/utils";

type Variant = "pos" | "neg" | "neutral" | "accent" | "warn" | "info" | "muted";

const variantClass: Record<Variant, string> = {
  pos:     "bg-pos/10 text-pos border border-pos/20",
  neg:     "bg-neg/10 text-neg border border-neg/20",
  neutral: "bg-subtle/30 text-secondary border border-line",
  accent:  "bg-accent-soft/40 text-accent border border-accent/20",
  warn:    "bg-warn/10 text-warn border border-warn/20",
  info:    "bg-info/10 text-info border border-info/20",
  muted:   "bg-raised text-muted border border-line",
};

interface BadgeProps {
  variant?: Variant;
  children: React.ReactNode;
  className?: string;
}

export default function Badge({ variant = "muted", children, className }: BadgeProps) {
  return (
    <span className={cn("inline-flex items-center rounded px-1.5 py-0.5 text-2xs font-medium", variantClass[variant], className)}>
      {children}
    </span>
  );
}

export function sentimentVariant(s: string): Variant {
  if (s === "positive") return "pos";
  if (s === "negative") return "neg";
  return "neutral";
}
