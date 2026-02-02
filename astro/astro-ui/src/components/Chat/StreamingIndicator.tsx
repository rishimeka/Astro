import styles from './Chat.module.scss';

export default function StreamingIndicator() {
  return (
    <div className={styles.streamingIndicator} aria-label="Assistant is typing">
      <div className={styles.dot} />
      <div className={styles.dot} />
      <div className={styles.dot} />
    </div>
  );
}
