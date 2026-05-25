import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function fmtNumber(n: number | null | undefined, opts?: Intl.NumberFormatOptions): string {
  if (n == null) return "—";
  return new Intl.NumberFormat("en-US", opts).format(n);
}

export function fmtMarketCap(n: number | null | undefined): string {
  if (n == null) return "—";
  if (n >= 1e12) return `$${(n / 1e12).toFixed(2)}T`;
  if (n >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `$${(n / 1e6).toFixed(2)}M`;
  return `$${n.toLocaleString()}`;
}

export function fmtPrice(n: number | null | undefined): string {
  if (n == null) return "—";
  return `$${n.toFixed(2)}`;
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function fmtRelative(iso: string | null | undefined): string {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function scoreColor(score: number): string {
  if (score > 0.2) return "text-pos";
  if (score < -0.2) return "text-neg";
  return "text-secondary";
}

export function sentimentColor(s: string): string {
  if (s === "positive") return "text-pos";
  if (s === "negative") return "text-neg";
  return "text-secondary";
}

export function eventLabel(e: string): string {
  return e.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
