import Chat from '../Chat';
import styles from './style.module.less';

const TOKEN = 'eyJhbGciOiJIUzUxMiJ9.eyJ0b2tlbl91c2VyX2VtYWlsIjoiIiwidG9rZW5fdXNlcl9pZCI6MTksInRva2VuX3VzZXJfZGlzcGxheV9uYW1lIjoiYXBpX2FkbWluIiwidG9rZW5fY3JlYXRlX3RpbWUiOjE3ODQxOTIxMjYwMTUsInRva2VuX2lzX2FkbWluIjoxLCJ0b2tlbl91c2VyX25hbWUiOiJhcGlfYWRtaW4iLCJ0b2tlbl91c2VyX3Bhc3N3b3JkIjoiYzNWd1pYSnpiMjVwWTBCaWFXTnZiV0ZqZkMrelYvWTlMSCtQRFROelF5dz0iLCJzdWIiOiJhcGlfYWRtaW4iLCJleHAiOjE3ODQyNjQxMjZ9.SAJ7DgHzEeJr-6xdznHcr5DreVZOwm_dFI3MOgj4K4EUamu3jcrWt_nFOYcX8WNhVpdsKgzB7afGxcuuYX0E6A';

type Props = {};

const ChatDemo: React.FC<Props> = () => {
  return (
    <div className={styles.chatDemo}>
      <Chat token={TOKEN} isDeveloper />
    </div>
  );
};

export default ChatDemo;
