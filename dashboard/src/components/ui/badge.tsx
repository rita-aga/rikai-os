import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-accent text-white',
        secondary: 'border-transparent bg-accent-subtle text-accent',
        outline: 'border-border text-text-secondary',
        destructive: 'border-transparent bg-destructive text-white',
        // Entity type badges
        self: 'border-transparent bg-entity-self/10 text-entity-self',
        project: 'border-transparent bg-entity-project/10 text-entity-project',
        person: 'border-transparent bg-entity-person/10 text-entity-person',
        topic: 'border-transparent bg-entity-topic/10 text-entity-topic',
        note: 'border-transparent bg-entity-note/10 text-entity-note',
        task: 'border-transparent bg-entity-task/10 text-entity-task',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
