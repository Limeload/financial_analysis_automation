import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  className?: string;
}

export default function EmptyState({ icon, title, description, className }: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center gap-2 py-16 text-center", className)}>
      {icon && <div className="mb-2 text-muted">{icon}</div>}
      <p className="text-sm font-medium text-secondary">{title}</p>
      {description && <p className="max-w-xs text-xs text-muted">{description}</p>}
    </div>
  );
}
