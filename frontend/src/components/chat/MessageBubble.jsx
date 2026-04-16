import MathRenderer from './MathRenderer';
import ReasoningPlan from './ReasoningPlan';
import ExplainMode from './ExplainMode';
import FeedbackPanel from '../feedback/FeedbackPanel';
import useChatStore from '../../store/chatStore';
import {
  CheckCircle,
  XCircle,
  AlertCircle,
  BookOpen,
  BarChart3,
  Lightbulb,
} from 'lucide-react';

const topicColors = {
  algebra: 'bg-purple-900/40 text-purple-300',
  calculus: 'bg-blue-900/40 text-blue-300',
  geometry: 'bg-green-900/40 text-green-300',
  trigonometry: 'bg-orange-900/40 text-orange-300',
  statistics: 'bg-cyan-900/40 text-cyan-300',
  number_theory: 'bg-rose-900/40 text-rose-300',
  general_math: 'bg-slate-700/40 text-slate-300',
};

const difficultyColors = {
  basic: 'bg-emerald-900/30 text-emerald-300',
  intermediate: 'bg-amber-900/30 text-amber-300',
  advanced: 'bg-red-900/30 text-red-300',
};

const ValidationBadge = ({ validation }) => {
  if (!validation || validation.attempted === false) return null;

  if (validation.match === true) {
    return (
      <div className="flex items-center gap-1.5 text-emerald-400 text-xs mt-2 bg-emerald-900/20 px-2 py-1 rounded-lg w-fit">
        <CheckCircle size={14} />
        <span>Verified by SymPy</span>
      </div>
    );
  }
  if (validation.match === false) {
    return (
      <div className="flex items-center gap-1.5 text-red-400 text-xs mt-2 bg-red-900/20 px-2 py-1 rounded-lg w-fit">
        <XCircle size={14} />
        <span>SymPy found a different answer: {validation.sympy_answer}</span>
      </div>
    );
  }
  return (
    <div className="flex items-center gap-1.5 text-amber-400 text-xs mt-2 bg-amber-900/20 px-2 py-1 rounded-lg w-fit">
      <AlertCircle size={14} />
      <span>{validation.reason || 'Could not verify automatically'}</span>
    </div>
  );
};

const FollowUpSuggestions = ({ suggestions }) => {
  const { sendQuery, isLoading } = useChatStore();

  if (!suggestions || suggestions.length === 0) return null;

  return (
    <div className="mt-3 pt-2 border-t border-slate-700/50">
      <div className="flex items-center gap-1.5 text-xs text-slate-400 mb-2">
        <Lightbulb size={12} />
        <span>Try next:</span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {suggestions.map((s, i) => (
          <button
            key={i}
            onClick={() => sendQuery(s)}
            disabled={isLoading}
            className="text-xs bg-slate-700/50 hover:bg-slate-600/50 text-slate-300 hover:text-white px-2.5 py-1 rounded-lg transition-colors border border-slate-600/30 hover:border-slate-500/50"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
};

const MessageBubble = ({ message }) => {
  const isUser = message.role === 'user';
  const topic = message.metadata?.topic;
  const difficulty = message.metadata?.difficulty;

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} solvera-msg-appear`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-blue-600 text-white rounded-br-sm'
            : message.isError
              ? 'bg-red-900/30 text-red-200 border border-red-800/50 rounded-bl-sm'
              : message.isNonMath
                ? 'bg-amber-900/30 text-amber-200 border border-amber-800/50 rounded-bl-sm'
                : 'msg-bubble-assistant rounded-bl-sm'
        }`}
      >
        {/* Topic + Difficulty badges */}
        {!isUser && (topic || difficulty) && (
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            {topic && (
              <span
                className={`inline-block text-xs px-2 py-0.5 rounded-full ${topicColors[topic] || topicColors.general_math}`}
              >
                {topic.replace('_', ' ')}
              </span>
            )}
            {difficulty && (
              <span
                className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${difficultyColors[difficulty] || difficultyColors.intermediate}`}
              >
                <BarChart3 size={10} />
                {difficulty}
              </span>
            )}
          </div>
        )}

        {/* User image preview */}
        {message.imagePreview && (
          <img
            src={message.imagePreview}
            alt="Uploaded math"
            className="max-w-[240px] rounded-lg mb-2 border border-slate-600"
          />
        )}

        {/* Content */}
        {isUser ? (
          <p className="text-sm">{message.content}</p>
        ) : (
          <>
            {message.metadata?.reasoning_plan && (
              <ReasoningPlan
                steps={message.metadata.reasoning_plan}
                mathType={message.metadata.math_type}
              />
            )}
            <MathRenderer content={message.content} />
          </>
        )}

        {/* Plot */}
        {message.metadata?.plot_url && (
          <img
            src={message.metadata.plot_url}
            alt="Function plot"
            className="mt-3 rounded-lg max-w-full border border-slate-600"
          />
        )}

        {/* Validation badge */}
        {message.metadata?.validation && (
          <ValidationBadge validation={message.metadata.validation} />
        )}

        {/* RAG sources */}
        {message.metadata?.rag_sources?.length > 0 && (
          <details className="mt-2 text-xs text-slate-400">
            <summary className="cursor-pointer hover:text-slate-300 flex items-center gap-1">
              <BookOpen size={12} />
              References used ({message.metadata.rag_sources.length})
            </summary>
            <ul className="mt-1 ml-4 list-disc list-inside space-y-0.5">
              {message.metadata.rag_sources.map((src, i) => (
                <li key={i}>
                  {src.title} ({src.topic}) -{' '}
                  {(src.relevance * 100).toFixed(0)}% match
                </li>
              ))}
            </ul>
          </details>
        )}

        {/* Explain Mode (Text / Voice / Visual) */}
        {!isUser && !message.isError && !message.isNonMath && message.content && (
          <ExplainMode
            solution={message.content}
            question={message.metadata?.query}
            plotUrl={message.metadata?.plot_url}
          />
        )}

        {/* Follow-up suggestions */}
        {!isUser && message.metadata?.follow_up_suggestions && (
          <FollowUpSuggestions
            suggestions={message.metadata.follow_up_suggestions}
          />)
        }

        {/* Feedback panel for assistant messages */}
        {!isUser && message.metadata?.history_id && (
          <FeedbackPanel historyId={message.metadata.history_id} />
        )}
      </div>
    </div>
  );
};

export default MessageBubble;
