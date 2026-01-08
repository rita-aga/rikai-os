'use client';

import { Search, Command, Sun, Moon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Logo } from '@/components/brand/Logo';

interface HeaderProps {
  title?: string;
  showSearch?: boolean;
  onSearchClick?: () => void;
  theme?: 'light' | 'dark';
  onThemeToggle?: () => void;
}

export function Header({
  title,
  showSearch = true,
  onSearchClick,
  theme = 'light',
  onThemeToggle,
}: HeaderProps) {
  return (
    <header className="h-14 border-b border-border bg-surface/80 backdrop-blur-sm sticky top-0 z-30">
      <div className="h-full flex items-center justify-between px-4 md:px-6">
        {/* Mobile: Logo + Title */}
        <div className="md:hidden flex items-center gap-3">
          <Logo size="sm" />
          {title && <h1 className="text-lg font-semibold">{title}</h1>}
        </div>

        {/* Desktop: Search bar - centered */}
        {showSearch && (
          <div className="hidden md:flex flex-1 justify-center max-w-xl mx-auto">
            <Button
              variant="secondary"
              onClick={onSearchClick}
              className="w-full justify-start h-9 px-4"
            >
              <Search className="w-4 h-4 mr-2 text-text-tertiary" />
              <span className="flex-1 text-left text-text-tertiary">
                Search your context...
              </span>
              <kbd className="hidden lg:inline-flex h-5 items-center gap-1 rounded border border-border bg-background px-1.5 font-mono text-xs text-text-tertiary">
                <Command className="w-3 h-3" />K
              </kbd>
            </Button>
          </div>
        )}

        {/* Right side */}
        <div className="flex items-center gap-2">
          {/* Mobile: Search + Theme */}
          <div className="md:hidden flex items-center gap-1">
            {showSearch && (
              <Button variant="ghost" size="icon-sm" onClick={onSearchClick}>
                <Search className="w-5 h-5" />
              </Button>
            )}
            <Button variant="ghost" size="icon-sm" onClick={onThemeToggle}>
              {theme === 'light' ? (
                <Moon className="w-5 h-5" />
              ) : (
                <Sun className="w-5 h-5" />
              )}
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
}
