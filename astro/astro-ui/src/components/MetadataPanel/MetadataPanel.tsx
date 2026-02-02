import styles from './MetadataPanel.module.scss';

export interface MetadataPanelProps {
  metadata: Record<string, unknown>;
  title?: string;
}

function renderValue(value: unknown, depth = 0): React.ReactNode {
  if (value === null || value === undefined) {
    return <span className={styles.null}>null</span>;
  }

  if (typeof value === 'boolean') {
    return <span className={styles.boolean}>{value ? 'true' : 'false'}</span>;
  }

  if (typeof value === 'number') {
    return <span className={styles.number}>{value}</span>;
  }

  if (typeof value === 'string') {
    return <span className={styles.string}>{value}</span>;
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return <span className={styles.empty}>[]</span>;
    }
    return (
      <ul className={styles.array}>
        {value.map((item, index) => (
          <li key={index}>{renderValue(item, depth + 1)}</li>
        ))}
      </ul>
    );
  }

  if (typeof value === 'object') {
    const entries = Object.entries(value);
    if (entries.length === 0) {
      return <span className={styles.empty}>{'{}'}</span>;
    }
    return (
      <dl className={styles.nested}>
        {entries.map(([key, val]) => (
          <div key={key} className={styles.nestedItem}>
            <dt className={styles.nestedKey}>{key}</dt>
            <dd className={styles.nestedValue}>{renderValue(val, depth + 1)}</dd>
          </div>
        ))}
      </dl>
    );
  }

  return <span>{String(value)}</span>;
}

export default function MetadataPanel({ metadata, title = 'Metadata' }: MetadataPanelProps) {
  const entries = Object.entries(metadata);

  if (entries.length === 0) {
    return (
      <div className={styles.panel}>
        <h4 className={styles.title}>{title}</h4>
        <p className={styles.emptyMessage}>No metadata</p>
      </div>
    );
  }

  return (
    <div className={styles.panel}>
      <h4 className={styles.title}>{title}</h4>
      <dl className={styles.list}>
        {entries.map(([key, value]) => (
          <div key={key} className={styles.item}>
            <dt className={styles.key}>{key}</dt>
            <dd className={styles.value}>{renderValue(value)}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
