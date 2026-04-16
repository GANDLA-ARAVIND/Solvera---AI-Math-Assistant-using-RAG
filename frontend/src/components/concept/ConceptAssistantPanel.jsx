import { useState, useRef, useEffect } from 'react';
import { X, Send, Loader2, Trash2, MessageCircle, BookOpen, FunctionSquare, ListOrdered, Lightbulb, Star } from 'lucide-react';
import useConceptStore from '../../store/conceptStore';
import MathRenderer from '../chat/MathRenderer';

// ── Structured section card ──────────────────────────────
const Section = ({ icon: Icon, title, color, children }) => {
  if (!children) return null;
  return (
    <div className={`mt-3 rounded-xl border ${color.border} ${color.bg} p-3`}>
      <div className={`flex items-center gap-1.5 mb-1.5 ${color.text} text-xs font-semibold uppercase tracking-wide`}>
        <Icon size={13} />
        {title}
      </div>
      <div className="text-slate-200 text-sm leading-relaxed prose prose-invert prose-sm max-w-none">
        <MathRenderer content={children} />
      </div>
    </div>
  );
};

// ── Section theme configs ────────────────────────────────
const sectionThemes = {
  concept: { icon: BookOpen, title: 'Concept', color: { border: 'border-blue-700/40', bg: 'bg-blue-900/20', text: 'text-blue-400' } },
  formula: { icon: FunctionSquare, title: 'Formula', color: { border: 'border-purple-700/40', bg: 'bg-purple-900/20', text: 'text-purple-400' } },
  steps: { icon: ListOrdered, title: 'Step-by-Step', color: { border: 'border-cyan-700/40', bg: 'bg-cyan-900/20', text: 'text-cyan-400' } },
  example: { icon: Lightbulb, title: 'Example', color: { border: 'border-amber-700/40', bg: 'bg-amber-900/20', text: 'text-amber-400' } },
  takeaway: { icon: Star, title: 'Key Takeaway', color: { border: 'border-emerald-700/40', bg: 'bg-emerald-900/20', text: 'text-emerald-400' } },
};

// ── Structured assistant message ─────────────────────────
const StructuredMessage = ({ data }) => {
  if (!data) return null;

  const hasStructure = data.formula || data.steps || data.example || data.key_takeaway;

  // If no structured fields came back, render the answer as prose
  if (!hasStructure) {
    return (
      <div className="prose prose-invert prose-sm max-w-none">
        <MathRenderer content={data.answer || ''} />
      </div>
    );
  }

  return (
    <div>
      {/* Concept / main answer */}
      {data.answer && (
        <Section {...sectionThemes.concept}>{data.answer}</Section>
      )}

      {/* Formula */}
      {data.formula && (
        <Section {...sectionThemes.formula}>{data.formula}</Section>
      )}

      {/* Step-by-Step */}
      {data.steps && (
        <Section {...sectionThemes.steps}>{data.steps}</Section>
      )}

      {/* Worked Example */}
      {data.example && (
        <Section {...sectionThemes.example}>{data.example}</Section>
      )}

      {/* Key Takeaway */}
      {data.key_takeaway && (
        <Section {...sectionThemes.takeaway}>{data.key_takeaway}</Section>
      )}
    </div>
  );
};

const ConceptAssistantPanel = () => {
  const {
    assistantOpen,
    closeAssistant,
    assistantMessages,
    assistantLoading,
    sendAssistantMessage,
    clearAssistantMessages,
  } = useConceptStore();
  const [input, setInput] = useState('');
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [assistantMessages, assistantLoading]);

  // Focus input when panel opens
  useEffect(() => {
    if (assistantOpen) inputRef.current?.focus();
  }, [assistantOpen]);

  const handleSend = (e) => {
    e.preventDefault();
    const q = input.trim();
    if (!q || assistantLoading) return;
    setInput('');
    sendAssistantMessage(q);
  };

  if (!assistantOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-[60] w-full sm:w-[440px] flex flex-col bg-slate-900 border-l border-slate-700/60 shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700/60 bg-slate-950/80">
        <div className="flex items-center gap-2">
          <MessageCircle size={18} className="text-blue-400" />
          <h3 className="text-sm font-semibold text-white">Concept Assistant</h3>
        </div>
        <div className="flex items-center gap-1">
          {assistantMessages.length > 0 && (
            <button
              onClick={clearAssistantMessages}
              title="Clear chat"
              className="p-1.5 text-slate-500 hover:text-red-400 transition-colors rounded-lg hover:bg-slate-800"
            >
              <Trash2 size={15} />
            </button>
          )}
          <button
            onClick={closeAssistant}
            className="p-1.5 text-slate-500 hover:text-white transition-colors rounded-lg hover:bg-slate-800"
          >
            <X size={18} />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {assistantMessages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <MessageCircle size={36} className="text-slate-600 mb-3" />
            <p className="text-slate-400 text-sm font-medium mb-1">Ask me anything about math</p>
            <p className="text-slate-500 text-xs max-w-[280px]">
              I'll give you a structured explanation with concept,
              formula, steps, and a worked example.
            </p>
          </div>
        )}

        {assistantMessages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'user' ? (
              <div className="max-w-[85%] rounded-2xl rounded-br-md bg-blue-600 text-white px-4 py-3 text-sm">
                <p>{msg.content}</p>
              </div>
            ) : (
              <div className="max-w-[95%] rounded-2xl rounded-bl-md bg-slate-800/80 border border-slate-700/50 px-4 py-3">
                {msg.data ? (
                  <StructuredMessage data={msg.data} />
                ) : (
                  <div className="prose prose-invert prose-sm max-w-none text-sm">
                    <MathRenderer content={msg.content} />
                  </div>
                )}
              </div>
            )}
          </div>
        ))}

        {assistantLoading && (
          <div className="flex justify-start">
            <div className="bg-slate-800/80 border border-slate-700/50 rounded-2xl rounded-bl-md px-4 py-3 flex items-center gap-2">
              <Loader2 size={16} className="animate-spin text-blue-400" />
              <span className="text-sm text-slate-400">Thinking…</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSend} className="px-4 py-3 border-t border-slate-700/60 bg-slate-950/60">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a math question…"
            disabled={assistantLoading}
            className="flex-1 bg-slate-800/60 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || assistantLoading}
            className="px-3 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-xl transition-colors"
          >
            <Send size={16} />
          </button>
        </div>
      </form>
    </div>
  );
};

export default ConceptAssistantPanel;
