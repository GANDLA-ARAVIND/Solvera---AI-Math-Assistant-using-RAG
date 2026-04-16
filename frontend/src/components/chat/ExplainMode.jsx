import { useState } from 'react';
import {
  BookOpen, BarChart3, ChevronDown, ChevronUp,
  Play, Square, Loader2,
} from 'lucide-react';
import MathRenderer from './MathRenderer';
import useSpeechSynthesis from '../../hooks/useSpeechSynthesis';
import api from '../../api/axiosInstance';

const API_BASE = import.meta.env.VITE_API_URL || '';

// ── Mode selector pills ────────────────────────────────────────
const modes = [
  { key: 'text', label: 'Text Explanation', icon: BookOpen, color: 'blue' },
  { key: 'voice', label: 'Voice Explanation', icon: Play, color: 'emerald' },
  { key: 'visual', label: 'Visual Explanation', icon: BarChart3, color: 'purple' },
];

const colorMap = {
  blue: {
    active: 'bg-blue-600 text-white border-blue-500',
    idle: 'bg-slate-800/60 text-slate-300 border-slate-700 hover:border-blue-500/50 hover:text-blue-300',
  },
  emerald: {
    active: 'bg-emerald-600 text-white border-emerald-500',
    idle: 'bg-slate-800/60 text-slate-300 border-slate-700 hover:border-emerald-500/50 hover:text-emerald-300',
  },
  purple: {
    active: 'bg-purple-600 text-white border-purple-500',
    idle: 'bg-slate-800/60 text-slate-300 border-slate-700 hover:border-purple-500/50 hover:text-purple-300',
  },
};

// ═══════════════════════════════════════════════════════════════════
//  Text Explanation Panel
// ═══════════════════════════════════════════════════════════════════

const TextPanel = ({ solution, query }) => {
  const [explanation, setExplanation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchExplanation = async () => {
    if (explanation) return; // already fetched
    setLoading(true);
    setError(null);
    try {
      const res = await api.post('/concept-assistant', {
        question: `Explain the solution to: ${query}\n\nSolution:\n${solution}`,
      });
      setExplanation(res.data);
    } catch {
      // Fallback: parse the existing solution into sections
      setExplanation(null);
      setError('Could not generate explanation. Showing original solution.');
    } finally {
      setLoading(false);
    }
  };

  // Auto-fetch on mount
  useState(() => { fetchExplanation(); });

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8 gap-2 text-slate-400">
        <Loader2 size={18} className="animate-spin" />
        <span className="text-sm">Generating structured explanation…</span>
      </div>
    );
  }

  // If we got structured data back
  if (explanation) {
    const sections = [
      { key: 'answer', label: 'Concept', icon: '📖', color: 'blue', content: explanation.answer },
      { key: 'formula', label: 'Formula', icon: '📐', color: 'purple', content: explanation.formula },
      { key: 'steps', label: 'Step-by-Step Explanation', icon: '📝', color: 'cyan', content: explanation.steps },
      { key: 'example', label: 'Worked Example', icon: '💡', color: 'amber', content: explanation.example },
      { key: 'key_takeaway', label: 'Key Takeaway', icon: '⭐', color: 'emerald', content: explanation.key_takeaway },
    ];

    const sectionColors = {
      blue: { border: 'border-blue-700/40', bg: 'bg-blue-900/15', heading: 'text-blue-400' },
      purple: { border: 'border-purple-700/40', bg: 'bg-purple-900/15', heading: 'text-purple-400' },
      cyan: { border: 'border-cyan-700/40', bg: 'bg-cyan-900/15', heading: 'text-cyan-400' },
      amber: { border: 'border-amber-700/40', bg: 'bg-amber-900/15', heading: 'text-amber-400' },
      emerald: { border: 'border-emerald-700/40', bg: 'bg-emerald-900/15', heading: 'text-emerald-400' },
    };

    return (
      <div className="space-y-3">
        {sections.map((s) => {
          if (!s.content) return null;
          const c = sectionColors[s.color];
          return (
            <div key={s.key} className={`rounded-xl border ${c.border} ${c.bg} p-3`}>
              <div className={`flex items-center gap-2 mb-2 text-xs font-semibold uppercase tracking-wide ${c.heading}`}>
                <span>{s.icon}</span>
                {s.label}
              </div>
              <div className="text-slate-200 text-sm leading-relaxed prose prose-invert prose-sm max-w-none">
                <MathRenderer content={s.content} />
              </div>
            </div>
          );
        })}
      </div>
    );
  }

  // Fallback: show the original solution with a note
  return (
    <div>
      {error && (
        <p className="text-xs text-amber-400 mb-2">{error}</p>
      )}
      <div className="text-slate-200 text-sm prose prose-invert prose-sm max-w-none">
        <MathRenderer content={solution} />
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════
//  Voice Explanation Panel (reuses existing useSpeechSynthesis hook)
// ═══════════════════════════════════════════════════════════════════

const VoicePanel = ({ solution, question }) => {
  const { play, stop, status, isSupported } = useSpeechSynthesis();

  if (!isSupported) {
    return <p className="text-sm text-slate-400">Voice is not supported in your browser.</p>;
  }

  const handlePlay = () => play(solution, question);
  const handleStop = () => stop();

  return (
    <div className="flex items-center gap-3">
      <button
        onClick={handlePlay}
        disabled={status === 'loading' || status === 'speaking'}
        className="voice-btn voice-btn--play"
        title="Play"
      >
        {status === 'loading' ? (
          <><Loader2 size={14} className="animate-spin" /><span>Loading…</span></>
        ) : (
          <><Play size={14} /><span>Play</span></>
        )}
      </button>
      <button
        onClick={handleStop}
        disabled={status === 'idle' || status === 'loading'}
        className="voice-btn voice-btn--stop"
        title="Stop"
      >
        <Square size={14} /><span>Stop</span>
      </button>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════
//  Visual Explanation Panel (graph)
// ═══════════════════════════════════════════════════════════════════

const VisualPanel = ({ solution, query, existingPlotUrl }) => {
  const [plotUrl, setPlotUrl] = useState(existingPlotUrl || null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Try to extract a plottable expression from the query / solution
  const extractExpression = () => {
    // Common patterns: "y = ...", "f(x) = ...", "graph of ..."
    const patterns = [
      /(?:y|f\(x\))\s*=\s*(.+?)(?:\n|$)/i,
      /(?:graph|plot)\s+(?:of\s+)?(.+?)(?:\n|$)/i,
      /(?:solve|integrate|differentiate|derivative of)\s+(.+?)(?:\n|$)/i,
    ];
    const text = query + '\n' + solution;
    for (const p of patterns) {
      const m = text.match(p);
      if (m) {
        // Clean up: remove LaTeX wrappers, $ signs
        return m[1]
          .replace(/\$+/g, '')
          .replace(/\\left|\\right/g, '')
          .replace(/\{|\}/g, '')
          .replace(/^\s+|\s+$/g, '')
          .replace(/\\cdot/g, '*')
          .replace(/\\frac\{([^}]+)\}\{([^}]+)\}/g, '($1)/($2)')
          .replace(/\\sin/g, 'sin')
          .replace(/\\cos/g, 'cos')
          .replace(/\\tan/g, 'tan')
          .replace(/\\ln/g, 'log')
          .replace(/\\sqrt\{([^}]+)\}/g, 'sqrt($1)')
          .trim();
      }
    }
    // Last fallback: try the raw query if it looks like an expression
    const clean = query.replace(/\$+/g, '').trim();
    if (/^[0-9x\s+\-*/^().sincotan,sqrtlogep]+$/i.test(clean) && clean.includes('x')) {
      return clean;
    }
    return null;
  };

  const fetchPlot = async () => {
    if (plotUrl) return;
    const expr = extractExpression();
    if (!expr) {
      setError('Could not identify a function to graph from this problem.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await api.post(`/solve/plot?expression=${encodeURIComponent(expr)}&x_min=-10&x_max=10`);
      if (res.data?.success && res.data?.plot_url) {
        setPlotUrl(res.data.plot_url);
      } else {
        setError('Graph generation failed. The expression may not be plottable.');
      }
    } catch {
      setError('Could not generate graph. Try a different expression.');
    } finally {
      setLoading(false);
    }
  };

  // Auto-fetch on mount
  useState(() => { if (!plotUrl) fetchPlot(); });

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8 gap-2 text-slate-400">
        <Loader2 size={18} className="animate-spin" />
        <span className="text-sm">Generating graph…</span>
      </div>
    );
  }

  if (error && !plotUrl) {
    return (
      <div className="py-6 text-center">
        <BarChart3 size={28} className="text-slate-600 mx-auto mb-2" />
        <p className="text-sm text-slate-400">{error}</p>
      </div>
    );
  }

  if (!plotUrl) return null;

  return (
    <div>
      <img
        src={plotUrl.startsWith('http') ? plotUrl : `${API_BASE}${plotUrl}`}
        alt="Function graph"
        className="w-full rounded-lg border border-slate-700"
      />
      <p className="text-xs text-slate-500 mt-2 text-center">Generated graph visualization</p>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════
//  ExplainMode — main exported component
// ═══════════════════════════════════════════════════════════════════

const ExplainMode = ({ solution, question, plotUrl }) => {
  const [open, setOpen] = useState(false);
  const [activeMode, setActiveMode] = useState(null); // 'text' | 'voice' | 'visual' | null

  const handleToggle = () => {
    setOpen((o) => !o);
    if (open) setActiveMode(null);
  };

  return (
    <div className="mt-3 pt-3 border-t border-slate-700/50">
      {/* Toggle button */}
      <button
        onClick={handleToggle}
        className="flex items-center gap-2 text-sm font-medium text-blue-400 hover:text-blue-300 transition-colors"
      >
        <BookOpen size={15} />
        <span>Explain</span>
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>

      {open && (
        <div className="mt-3">
          {/* Mode selector */}
          <div className="flex flex-wrap gap-2 mb-4">
            {modes.map((m) => {
              const Icon = m.icon;
              const isActive = activeMode === m.key;
              const c = colorMap[m.color];
              return (
                <button
                  key={m.key}
                  onClick={() => setActiveMode(isActive ? null : m.key)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-xl border text-xs font-medium transition-all ${
                    isActive ? c.active : c.idle
                  }`}
                >
                  <Icon size={14} />
                  {m.label}
                </button>
              );
            })}
          </div>

          {/* Panel content */}
          {activeMode === 'text' && (
            <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-4">
              <TextPanel solution={solution} query={question} />
            </div>
          )}

          {activeMode === 'voice' && (
            <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-4">
              <VoicePanel solution={solution} question={question} />
            </div>
          )}

          {activeMode === 'visual' && (
            <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-4">
              <VisualPanel solution={solution} query={question} existingPlotUrl={plotUrl} />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ExplainMode;
