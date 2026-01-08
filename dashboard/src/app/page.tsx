'use client';

import styles from './page.module.css';
import { Logo } from '@/components/Logo';
import { Search } from '@/components/Search';
import { ListItem } from '@/components/ListItem';
import { IconButton } from '@/components/IconButton';
import { ThemeToggle } from '@/components/ThemeToggle';
import { BottomNav } from '@/components/BottomNav';
import { Settings } from 'lucide-react';

const recentItems = [
  { id: '1', title: 'RikaiOS Dashboard', href: '/entities/1' },
  { id: '2', title: 'Design System Ideas', href: '/entities/2' },
  { id: '3', title: 'React Patterns', href: '/entities/3' },
];

export default function Home() {
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <Logo />
        <div className={styles.actions}>
          <IconButton icon={<Settings />} label="Settings" />
          <ThemeToggle />
        </div>
      </header>

      <main className={styles.main}>
        <h1 className={styles.greeting}>Welcome back</h1>
        <p className={styles.subtitle}>What would you like to explore?</p>

        <Search placeholder="Search your context..." />

        <ul className={styles.list}>
          {recentItems.map((item) => (
            <li key={item.id}>
              <ListItem title={item.title} href={item.href} />
            </li>
          ))}
        </ul>
      </main>

      <BottomNav />
    </div>
  );
}
