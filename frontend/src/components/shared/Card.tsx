import { cn } from "@/lib/utils";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  as?: "div" | "section" | "article";
}

export default function Card({ children, className, as: Tag = "div" }: CardProps) {
  return (
    <Tag className={cn("rounded-xl border border-line bg-surface p-4", className)}>
      {children}
    </Tag>
  );
}

export function CardHeader({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("mb-3 flex items-center justify-between", className)}>{children}</div>;
}

export function CardTitle({ children, className }: { children: React.ReactNode; className?: string }) {
  return <h3 className={cn("text-sm font-semibold text-primary", className)}>{children}</h3>;
}
