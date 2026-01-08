'use client';

import styles from './Search.module.css';

interface SearchProps {
  placeholder?: string;
}

export function Search({ placeholder = 'Search...' }: SearchProps) {
  return (
    <div className={styles.wrapper}>
      <input
        type="text"
        className={styles.input}
        placeholder={placeholder}
      />
      <span className={styles.shortcut}>⌘K</span>
    </div>
  );
}
