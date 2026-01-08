'use client';

import { Search, Command } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface HeaderProps {
  title?: string;
  showSearch?: boolean;
  onSearchClick?: () => void;
}

export function Header({ title, showSearch = true, onSearchClick }: HeaderProps) {
  return (
    <header className="h-14 border-b border-border bg-card/80 backdrop-blur-sm sticky top-0 z-40">
      <div className="h-full flex items-center justify-between px-4 md:px-6">
        {/* Mobile: Title or Search */}
        <div className="md:hidden flex items-center gap-3 flex-1">
          {title ? (
            <h1 className="text-lg font-semibold">{title}</h1>
          ) : (
            <div className="text-lg font-semibold">RikaiOS</div>
          )}
        </div>

        {/* Desktop: Search bar */}
        {showSearch && (
          <div className="hidden md:flex flex-1 max-w-xl">
            <Button
              variant="outline"
              onClick={onSearchClick}
              className="w-full justify-start text-muted-foreground h-9 px-3"
            >
              <Search className="w-4 h-4 mr-2" />
              <span className="flex-1 text-left">Search your context...</span>
              <kbd className="hidden lg:inline-flex h-5 items-center gap-1 rounded border bg-muted px-1.5 font-mono text-xs">
                <Command className="w-3 h-3" />K
              </kbd>
            </Button>
          </div>
        )}

        {/* Mobile: Search icon */}
        {showSearch && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onSearchClick}
            className="md:hidden"
          >
            <Search className="w-5 h-5" />
          </Button>
        )}

        {/* Right side - can add avatar, notifications, etc. */}
        <div className="hidden md:flex items-center gap-2 ml-4">
          {/* Placeholder for future user menu */}
        </div>
      </div>
    </header>
  );
}
