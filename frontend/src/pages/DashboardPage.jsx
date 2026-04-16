import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Calculator,
  GraduationCap,
  BookOpen,
  ArrowRight,
  User,
  LogOut,
  Mail,
} from 'lucide-react';
import useAuthStore from '../store/authStore';

const DashboardPage = () => {
  const navigate = useNavigate();
  const { user, fetchUser, logout } = useAuthStore();
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const profileRef = useRef(null);

  useEffect(() => {
    if (!user) fetchUser();
  }, [user, fetchUser]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (profileRef.current && !profileRef.current.contains(e.target)) {
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

  const modes = [
    {
      id: 'math-solver',
      title: 'Math Query Solver',
      icon: Calculator,
      gradient: 'from-blue-600 to-cyan-500',
      iconBg: 'bg-blue-600/20',
      iconColor: 'text-blue-400',
      borderHover: 'hover:border-blue-500/50',
      route: '/chat',
    },
    {
      id: 'jee-exam',
      title: 'JEE Exam Mode',
      icon: GraduationCap,
      gradient: 'from-amber-500 to-orange-500',
      iconBg: 'bg-amber-600/20',
      iconColor: 'text-amber-400',
      borderHover: 'hover:border-amber-500/50',
      route: '/jee-exam',
    },
    {
      id: 'concept-learning',
      title: 'Concept Learning Mode',
      icon: BookOpen,
      gradient: 'from-purple-500 to-pink-500',
      iconBg: 'bg-purple-600/20',
      iconColor: 'text-purple-400',
      borderHover: 'hover:border-purple-500/50',
      route: '/concept-learning',
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* ── Top navigation ─────────────────────────────── */}
      <nav className="fixed top-0 inset-x-0 z-50 bg-slate-950/80 backdrop-blur-md border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 bg-blue-600/20 rounded-lg flex items-center justify-center">
              <span className="text-blue-400 font-bold text-lg">S</span>
            </div>
            <h1 className="text-xl font-bold text-white">
              <span className="text-blue-400">Solv</span>era
            </h1>
          </div>

          {/* Profile icon dropdown */}
          <div className="relative" ref={profileRef}>
            <button
              onClick={() => setIsProfileOpen(!isProfileOpen)}
              className="w-10 h-10 bg-gradient-to-br from-blue-400 to-blue-600 rounded-full flex items-center justify-center hover:ring-2 hover:ring-blue-400/50 transition-all"
            >
              <User size={20} className="text-white" />
            </button>

            {isProfileOpen && (
              <div className="absolute right-0 mt-2 w-56 bg-slate-800 rounded-xl border border-slate-700 shadow-2xl overflow-hidden animate-in fade-in slide-in-from-top-1">
                <div className="px-4 py-3 border-b border-slate-700">
                  <div className="flex items-center gap-2 mb-1">
                    <User size={14} className="text-slate-400" />
                    <p className="text-sm font-medium text-white">{user?.username || 'Student'}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Mail size={14} className="text-slate-400" />
                    <p className="text-xs text-slate-400">{user?.email || 'No email'}</p>
                  </div>
                </div>
                <div className="p-1">
                  <button
                    onClick={handleLogout}
                    className="w-full text-left px-3 py-2.5 text-sm text-red-400 hover:bg-red-900/30 rounded-lg transition-colors flex items-center gap-2"
                  >
                    <LogOut size={16} />
                    Sign Out
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </nav>

      {/* ── Main content ───────────────────────────────── */}
      <main className="pt-24 pb-20 px-6">
        <div className="max-w-5xl mx-auto">
          {/* Greeting */}
          <div className="mb-10">
            <h2 className="text-2xl md:text-3xl font-bold text-white mb-1">
              Welcome, {user?.username || 'Student'}
            </h2>
            <p className="text-slate-400 text-sm">Select a module to get started</p>
          </div>

          {/* ── Mode cards ───────────────────────────────── */}
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {modes.map((mode) => {
              const Icon = mode.icon;
              return (
                <button
                  key={mode.id}
                  onClick={() => mode.route && navigate(mode.route)}
                  className={`group relative rounded-2xl border border-slate-700/60 ${mode.borderHover} bg-slate-900/50 backdrop-blur-sm transition-all duration-300 hover:shadow-xl hover:shadow-slate-900/50 hover:-translate-y-1 overflow-hidden text-left ${
                    mode.route ? 'cursor-pointer' : 'cursor-pointer'
                  }`}
                >
                  {/* Gradient top accent */}
                  <div className={`h-1 bg-gradient-to-r ${mode.gradient}`} />

                  <div className="p-6">
                    <div className={`w-12 h-12 ${mode.iconBg} rounded-xl flex items-center justify-center mb-4`}>
                      <Icon size={24} className={mode.iconColor} />
                    </div>

                    <h3 className="text-lg font-semibold text-white mb-2">{mode.title}</h3>

                    <div className="flex items-center gap-1.5 text-sm text-slate-400 group-hover:text-blue-400 transition-colors">
                      <span>Open</span>
                      <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </main>
    </div>
  );
};

export default DashboardPage;
