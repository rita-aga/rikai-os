'use client';

import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { EntityIcon } from './EntityIcon';
import type { EntityType } from '@/types';
import { entityLabels } from '@/types';

interface EntityBadgeProps {
  type: EntityType;
  showLabel?: boolean;
  className?: string;
}

const colorClasses: Record<EntityType, string> = {
  self: 'bg-entity-self/10 text-entity-self border-entity-self/20',
  project: 'bg-entity-project/10 text-entity-project border-entity-project/20',
  person: 'bg-entity-person/10 text-entity-person border-entity-person/20',
  topic: 'bg-entity-topic/10 text-entity-topic border-entity-topic/20',
  note: 'bg-entity-note/10 text-entity-note border-entity-note/20',
  task: 'bg-entity-task/10 text-entity-task border-entity-task/20',
};

export function EntityBadge({ type, showLabel = true, className }: EntityBadgeProps) {
  return (
    <Badge
      variant="outline"
      className={cn(
        'gap-1 font-medium',
        colorClasses[type],
        className
      )}
    >
      <EntityIcon type={type} size="sm" />
      {showLabel && <span>{entityLabels[type]}</span>}
    </Badge>
  );
}
