'use client';

import { ReactNode } from 'react';
import styles from './IconButton.module.css';

interface IconButtonProps {
  icon: ReactNode;
  onClick?: () => void;
  label?: string;
}

export function IconButton({ icon, onClick, label }: IconButtonProps) {
  return (
    <button
      className={styles.button}
      onClick={onClick}
      aria-label={label}
      type="button"
    >
      {icon}
    </button>
  );
}
