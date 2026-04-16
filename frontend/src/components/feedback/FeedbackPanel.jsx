import { useState } from 'react';
import api from '../../api/axiosInstance';
import { ThumbsUp, ThumbsDown, MessageSquare } from 'lucide-react';

const FeedbackPanel = ({ historyId }) => {
  const [rating, setRating] = useState(null);
  const [showCorrection, setShowCorrection] = useState(false);
  const [correction, setCorrection] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const submitFeedback = async (ratingValue, correctionText = null) => {
    try {
      await api.post('/feedback/', {
        history_id: historyId,
        rating: ratingValue,
        correction_text: correctionText,
        feedback_type: correctionText ? 'correction' : 'rating',
      });
      setSubmitted(true);
    } catch {
      // silently fail
    }
  };

  if (submitted) {
    return (
      <p className="text-xs text-emerald-400 mt-2">Feedback recorded. Thank you!</p>
    );
  }

  return (
    <div className="mt-3 pt-2 border-t border-slate-700">
      <div className="flex items-center gap-2">
        <span className="text-xs text-slate-400">Was this helpful?</span>
        <button
          onClick={() => {
            setRating(5);
            submitFeedback(5);
          }}
          className="p-1 text-slate-400 hover:text-emerald-400 transition-colors"
        >
          <ThumbsUp size={14} />
        </button>
        <button
          onClick={() => {
            setRating(1);
            setShowCorrection(true);
          }}
          className="p-1 text-slate-400 hover:text-red-400 transition-colors"
        >
          <ThumbsDown size={14} />
        </button>
        <button
          onClick={() => setShowCorrection(!showCorrection)}
          className="p-1 text-slate-400 hover:text-amber-400 transition-colors"
          title="Suggest correction"
        >
          <MessageSquare size={14} />
        </button>
      </div>
      {showCorrection && (
        <div className="mt-2">
          <textarea
            value={correction}
            onChange={(e) => setCorrection(e.target.value)}
            placeholder="What should the correct answer be?"
            className="w-full bg-slate-900 text-white text-sm rounded-lg p-2 h-16 border border-slate-600 focus:border-blue-500 focus:outline-none resize-none"
          />
          <button
            onClick={() => submitFeedback(rating || 2, correction)}
            className="mt-1 text-xs bg-amber-600 text-white px-3 py-1 rounded-lg hover:bg-amber-700 transition-colors"
          >
            Submit Correction
          </button>
        </div>
      )}
    </div>
  );
};

export default FeedbackPanel;
