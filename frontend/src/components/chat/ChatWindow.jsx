import { useRef, useEffect } from 'react';
import useChatStore from '../../store/chatStore';
import MessageBubble from './MessageBubble.jsx';
import InputBar from './InputBar.jsx';
import ChatMenu from './ChatMenu.jsx';
import LoadingAnimation from '../common/LoadingAnimation';
import { Calculator, Sigma, Triangle, TrendingUp, FileText, X } from 'lucide-react';

const exampleQueries = [
  { text: 'Solve x² - 5x + 6 = 0', icon: Calculator },
  { text: 'Find the derivative of sin(x) * eˣ', icon: Sigma },
  { text: 'Integrate x² from 0 to 3', icon: TrendingUp },
  { text: 'Area of triangle with vertices (0,0), (4,0), (0,3)', icon: Triangle },
];

const ChatWindow = () => {
  const { messages, isLoading, sendQuery, pdfContext, pdfFileName, clearPdf } = useChatStore();
  const messagesEndRef = useRef(null);

  // Scroll to bottom whenever messages change or loading state changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, isLoading]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: '1 1 0%', minHeight: 0 }}>
      {/* Chat toolbar — visible when conversation has started */}
      {messages.length > 0 && (
        <div className="flex items-center justify-end px-6 py-1.5 border-b border-slate-800/60">
          <ChatMenu />
        </div>
      )}

      {/* PDF context banner */}
      {pdfContext && pdfFileName && (
        <div className="pdf-context-banner flex items-center gap-2 mx-6 mt-2 px-4 py-2 rounded-xl bg-blue-600/15 border border-blue-500/30 text-blue-300 text-sm">
          <FileText size={16} className="shrink-0" />
          <span className="flex-1 truncate">
            PDF loaded: <strong>{pdfFileName}</strong> — ask questions below
          </span>
          <button
            onClick={() => clearPdf()}
            className="p-1 hover:bg-blue-500/20 rounded-lg transition-colors"
            title="Close PDF session"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Messages area */}
      <div
        style={{ flex: '1 1 0%', minHeight: 0, overflowY: 'auto' }}
        className="px-6 py-4 space-y-4"
      >
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center px-4">
            <div className="w-16 h-16 bg-blue-600/20 rounded-2xl flex items-center justify-center mb-4">
              <Calculator size={32} className="text-blue-400" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-1">
              Welcome to Solvera
            </h2>
            <p className="text-slate-400 mb-6 max-w-md">
              Your AI-powered math assistant. Ask any math question or upload a
              photo of a handwritten problem.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-lg w-full">
              {exampleQueries.map(({ text, icon: Icon }) => (
                <button
                  key={text}
                  onClick={() => sendQuery(text)}
                  disabled={isLoading}
                  className="flex items-center gap-3 bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-slate-600 p-3 rounded-xl text-left text-sm text-slate-300 hover:text-white transition-all group"
                >
                  <Icon
                    size={16}
                    className="text-slate-500 group-hover:text-blue-400 shrink-0"
                  />
                  {text}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
        {isLoading && <LoadingAnimation />}
        {/* Scroll anchor — always at the bottom */}
        <div ref={messagesEndRef} />
      </div>

      {/* Input bar */}
      <InputBar />
    </div>
  );
};

export default ChatWindow;
