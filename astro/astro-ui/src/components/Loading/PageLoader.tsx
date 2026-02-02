import Spinner from './Spinner';
import styles from './Loading.module.scss';

interface PageLoaderProps {
  message?: string;
}

export default function PageLoader({ message }: PageLoaderProps) {
  return (
    <div className={styles.pageLoader}>
      <Spinner size="lg" />
      {message && <p className={styles.pageLoaderMessage}>{message}</p>}
    </div>
  );
}
