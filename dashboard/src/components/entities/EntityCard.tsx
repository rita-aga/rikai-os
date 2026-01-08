'use client';

import Link from 'next/link';
import { cn } from '@/lib/utils';
import { Card, CardContent } from '@/components/ui/card';
import { EntityIcon } from './EntityIcon';
import { EntityBadge } from './EntityBadge';
import type { Entity } from '@/types';

interface EntityCardProps {
  entity: Entity;
  variant?: 'compact' | 'detailed' | 'grid';
  className?: string;
}

export function EntityCard({ entity, variant = 'compact', className }: EntityCardProps) {
  const href = entity.type === 'self'
    ? '/entities/self'
    : `/entities/${entity.type}s/${entity.id}`;

  // Format relative time
  const formatTime = (date: string) => {
    const now = new Date();
    const then = new Date(date);
    const diff = now.getTime() - then.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days}d ago`;
    return then.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  if (variant === 'compact') {
    return (
      <Link href={href} className={cn('block', className)}>
        <Card className="hover:shadow-float transition-subtle border-0 shadow-subtle">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <div
                className={cn(
                  'w-10 h-10 rounded-lg flex items-center justify-center shrink-0',
                  `bg-entity-${entity.type}/10`
                )}
              >
                <EntityIcon type={entity.type} />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-medium text-sm truncate">{entity.name}</h3>
                {entity.content && (
                  <p className="text-xs text-muted-foreground line-clamp-1 mt-0.5">
                    {entity.content}
                  </p>
                )}
                <span className="text-xs text-muted-foreground mt-1 block">
                  {formatTime(entity.updated_at)}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </Link>
    );
  }

  if (variant === 'grid') {
    return (
      <Link href={href} className={cn('block', className)}>
        <Card className="hover:shadow-float transition-subtle border-0 shadow-subtle h-full">
          <CardContent className="p-4">
            <EntityBadge type={entity.type} className="mb-3" />
            <h3 className="font-medium text-sm line-clamp-2">{entity.name}</h3>
            {entity.content && (
              <p className="text-xs text-muted-foreground line-clamp-2 mt-1">
                {entity.content}
              </p>
            )}
          </CardContent>
        </Card>
      </Link>
    );
  }

  // detailed variant
  return (
    <Link href={href} className={cn('block', className)}>
      <Card className="hover:shadow-float transition-subtle border-0 shadow-subtle">
        <CardContent className="p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3 flex-1 min-w-0">
              <div
                className={cn(
                  'w-12 h-12 rounded-lg flex items-center justify-center shrink-0',
                  `bg-entity-${entity.type}/10`
                )}
              >
                <EntityIcon type={entity.type} size="lg" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-medium truncate">{entity.name}</h3>
                {entity.content && (
                  <p className="text-sm text-muted-foreground line-clamp-2 mt-1">
                    {entity.content}
                  </p>
                )}
              </div>
            </div>
            <span className="text-xs text-muted-foreground shrink-0">
              {formatTime(entity.updated_at)}
            </span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
