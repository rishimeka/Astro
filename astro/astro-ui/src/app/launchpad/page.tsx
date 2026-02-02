import Chat from '@/components/Chat';
import styles from './launchpad.module.scss';

export default function Launchpad() {
  return (
    <div className={styles.launchpadPage}>
      <Chat />
    </div>
  );
}
