import styles from './ConstellationCard.module.scss';

export interface ConstellationCardProps {
  id: string;
  name: string;
  description: string;
  nodeCount: number;
  tags: string[];
  onClick?: () => void;
}

export default function ConstellationCard({
  name,
  description,
  nodeCount,
  tags,
  onClick,
}: ConstellationCardProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick?.();
    }
  };

  return (
    <div className={styles.card} onClick={onClick} onKeyDown={handleKeyDown} role="button" tabIndex={0}>
      <div className={styles.header}>
        <div className={styles.icon}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <circle cx="12" cy="12" r="3" />
            <circle cx="19" cy="5" r="2" />
            <circle cx="5" cy="19" r="2" />
            <circle cx="5" cy="5" r="2" />
            <circle cx="19" cy="19" r="2" />
            <line x1="14.5" y1="9.5" x2="17.5" y2="6.5" />
            <line x1="9.5" y1="14.5" x2="6.5" y2="17.5" />
            <line x1="6.5" y1="6.5" x2="9.5" y2="9.5" />
            <line x1="14.5" y1="14.5" x2="17.5" y2="17.5" />
          </svg>
        </div>
        <div className={styles.nodeCount}>
          <span className={styles.nodeNumber}>{nodeCount}</span>
          <span className={styles.nodeLabel}>nodes</span>
        </div>
      </div>

      <h3 className={styles.name}>{name}</h3>
      <p className={styles.description}>{description}</p>

      {tags.length > 0 && (
        <div className={styles.tags}>
          {tags.slice(0, 3).map((tag) => (
            <span key={tag} className={styles.tag}>
              {tag}
            </span>
          ))}
          {tags.length > 3 && (
            <span className={styles.moreTags}>+{tags.length - 3}</span>
          )}
        </div>
      )}
    </div>
  );
}
