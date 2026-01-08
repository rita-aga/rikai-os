'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

interface LogoProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'icon' | 'full';
  animated?: boolean;
}

/**
 * RikaiOS Logo - 理解 (rikai) meaning "understanding"
 * Calligraphy-style brush stroke design
 */
export function Logo({
  className,
  size = 'md',
  variant = 'icon',
  animated = false,
}: LogoProps) {
  const sizes = {
    sm: 'w-6 h-6',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  };

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <svg
        viewBox="0 0 40 40"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={cn(sizes[size], 'flex-shrink-0')}
      >
        {/* Background circle with subtle gradient */}
        <circle
          cx="20"
          cy="20"
          r="19"
          className="fill-accent"
        />

        {/* 理 kanji - simplified calligraphy style */}
        <g className="stroke-white" strokeLinecap="round" strokeLinejoin="round">
          {/* Top horizontal line */}
          <path
            d="M11 12 L29 12"
            strokeWidth="2.5"
            className={cn(animated && 'animate-stroke-draw')}
            style={animated ? { strokeDasharray: 18, strokeDashoffset: 18, animationDelay: '0s' } : undefined}
          />

          {/* Left vertical line */}
          <path
            d="M14 12 L14 28"
            strokeWidth="2.5"
            className={cn(animated && 'animate-stroke-draw')}
            style={animated ? { strokeDasharray: 16, strokeDashoffset: 16, animationDelay: '0.1s' } : undefined}
          />

          {/* Right vertical line */}
          <path
            d="M26 12 L26 28"
            strokeWidth="2.5"
            className={cn(animated && 'animate-stroke-draw')}
            style={animated ? { strokeDasharray: 16, strokeDashoffset: 16, animationDelay: '0.2s' } : undefined}
          />

          {/* Middle horizontal line */}
          <path
            d="M14 20 L26 20"
            strokeWidth="2.5"
            className={cn(animated && 'animate-stroke-draw')}
            style={animated ? { strokeDasharray: 12, strokeDashoffset: 12, animationDelay: '0.3s' } : undefined}
          />

          {/* Bottom horizontal line */}
          <path
            d="M11 28 L29 28"
            strokeWidth="2.5"
            className={cn(animated && 'animate-stroke-draw')}
            style={animated ? { strokeDasharray: 18, strokeDashoffset: 18, animationDelay: '0.4s' } : undefined}
          />

          {/* Center dot/mark - essence */}
          <circle
            cx="20"
            cy="20"
            r="2"
            className={cn('fill-white', animated && 'animate-fade-in')}
            style={animated ? { opacity: 0, animationDelay: '0.5s', animationFillMode: 'forwards' } : undefined}
          />
        </g>
      </svg>

      {variant === 'full' && (
        <span className="font-semibold text-lg tracking-tight">
          RikaiOS
        </span>
      )}
    </div>
  );
}

/**
 * Minimal abstract logo mark - for very small spaces
 */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn('w-6 h-6', className)}
    >
      <circle cx="12" cy="12" r="11" className="fill-accent" />
      <path
        d="M7 8h10M7 12h10M7 16h10M9 8v8M15 8v8"
        className="stroke-white"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}
