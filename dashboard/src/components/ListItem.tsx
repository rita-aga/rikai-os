import Link from 'next/link';
import styles from './ListItem.module.css';

interface ListItemProps {
  title: string;
  href?: string;
}

export function ListItem({ title, href = '#' }: ListItemProps) {
  return (
    <Link href={href} className={styles.item}>
      <span className={styles.dot} />
      <span className={styles.title}>{title}</span>
    </Link>
  );
}
