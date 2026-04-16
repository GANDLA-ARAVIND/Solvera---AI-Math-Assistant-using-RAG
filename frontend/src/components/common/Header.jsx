import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, LogOut, History, Plus, LayoutDashboard, ArrowLeft } from 'lucide-react';
import useAuthStore from '../../store/authStore';
import useChatStore from '../../store/chatStore';
import ThemeToggle from './ThemeToggle';

const Header = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const { clearChat } = useChatStore();
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const profileRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (profileRef.current && !profileRef.current.contains(event.target)) {
        setIsProfileOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const handleNewChat = () => {
    clearChat();
    navigate('/chat');
    setIsProfileOpen(false);
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-40 bg-slate-950/80 backdrop-blur-md border-b border-slate-800">
      <div className="max-w-full px-6 h-16 flex items-center justify-between">
        {/* Logo/Brand - Left side */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(-1)}
            className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
            title="Go back"
          >
            <ArrowLeft size={18} />
          </button>
          <div className="w-9 h-9 bg-blue-600/20 rounded-lg flex items-center justify-center">
            <span className="text-blue-400 font-bold text-lg">S</span>
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Solvera</h1>
          </div>
          <button
            onClick={() => navigate('/dashboard')}
            className="ml-4 px-3 py-2 flex items-center gap-2 text-sm font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
          >
            <LayoutDashboard size={16} />
            Dashboard
          </button>
          <button
            onClick={handleNewChat}
            className="px-3 py-2 flex items-center gap-2 text-sm font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
          >
            <Plus size={16} />
            New Chat
          </button>
        </div>

        {/* Profile Section - Right side */}
        <div className="flex items-center gap-4">
          <ThemeToggle />
          <div className="relative" ref={profileRef}>
            <button
              onClick={() => setIsProfileOpen(!isProfileOpen)}
              className="flex items-center gap-3 px-4 py-2 rounded-lg hover:bg-slate-800 transition-colors"
            >
              <div className="text-right">
                <p className="text-sm font-medium text-white">{user?.username || 'User'}</p>
                <p className="text-xs text-slate-500">{user?.email}</p>
              </div>
              <div className="w-9 h-9 bg-gradient-to-br from-blue-400 to-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
                <User size={18} className="text-white" />
              </div>
            </button>

            {/* Dropdown Menu */}
            {isProfileOpen && (
              <div className="absolute right-0 mt-2 w-48 bg-slate-800 rounded-lg border border-slate-700 shadow-lg overflow-hidden">
                <div className="px-4 py-3 border-b border-slate-700">
                  <p className="text-sm font-medium text-white">{user?.username}</p>
                  <p className="text-xs text-slate-400">{user?.email}</p>
                </div>
                
                <button
                  onClick={() => {
                    navigate('/history');
                    setIsProfileOpen(false);
                  }}
                  className="w-full text-left px-4 py-2.5 text-sm text-slate-300 hover:bg-slate-700 hover:text-white transition-colors flex items-center gap-2"
                >
                  <History size={16} />
                  Chat History
                </button>
                
                <div className="border-t border-slate-700">
                  <button
                    onClick={handleLogout}
                    className="w-full text-left px-4 py-2.5 text-sm text-red-400 hover:bg-red-900/30 transition-colors flex items-center gap-2"
                  >
                    <LogOut size={16} />
                    Sign Out
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
