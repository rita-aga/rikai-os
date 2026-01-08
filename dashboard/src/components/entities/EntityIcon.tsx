'use client';

import { cn } from '@/lib/utils';
import {
  User,
  FolderKanban,
  Users,
  Hash,
  FileText,
  CheckSquare,
} from 'lucide-react';
import type { EntityType } from '@/types';

interface EntityIconProps {
  type: EntityType;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

const iconMap = {
  self: User,
  project: FolderKanban,
  person: Users,
  topic: Hash,
  note: FileText,
  task: CheckSquare,
};

const sizeMap = {
  sm: 'w-4 h-4',
  md: 'w-5 h-5',
  lg: 'w-6 h-6',
};

export function EntityIcon({ type, className, size = 'md' }: EntityIconProps) {
  const Icon = iconMap[type];

  return (
    <Icon
      className={cn(
        sizeMap[size],
        `text-entity-${type}`,
        className
      )}
    />
  );
}
