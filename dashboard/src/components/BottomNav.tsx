'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, Layers, Network } from 'lucide-react';
import styles from './BottomNav.module.css';

const navItems = [
  { href: '/', label: 'Home', icon: Home },
  { href: '/entities', label: 'Entities', icon: Layers },
  { href: '/graph', label: 'Graph', icon: Network },
];

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className={styles.nav}>
      {navItems.map((item) => {
        const Icon = item.icon;
        const isActive = pathname === item.href;

        return (
          <Link
            key={item.href}
            href={item.href}
            className={`${styles.navItem} ${isActive ? styles.active : ''}`}
          >
            <Icon />
            <span className={styles.label}>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
