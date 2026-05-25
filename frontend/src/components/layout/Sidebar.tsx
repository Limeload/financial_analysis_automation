"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Newspaper,
  BarChart3,
  TrendingUp,
  Radio,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/",         label: "Dashboard",  icon: LayoutDashboard },
  { href: "/articles", label: "Articles",   icon: Newspaper },
  { href: "/analysis", label: "Analysis",   icon: BarChart3 },
  { href: "/stocks",   label: "Stocks",     icon: TrendingUp },
  { href: "/stream",   label: "Live Feed",  icon: Radio },
];

export default function Sidebar() {
  const path = usePathname();

  return (
    <aside className="flex h-screen w-56 flex-col border-r border-line bg-surface">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 py-5">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent">
          <Zap className="h-4 w-4 text-white" />
        </div>
        <span className="text-sm font-semibold tracking-tight text-primary">MarketPulse</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-0.5 px-2 py-2">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? path === "/" : path.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-accent/10 text-accent"
                  : "text-dim hover:bg-raised hover:text-secondary"
              )}
            >
              <Icon className="h-4 w-4 flex-shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-line px-4 py-3">
        <p className="text-2xs text-muted">MarketPulse · open source</p>
      </div>
    </aside>
  );
}
