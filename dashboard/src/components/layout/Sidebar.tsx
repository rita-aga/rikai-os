'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  Home,
  Network,
  Layers,
  FileText,
  Users,
  Settings,
  Sun,
  Moon,
} from 'lucide-react';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip';
import { Logo } from '@/components/brand/Logo';

interface SidebarProps {
  className?: string;
  theme?: 'light' | 'dark';
  onThemeToggle?: () => void;
}

const navItems = [
  { href: '/', label: 'Home', icon: Home },
  { href: '/graph', label: 'Graph', icon: Network },
  { href: '/entities', label: 'Entities', icon: Layers },
  { href: '/documents', label: 'Documents', icon: FileText },
  { href: '/hiroba', label: 'Hiroba', icon: Users },
];

const bottomNavItems = [
  { href: '/settings', label: 'Settings', icon: Settings },
];

export function Sidebar({ className, theme = 'light', onThemeToggle }: SidebarProps) {
  const pathname = usePathname();

  return (
    <TooltipProvider delayDuration={0}>
      <aside
        className={cn(
          'hidden md:flex flex-col w-14 bg-surface border-r border-border',
          'fixed left-0 top-0 h-screen z-40',
          className
        )}
      >
        {/* Logo */}
        <div className="h-14 flex items-center justify-center border-b border-border">
          <Tooltip>
            <TooltipTrigger asChild>
              <Link href="/" className="p-2 rounded-lg hover:bg-accent-subtle transition-colors">
                <Logo size="sm" />
              </Link>
            </TooltipTrigger>
            <TooltipContent side="right">RikaiOS</TooltipContent>
          </Tooltip>
        </div>

        {/* Navigation */}
        <nav className="flex-1 flex flex-col items-center gap-1 py-3">
          {navItems.map((item) => {
            const isActive =
              pathname === item.href ||
              (item.href !== '/' && pathname.startsWith(item.href));
            const Icon = item.icon;

            return (
              <Tooltip key={item.href}>
                <TooltipTrigger asChild>
                  <Link
                    href={item.href}
                    className={cn(
                      'flex items-center justify-center w-10 h-10 rounded-lg',
                      'transition-all duration-150',
                      isActive
                        ? 'bg-accent text-white shadow-subtle'
                        : 'text-text-secondary hover:text-text-primary hover:bg-accent-subtle'
                    )}
                  >
                    <Icon className="w-5 h-5" />
                  </Link>
                </TooltipTrigger>
                <TooltipContent side="right">{item.label}</TooltipContent>
              </Tooltip>
            );
          })}
        </nav>

        {/* Bottom section */}
        <div className="flex flex-col items-center gap-1 py-3 border-t border-border">
          {bottomNavItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;

            return (
              <Tooltip key={item.href}>
                <TooltipTrigger asChild>
                  <Link
                    href={item.href}
                    className={cn(
                      'flex items-center justify-center w-10 h-10 rounded-lg',
                      'transition-all duration-150',
                      isActive
                        ? 'bg-accent text-white shadow-subtle'
                        : 'text-text-secondary hover:text-text-primary hover:bg-accent-subtle'
                    )}
                  >
                    <Icon className="w-5 h-5" />
                  </Link>
                </TooltipTrigger>
                <TooltipContent side="right">{item.label}</TooltipContent>
              </Tooltip>
            );
          })}

          {/* Theme toggle */}
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                onClick={onThemeToggle}
                className={cn(
                  'flex items-center justify-center w-10 h-10 rounded-lg',
                  'transition-all duration-150',
                  'text-text-secondary hover:text-text-primary hover:bg-accent-subtle'
                )}
              >
                {theme === 'light' ? (
                  <Moon className="w-5 h-5" />
                ) : (
                  <Sun className="w-5 h-5" />
                )}
              </button>
            </TooltipTrigger>
            <TooltipContent side="right">
              {theme === 'light' ? 'Dark mode' : 'Light mode'}
            </TooltipContent>
          </Tooltip>
        </div>
      </aside>
    </TooltipProvider>
  );
}
