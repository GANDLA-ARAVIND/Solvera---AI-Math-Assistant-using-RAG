import { useEffect } from 'react';
import ChatWindow from '../components/chat/ChatWindow';
import Header from '../components/common/Header';
import useAuthStore from '../store/authStore';

const ChatPage = () => {
  const { fetchUser, user } = useAuthStore();

  useEffect(() => {
    if (!user) {
      fetchUser();
    }
  }, [user, fetchUser]);

  return (
    <div className="bg-slate-950" style={{ position: 'fixed', inset: 0 }}>
      <Header />
      {/* Absolute-positioned area below header — guaranteed height */}
      <div
        style={{
          position: 'absolute',
          top: '4rem',
          left: 0,
          right: 0,
          bottom: 0,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <ChatWindow />
      </div>
    </div>
  );
};

export default ChatPage;
