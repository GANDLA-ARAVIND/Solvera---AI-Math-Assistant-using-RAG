import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  BookOpen,
  FileText,
  Lightbulb,
  PenTool,
  ChevronRight,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Send,
  RotateCcw,
  HelpCircle,
  Calculator,
  Sigma,
  Triangle,
  Circle,
  BarChart3,
  MessageCircle,
  Sparkles,
} from 'lucide-react';
import useConceptStore from '../store/conceptStore';
import MathRenderer from '../components/chat/MathRenderer';
import ConceptAssistantPanel from '../components/concept/ConceptAssistantPanel';

const API_BASE = import.meta.env.VITE_API_URL || '';

// ── Topic icon mapping ───────────────────────────────────────────
const topicIcons = {
  algebra: Calculator,
  calculus: Sigma,
  trigonometry: Triangle,
  geometry: Circle,
  statistics: BarChart3,
};

const topicColors = {
  algebra: { gradient: 'from-blue-500 to-cyan-500', bg: 'bg-blue-600/20', text: 'text-blue-400', border: 'border-blue-500/40' },
  calculus: { gradient: 'from-purple-500 to-pink-500', bg: 'bg-purple-600/20', text: 'text-purple-400', border: 'border-purple-500/40' },
  trigonometry: { gradient: 'from-amber-500 to-orange-500', bg: 'bg-amber-600/20', text: 'text-amber-400', border: 'border-amber-500/40' },
  geometry: { gradient: 'from-emerald-500 to-green-500', bg: 'bg-emerald-600/20', text: 'text-emerald-400', border: 'border-emerald-500/40' },
  statistics: { gradient: 'from-red-500 to-rose-500', bg: 'bg-red-600/20', text: 'text-red-400', border: 'border-red-500/40' },
};

const pretty = (s) => s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

// ── Topic Selector ───────────────────────────────────────────────
const TopicSelector = () => {
  const { topics, selectedTopic, selectedSubtopic, selectTopic, selectSubtopic, error } = useConceptStore();
  const navigate = useNavigate();

  const topicKeys = Object.keys(topics);

  return (
    <div className="max-w-4xl mx-auto">
      <button
        onClick={() => navigate('/dashboard')}
        className="flex items-center gap-2 text-slate-400 hover:text-white mb-8 transition-colors"
      >
        <ArrowLeft size={18} />
        <span className="text-sm">Back to Dashboard</span>
      </button>

      <h2 className="text-2xl font-bold text-white mb-2">Concept Learning Mode</h2>
      <p className="text-slate-400 mb-8">Select a topic and subtopic to start learning</p>

      {error && (
        <div className="mb-6 p-3 bg-red-900/30 border border-red-700/50 rounded-lg text-red-300 text-sm flex items-center gap-2">
          <AlertTriangle size={16} />
          {error}
        </div>
      )}

      {/* Topic cards */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {topicKeys.map((topic) => {
          const Icon = topicIcons[topic] || BookOpen;
          const colors = topicColors[topic] || topicColors.algebra;
          const isSelected = selectedTopic === topic;
          return (
            <button
              key={topic}
              onClick={() => selectTopic(topic)}
              className={`group relative rounded-2xl border ${isSelected ? colors.border + ' ring-2 ring-offset-2 ring-offset-slate-950 ring-blue-500/50' : 'border-slate-700/60'} bg-slate-900/60 p-5 text-left hover:-translate-y-0.5 hover:shadow-lg transition-all duration-200`}
            >
              <div className={`h-1 absolute top-0 left-0 right-0 bg-gradient-to-r ${colors.gradient} rounded-t-2xl`} />
              <Icon size={24} className={`${colors.text} mb-3`} />
              <h3 className="text-base font-semibold text-white">{pretty(topic)}</h3>
              <p className="text-xs text-slate-500 mt-1">{topics[topic].length} subtopics</p>
            </button>
          );
        })}
      </div>

      {/* Subtopic list */}
      {selectedTopic && topics[selectedTopic] && (
        <div className="bg-slate-800/50 border border-slate-700/60 rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">
            {pretty(selectedTopic)} — Choose a subtopic
          </h3>
          <div className="grid sm:grid-cols-2 gap-3">
            {topics[selectedTopic].map((sub) => {
              const isSelected = selectedSubtopic === sub;
              return (
                <button
                  key={sub}
                  onClick={() => selectSubtopic(sub)}
                  className={`text-left px-4 py-3 rounded-xl border transition-all ${
                    isSelected
                      ? 'border-blue-500/60 bg-blue-600/10 text-blue-300'
                      : 'border-slate-700/40 bg-slate-900/40 text-slate-300 hover:border-slate-600 hover:text-white'
                  }`}
                >
                  {pretty(sub)}
                </button>
              );
            })}
          </div>

          {/* Action buttons */}
          {selectedSubtopic && (
            <div className="mt-6 pt-6 border-t border-slate-700/40">
              <p className="text-sm text-slate-400 mb-4">
                Learning <span className="text-white font-medium">{pretty(selectedSubtopic)}</span> — choose an action:
              </p>
              <ActionButtons />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ── Action buttons ───────────────────────────────────────────────
const ActionButtons = () => {
  const { fetchExplanation, fetchFormulas, fetchExample, fetchPractice, fetchBundle, selectedTopic } = useConceptStore();

  const actions = [
    { label: 'Explain Concept', icon: BookOpen, action: fetchExplanation, color: 'bg-blue-600 hover:bg-blue-700' },
    { label: 'Show Formulas', icon: FileText, action: fetchFormulas, color: 'bg-purple-600 hover:bg-purple-700' },
    { label: 'Worked Example', icon: Lightbulb, action: fetchExample, color: 'bg-amber-600 hover:bg-amber-700' },
    { label: 'Practice Question', icon: PenTool, action: fetchPractice, color: 'bg-emerald-600 hover:bg-emerald-700' },
  ];

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {actions.map((a) => {
          const Icon = a.icon;
          return (
            <button
              key={a.label}
              onClick={a.action}
              className={`${a.color} text-white font-medium py-3 px-4 rounded-xl transition-colors flex flex-col items-center gap-2 text-sm`}
            >
              <Icon size={20} />
              {a.label}
            </button>
          );
        })}
      </div>
      {selectedTopic && (
        <button
          onClick={() => fetchBundle()}
          className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-medium py-3 px-4 rounded-xl transition-all flex items-center justify-center gap-2 text-sm"
        >
          <Sparkles size={18} />
          Learn Complete Topic (All-in-One)
        </button>
      )}
    </div>
  );
};

// ── Content display (explanation / formulas / example) ────────────
const ContentView = ({ title, content, icon: Icon }) => {
  const { goToTopics, selectedTopic, selectedSubtopic, plotUrl } = useConceptStore();

  return (
    <div className="max-w-3xl mx-auto">
      {/* Breadcrumb */}
      <button
        onClick={goToTopics}
        className="flex items-center gap-2 text-slate-400 hover:text-white mb-6 transition-colors"
      >
        <ArrowLeft size={18} />
        <span className="text-sm">Back to Topics</span>
      </button>

      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-blue-600/20 rounded-lg flex items-center justify-center">
          <Icon size={20} className="text-blue-400" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">{title}</h2>
          <p className="text-sm text-slate-400">
            {pretty(selectedTopic)} → {pretty(selectedSubtopic)}
          </p>
        </div>
      </div>

      {/* Content */}
      <div className="bg-slate-800/50 border border-slate-700/60 rounded-2xl p-6 mb-6">
        <div className="text-slate-200 leading-relaxed prose prose-invert prose-sm max-w-none">
          <MathRenderer content={content} />
        </div>
      </div>

      {/* Plot if available */}
      {plotUrl && (
        <div className="bg-slate-800/50 border border-slate-700/60 rounded-2xl p-4 mb-6">
          <h4 className="text-sm font-semibold text-blue-400 mb-3 uppercase tracking-wide">Graph</h4>
          <img
            src={`${API_BASE}${plotUrl}`}
            alt="Concept graph"
            className="w-full rounded-lg"
          />
        </div>
      )}

      {/* Action buttons to continue */}
      <div className="pt-2">
        <p className="text-sm text-slate-400 mb-3">Continue learning:</p>
        <ActionButtons />
      </div>
    </div>
  );
};

// ── Practice Question View ───────────────────────────────────────
const PracticeView = () => {
  const {
    practiceQuestion, practiceHint, submitPracticeAnswer, goToTopics,
    selectedTopic, selectedSubtopic, status, error,
  } = useConceptStore();
  const [answer, setAnswer] = useState('');
  const [showHint, setShowHint] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
    setAnswer('');
    setShowHint(false);
  }, [practiceQuestion]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!answer.trim()) return;
    submitPracticeAnswer(answer.trim());
  };

  const isSubmitting = status === 'evaluating';

  return (
    <div className="max-w-3xl mx-auto">
      <button
        onClick={goToTopics}
        className="flex items-center gap-2 text-slate-400 hover:text-white mb-6 transition-colors"
      >
        <ArrowLeft size={18} />
        <span className="text-sm">Back to Topics</span>
      </button>

      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-emerald-600/20 rounded-lg flex items-center justify-center">
          <PenTool size={20} className="text-emerald-400" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">Practice Question</h2>
          <p className="text-sm text-slate-400">
            {pretty(selectedTopic)} → {pretty(selectedSubtopic)}
          </p>
        </div>
      </div>

      {/* Question */}
      <div className="bg-slate-800/50 border border-slate-700/60 rounded-2xl p-6 mb-6">
        <div className="text-lg text-white leading-relaxed">
          <MathRenderer content={practiceQuestion} />
        </div>
      </div>

      {/* Hint */}
      {practiceHint && (
        <div className="mb-6">
          {!showHint ? (
            <button
              onClick={() => setShowHint(true)}
              className="flex items-center gap-2 text-sm text-amber-400 hover:text-amber-300 transition-colors"
            >
              <HelpCircle size={16} />
              Show Hint
            </button>
          ) : (
            <div className="p-4 bg-amber-900/20 border border-amber-700/40 rounded-xl">
              <p className="text-sm text-amber-300 flex items-center gap-2 mb-1">
                <HelpCircle size={14} />
                Hint
              </p>
              <div className="text-sm text-amber-200">
                <MathRenderer content={practiceHint} />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Answer input */}
      <form onSubmit={handleSubmit}>
        <div className="flex gap-3">
          <input
            ref={inputRef}
            type="text"
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Type your answer here..."
            disabled={isSubmitting}
            className="flex-1 bg-slate-800/60 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!answer.trim() || isSubmitting}
            className="px-6 py-3 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-700 disabled:text-slate-500 text-white font-medium rounded-xl transition-colors flex items-center gap-2"
          >
            {isSubmitting ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                Checking
              </>
            ) : (
              <>
                <Send size={18} />
                Submit
              </>
            )}
          </button>
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Enter a number (e.g. 42), fraction (3/4), or expression (3*x**2)
        </p>
      </form>

      {error && (
        <div className="mt-4 p-3 bg-red-900/30 border border-red-700/50 rounded-lg text-red-300 text-sm flex items-center gap-2">
          <AlertTriangle size={16} />
          {error}
        </div>
      )}
    </div>
  );
};

// ── Practice Result View ─────────────────────────────────────────
const PracticeResultView = () => {
  const { practiceResult, fetchPractice, goToTopics, selectedTopic, selectedSubtopic } = useConceptStore();

  if (!practiceResult) return null;

  return (
    <div className="max-w-3xl mx-auto">
      <button
        onClick={goToTopics}
        className="flex items-center gap-2 text-slate-400 hover:text-white mb-6 transition-colors"
      >
        <ArrowLeft size={18} />
        <span className="text-sm">Back to Topics</span>
      </button>

      {/* Verdict */}
      <div
        className={`rounded-2xl p-5 mb-6 flex items-center gap-4 ${
          practiceResult.is_correct
            ? 'bg-emerald-900/30 border border-emerald-700/50'
            : 'bg-red-900/30 border border-red-700/50'
        }`}
      >
        {practiceResult.is_correct ? (
          <CheckCircle2 size={32} className="text-emerald-400 flex-shrink-0" />
        ) : (
          <XCircle size={32} className="text-red-400 flex-shrink-0" />
        )}
        <div>
          <h3 className={`text-lg font-bold ${practiceResult.is_correct ? 'text-emerald-300' : 'text-red-300'}`}>
            {practiceResult.is_correct ? 'Correct!' : 'Not Quite Right'}
          </h3>
          <p className="text-sm text-slate-400 mt-0.5">
            Your answer: <span className="text-white">{practiceResult.user_answer}</span>
            {!practiceResult.is_correct && (
              <>
                {' · '}Correct answer: <span className="text-white">{practiceResult.correct_answer}</span>
              </>
            )}
          </p>
        </div>
      </div>

      {/* Solution */}
      {practiceResult.solution && (
        <div className="bg-slate-800/50 border border-slate-700/60 rounded-2xl p-6 mb-6">
          <h4 className="text-sm font-semibold text-blue-400 mb-3 uppercase tracking-wide">
            Step-by-Step Solution
          </h4>
          <div className="text-slate-200 leading-relaxed prose prose-invert prose-sm max-w-none">
            <MathRenderer content={practiceResult.solution} />
          </div>
        </div>
      )}

      {/* Feedback (if incorrect) */}
      {practiceResult.feedback && (
        <div className="bg-amber-900/20 border border-amber-700/40 rounded-2xl p-6 mb-6">
          <h4 className="text-sm font-semibold text-amber-400 mb-3 uppercase tracking-wide">
            Feedback
          </h4>
          <div className="text-amber-200 leading-relaxed prose prose-invert prose-sm max-w-none">
            <MathRenderer content={practiceResult.feedback} />
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-4">
        <button
          onClick={fetchPractice}
          className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-3 rounded-xl transition-colors flex items-center justify-center gap-2"
        >
          <RotateCcw size={16} />
          Try Another Question
        </button>
        <button
          onClick={goToTopics}
          className="px-6 py-3 text-slate-400 hover:text-white border border-slate-700 hover:border-slate-600 rounded-xl transition-colors"
        >
          Back to Topics
        </button>
      </div>
    </div>
  );
};

// ── Loading View ─────────────────────────────────────────────────
const LoadingView = () => (
  <div className="flex flex-col items-center justify-center py-32">
    <Loader2 size={36} className="text-blue-400 animate-spin mb-4" />
    <p className="text-slate-400">Generating content…</p>
  </div>
);

// ── Bundle View (single-call /concept-mode response) ─────────────
const BundleView = () => {
  const { bundle, goToTopics, selectedTopic } = useConceptStore();
  if (!bundle) return null;

  return (
    <div className="max-w-3xl mx-auto">
      <button
        onClick={goToTopics}
        className="flex items-center gap-2 text-slate-400 hover:text-white mb-6 transition-colors"
      >
        <ArrowLeft size={18} />
        <span className="text-sm">Back to Topics</span>
      </button>

      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-lg flex items-center justify-center">
          <Sparkles size={20} className="text-blue-400" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">
            {selectedTopic ? pretty(selectedTopic) : 'Concept Bundle'}
          </h2>
          <p className="text-sm text-slate-400">Complete learning overview</p>
        </div>
      </div>

      {/* Concept explanation */}
      {bundle.concept && (
        <div className="bg-slate-800/50 border border-slate-700/60 rounded-2xl p-6 mb-4">
          <h4 className="text-sm font-semibold text-blue-400 mb-3 uppercase tracking-wide flex items-center gap-2">
            <BookOpen size={14} /> Concept
          </h4>
          <div className="text-slate-200 leading-relaxed prose prose-invert prose-sm max-w-none">
            <MathRenderer content={bundle.concept} />
          </div>
        </div>
      )}

      {/* Formulas */}
      {bundle.formula && (
        <div className="bg-slate-800/50 border border-slate-700/60 rounded-2xl p-6 mb-4">
          <h4 className="text-sm font-semibold text-purple-400 mb-3 uppercase tracking-wide flex items-center gap-2">
            <FileText size={14} /> Key Formulas
          </h4>
          <div className="text-slate-200 leading-relaxed prose prose-invert prose-sm max-w-none">
            <MathRenderer content={bundle.formula} />
          </div>
        </div>
      )}

      {/* Worked example */}
      {bundle.example && (
        <div className="bg-slate-800/50 border border-slate-700/60 rounded-2xl p-6 mb-4">
          <h4 className="text-sm font-semibold text-amber-400 mb-3 uppercase tracking-wide flex items-center gap-2">
            <Lightbulb size={14} /> Worked Example
          </h4>
          <div className="text-slate-200 leading-relaxed prose prose-invert prose-sm max-w-none">
            <MathRenderer content={bundle.example} />
          </div>
        </div>
      )}

      {/* Graph */}
      {bundle.graph && (
        <div className="bg-slate-800/50 border border-slate-700/60 rounded-2xl p-4 mb-4">
          <h4 className="text-sm font-semibold text-emerald-400 mb-3 uppercase tracking-wide">Graph</h4>
          <img
            src={`${API_BASE}${bundle.graph}`}
            alt="Concept graph"
            className="w-full rounded-lg"
          />
        </div>
      )}

      {/* Practice question preview */}
      {bundle.practice_question && (
        <div className="bg-emerald-900/20 border border-emerald-700/40 rounded-2xl p-6 mb-4">
          <h4 className="text-sm font-semibold text-emerald-400 mb-3 uppercase tracking-wide flex items-center gap-2">
            <PenTool size={14} /> Practice Question
          </h4>
          <div className="text-slate-200 leading-relaxed prose prose-invert prose-sm max-w-none">
            <MathRenderer content={bundle.practice_question} />
          </div>
        </div>
      )}

      {/* Continue actions */}
      <div className="pt-2">
        <p className="text-sm text-slate-400 mb-3">Explore further:</p>
        <ActionButtons />
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════
//  Main page
// ═══════════════════════════════════════════════════════════════════
const ConceptPage = () => {
  const { status, fetchTopics, explanation, formulas, example, assistantOpen, toggleAssistant } = useConceptStore();

  useEffect(() => {
    if (status === 'idle') fetchTopics();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Top bar */}
      <nav className="fixed top-0 inset-x-0 z-50 bg-slate-950/80 backdrop-blur-md border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-blue-600/20 rounded-lg flex items-center justify-center">
              <span className="text-blue-400 font-bold text-sm">S</span>
            </div>
            <span className="text-lg font-bold text-white">
              <span className="text-blue-400">Solv</span>era
            </span>
            <span className="ml-2 text-xs text-slate-500">/ Concept Learning Mode</span>
          </div>
        </div>
      </nav>

      <main className="pt-24 pb-16 px-6">
        {status === 'topics' && <TopicSelector />}
        {status === 'loading' && <LoadingView />}
        {status === 'explanation' && <ContentView title="Concept Explanation" content={explanation} icon={BookOpen} />}
        {status === 'formulas' && <ContentView title="Key Formulas" content={formulas} icon={FileText} />}
        {status === 'example' && <ContentView title="Worked Example" content={example} icon={Lightbulb} />}
        {status === 'practice' && <PracticeView />}
        {status === 'evaluating' && <PracticeView />}
        {status === 'result' && <PracticeResultView />}
        {status === 'bundle' && <BundleView />}
      </main>

      {/* Concept Assistant sliding panel */}
      <ConceptAssistantPanel />

      {/* Floating Concept Assistant button */}
      {!assistantOpen && (
        <button
          onClick={toggleAssistant}
          className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-600/30 flex items-center justify-center transition-all hover:scale-105"
          title="Open Concept Assistant"
        >
          <MessageCircle size={22} />
        </button>
      )}
    </div>
  );
};

export default ConceptPage;
