'use client';

import { cn, getStatusBadgeClass } from '@/lib/utils';

interface StatusBadgeProps {
  status: string;
  label?: string;
}

export function StatusBadge({ status, label }: StatusBadgeProps) {
  const displayLabel = label || status.charAt(0).toUpperCase() + status.slice(1);

  return (
    <span className={cn('badge', getStatusBadgeClass(status))}>
      {displayLabel}
    </span>
  );
}
