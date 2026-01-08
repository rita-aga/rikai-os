'use client';

import { useState, useEffect } from 'react';
import { Sidebar } from './Sidebar';
import { BottomNav } from './BottomNav';
import { Header } from './Header';

interface AppShellProps {
  children: React.ReactNode;
  title?: string;
  showSearch?: boolean;
}

export function AppShell({ children, title, showSearch = true }: AppShellProps) {
  const [searchOpen, setSearchOpen] = useState(false);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');

  // Initialize theme from localStorage or system preference
  useEffect(() => {
    const stored = localStorage.getItem('theme');
    if (stored === 'dark' || stored === 'light') {
      setTheme(stored);
      document.documentElement.classList.toggle('dark', stored === 'dark');
    } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      setTheme('dark');
      document.documentElement.classList.add('dark');
    }
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme);
    document.documentElement.classList.toggle('dark', newTheme === 'dark');
  };

  const handleSearchClick = () => {
    setSearchOpen(true);
    // Will integrate with command palette later
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Desktop Sidebar - Fixed position */}
      <Sidebar theme={theme} onThemeToggle={toggleTheme} />

      {/* Main Content Area - Offset by sidebar width on desktop */}
      <div className="md:pl-14 min-h-screen flex flex-col">
        {/* Header */}
        <Header
          title={title}
          showSearch={showSearch}
          onSearchClick={handleSearchClick}
          theme={theme}
          onThemeToggle={toggleTheme}
        />

        {/* Main Content */}
        <main className="flex-1 overflow-auto px-4 py-6 md:px-8 pb-24 md:pb-6">
          {children}
        </main>
      </div>

      {/* Mobile Bottom Navigation */}
      <BottomNav />
    </div>
  );
}
