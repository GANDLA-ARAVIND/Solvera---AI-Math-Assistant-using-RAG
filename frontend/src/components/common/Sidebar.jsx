import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { MessageSquare, History, LogOut, Plus, User, Menu, X } from 'lucide-react';
import useAuthStore from '../../store/authStore';
import useChatStore from '../../store/chatStore';

const Sidebar = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuthStore();
  const { clearChat } = useChatStore();
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleNewChat = () => {
    clearChat();
    navigate('/');
    setMobileOpen(false);
  };

  const navItems = [
    { path: '/', icon: MessageSquare, label: 'Chat' },
    { path: '/history', icon: History, label: 'History' },
  ];

  const sidebarContent = (
    <>
      {/* Logo */}
      <div className="p-4 border-b border-slate-700 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">
            <span className="text-blue-400">S</span>olvera
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">AI Math Assistant</p>
        </div>
        <button
          onClick={() => setMobileOpen(false)}
          className="lg:hidden p-1 text-slate-400 hover:text-white"
        >
          <X size={20} />
        </button>
      </div>

      {/* New Chat button */}
      <div className="p-3">
        <button
          onClick={handleNewChat}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-800 hover:text-white transition-colors text-sm"
        >
          <Plus size={16} />
          New Chat
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3">
        {navItems.map(({ path, icon: Icon, label }) => (
          <button
            key={path}
            onClick={() => {
              navigate(path);
              setMobileOpen(false);
            }}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm mb-1 transition-colors ${
              location.pathname === path
                ? 'bg-blue-600/20 text-blue-400'
                : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
            }`}
          >
            <Icon size={18} />
            {label}
          </button>
        ))}
      </nav>

      {/* User section */}
      <div className="p-3 border-t border-slate-700">
        <div className="flex items-center gap-3 px-3 py-2">
          <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
            <User size={16} className="text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-white truncate">{user?.username || 'User'}</p>
            <p className="text-xs text-slate-500 truncate">{user?.email}</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-2 px-3 py-2 mt-1 rounded-lg text-slate-400 hover:bg-red-900/30 hover:text-red-400 transition-colors text-sm"
        >
          <LogOut size={16} />
          Sign Out
        </button>
      </div>
    </>
  );

  return (
    <>
      {/* Mobile menu button */}
      <button
        onClick={() => setMobileOpen(true)}
        className="lg:hidden fixed top-3 left-3 z-50 p-2 bg-slate-800 rounded-lg text-slate-300 hover:text-white border border-slate-700"
      >
        <Menu size={20} />
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Mobile sidebar */}
      <aside
        className={`lg:hidden fixed inset-y-0 left-0 z-50 w-64 bg-slate-900 border-r border-slate-700 flex flex-col transform transition-transform duration-200 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {sidebarContent}
      </aside>

      {/* Desktop sidebar */}
      <aside className="hidden lg:flex w-64 bg-slate-900 border-r border-slate-700 flex-col h-full">
        {sidebarContent}
      </aside>
    </>
  );
};

export default Sidebar;
