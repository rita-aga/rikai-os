import { ReactNode } from 'react';
import styles from './Card.module.css';

interface CardProps {
  children: ReactNode;
  variant?: 'default' | 'interactive';
  className?: string;
}

export function Card({ children, variant = 'default', className }: CardProps) {
  return (
    <div className={`${styles.card} ${styles[variant]} ${className || ''}`}>
      {children}
    </div>
  );
}
