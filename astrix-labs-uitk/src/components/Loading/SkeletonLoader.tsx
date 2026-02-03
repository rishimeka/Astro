import styles from './Loading.module.scss';

export interface SkeletonLoaderProps {
  width?: string;
  height?: string;
  variant?: 'text' | 'rectangular' | 'circular';
  className?: string;
}

export function SkeletonLoader({
  width = '100%',
  height = '1rem',
  variant = 'text',
  className = '',
}: SkeletonLoaderProps) {
  return (
    <div
      className={`${styles.skeleton} ${styles[variant]} ${className}`}
      style={{ width, height }}
    />
  );
}
