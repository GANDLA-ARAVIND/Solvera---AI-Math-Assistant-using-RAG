import { useState, useRef, useEffect } from 'react';
import { MoreVertical, Download } from 'lucide-react';
import useChatStore from '../../store/chatStore';
import downloadChatPdf from '../../utils/downloadChatPdf';

const ChatMenu = () => {
  const [open, setOpen] = useState(false);
  const menuRef = useRef(null);
  const messages = useChatStore((s) => s.messages);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleDownload = () => {
    downloadChatPdf(messages);
    setOpen(false);
  };

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        aria-label="Chat options"
      >
        <MoreVertical size={20} />
      </button>

      {open && (
        <div className="absolute right-0 mt-1 w-52 bg-slate-800 border border-slate-700 rounded-xl shadow-xl overflow-hidden z-50 animate-in fade-in slide-in-from-top-2">
          <button
            onClick={handleDownload}
            disabled={messages.length === 0}
            className="w-full flex items-center gap-3 px-4 py-3 text-sm text-slate-200 hover:bg-slate-700 hover:text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Download size={16} className="text-blue-400" />
            Download Chat as PDF
          </button>
        </div>
      )}
    </div>
  );
};

export default ChatMenu;
