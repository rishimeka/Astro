import styles from './Error.module.scss';

interface ErrorPageProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export default function ErrorPage({
  title = 'Something went wrong',
  message,
  onRetry,
}: ErrorPageProps) {
  return (
    <div className={styles.errorPage}>
      <div className={styles.errorPageContent}>
        <svg
          className={styles.errorPageIcon}
          width="64"
          height="64"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
        <h1 className={styles.errorPageTitle}>{title}</h1>
        <p className={styles.errorPageMessage}>{message}</p>
        {onRetry && (
          <button
            className="btn btn-primary btn-highlight"
            onClick={onRetry}
          >
            Try Again
          </button>
        )}
      </div>
    </div>
  );
}
