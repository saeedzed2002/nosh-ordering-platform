import { type ReactNode } from "react";

export type StatusTone = "available" | "preparing" | "ready" | "unavailable";

type StatusBadgeProps = {
  children: ReactNode;
  tone: StatusTone;
};

export function StatusBadge({ children, tone }: StatusBadgeProps) {
  return (
    <span className="nosh-status-badge" data-tone={tone}>
      <span aria-hidden="true" className="nosh-status-dot" />
      {children}
    </span>
  );
}
