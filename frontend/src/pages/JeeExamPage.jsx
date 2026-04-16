import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Clock,
  CheckCircle2,
  XCircle,
  ChevronRight,
  Trophy,
  Target,
  Zap,
  BarChart3,
  RotateCcw,
  Send,
  Loader2,
  AlertTriangle,
  BookOpen,
  Download,
} from 'lucide-react';
import { jsPDF } from 'jspdf';
import useExamStore from '../store/examStore';
import MathRenderer from '../components/chat/MathRenderer';

// ── Timer component ──────────────────────────────────────────────
const Timer = () => {
  const { questionStartTime, setElapsed, elapsedSeconds, status } = useExamStore();

  useEffect(() => {
    if (status !== 'question' || !questionStartTime) return;
    const id = setInterval(() => {
      setElapsed(Math.floor((Date.now() - questionStartTime) / 1000));
    }, 1000);
    return () => clearInterval(id);
  }, [status, questionStartTime, setElapsed]);

  const mins = Math.floor(elapsedSeconds / 60);
  const secs = elapsedSeconds % 60;

  return (
    <div className="flex items-center gap-2 text-slate-300 font-mono text-lg">
      <Clock size={18} className="text-blue-400" />
      <span>
        {String(mins).padStart(2, '0')}:{String(secs).padStart(2, '0')}
      </span>
    </div>
  );
};

// ── Difficulty selector ──────────────────────────────────────────
const DifficultySelector = () => {
  const { startExam, error } = useExamStore();
  const navigate = useNavigate();

  const levels = [
    {
      key: 'basic',
      label: 'Basic',
      desc: 'Fundamentals & NCERT level',
      color: 'from-emerald-500 to-green-500',
      border: 'border-emerald-500/40',
      icon: BookOpen,
      iconColor: 'text-emerald-400',
    },
    {
      key: 'medium',
      label: 'Medium',
      desc: 'JEE Mains standard',
      color: 'from-amber-500 to-orange-500',
      border: 'border-amber-500/40',
      icon: Target,
      iconColor: 'text-amber-400',
    },
    {
      key: 'hard',
      label: 'Hard',
      desc: 'JEE Advanced level',
      color: 'from-red-500 to-pink-500',
      border: 'border-red-500/40',
      icon: Zap,
      iconColor: 'text-red-400',
    },
  ];

  return (
    <div className="max-w-3xl mx-auto">
      <button
        onClick={() => navigate('/dashboard')}
        className="flex items-center gap-2 text-slate-400 hover:text-white mb-8 transition-colors"
      >
        <ArrowLeft size={18} />
        <span className="text-sm">Back to Dashboard</span>
      </button>

      <h2 className="text-2xl font-bold text-white mb-2">JEE Exam Mode</h2>
      <p className="text-slate-400 mb-8">Select difficulty level to begin</p>

      {error && (
        <div className="mb-6 p-3 bg-red-900/30 border border-red-700/50 rounded-lg text-red-300 text-sm flex items-center gap-2">
          <AlertTriangle size={16} />
          {error}
        </div>
      )}

      <div className="grid sm:grid-cols-3 gap-5">
        {levels.map((lv) => {
          const Icon = lv.icon;
          return (
            <button
              key={lv.key}
              onClick={() => startExam(lv.key)}
              className={`group relative rounded-2xl border ${lv.border} bg-slate-900/60 p-6 text-left hover:-translate-y-1 hover:shadow-xl transition-all duration-300`}
            >
              <div className={`h-1 absolute top-0 left-0 right-0 bg-gradient-to-r ${lv.color} rounded-t-2xl`} />
              <Icon size={28} className={`${lv.iconColor} mb-4`} />
              <h3 className="text-lg font-semibold text-white mb-1">{lv.label}</h3>
              <p className="text-sm text-slate-400">{lv.desc}</p>
              <div className="mt-4 flex items-center gap-1 text-sm text-slate-400 group-hover:text-blue-400 transition-colors">
                Start <ChevronRight size={14} className="group-hover:translate-x-1 transition-transform" />
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};

// ── Question card ────────────────────────────────────────────────
const QuestionCard = () => {
  const { question, questionNumber, topic, difficulty, score, submitAnswer, status, error, endExam } =
    useExamStore();
  const [answer, setAnswer] = useState('');
  const inputRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
    setAnswer('');
  }, [questionNumber]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!answer.trim()) return;
    submitAnswer(answer.trim());
  };

  const isSubmitting = status === 'submitting';

  return (
    <div className="max-w-3xl mx-auto">
      {/* Top bar */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <span className="px-3 py-1 text-xs font-medium bg-blue-600/20 text-blue-300 border border-blue-500/30 rounded-full">
            Q{questionNumber}
          </span>
          <span className="px-3 py-1 text-xs font-medium bg-slate-800 text-slate-300 rounded-full capitalize">
            {topic}
          </span>
          <span className="px-3 py-1 text-xs font-medium bg-slate-800 text-slate-300 rounded-full capitalize">
            {difficulty}
          </span>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-sm text-slate-400">
            Score: <span className="text-white font-semibold">{score}</span>
          </div>
          <Timer />
        </div>
      </div>

      {/* Question */}
      <div className="bg-slate-800/50 border border-slate-700/60 rounded-2xl p-6 mb-6">
        <div className="text-lg text-white leading-relaxed">
          <MathRenderer content={question} />
        </div>
      </div>

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
            className="flex-1 bg-slate-800/60 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!answer.trim() || isSubmitting}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:text-slate-500 text-white font-medium rounded-xl transition-colors flex items-center gap-2"
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
          Enter a number (e.g. 42), fraction (3/4), or expression (3*x**2). For multiple roots use: 2, 3
        </p>
      </form>

      {error && (
        <div className="mt-4 p-3 bg-red-900/30 border border-red-700/50 rounded-lg text-red-300 text-sm flex items-center gap-2">
          <AlertTriangle size={16} />
          {error}
        </div>
      )}

      {/* End exam button */}
      <div className="mt-6 flex justify-end">
        <button
          onClick={endExam}
          className="text-sm text-slate-500 hover:text-red-400 transition-colors"
        >
          End Exam
        </button>
      </div>
    </div>
  );
};

// ── Result card ──────────────────────────────────────────────────
const ResultCard = () => {
  const { lastResult, nextQuestion, endExam, status, error } = useExamStore();
  const isLoading = status === 'loading';

  if (!lastResult) return null;

  return (
    <div className="max-w-3xl mx-auto">
      {/* Verdict banner */}
      <div
        className={`rounded-2xl p-5 mb-6 flex items-center gap-4 ${
          lastResult.is_correct
            ? 'bg-emerald-900/30 border border-emerald-700/50'
            : 'bg-red-900/30 border border-red-700/50'
        }`}
      >
        {lastResult.is_correct ? (
          <CheckCircle2 size={32} className="text-emerald-400 flex-shrink-0" />
        ) : (
          <XCircle size={32} className="text-red-400 flex-shrink-0" />
        )}
        <div>
          <h3
            className={`text-lg font-bold ${
              lastResult.is_correct ? 'text-emerald-300' : 'text-red-300'
            }`}
          >
            {lastResult.is_correct ? 'Correct!' : 'Incorrect'}
          </h3>
          <p className="text-sm text-slate-400 mt-0.5">
            Your answer: <span className="text-white">{lastResult.user_answer}</span>
            {!lastResult.is_correct && (
              <>
                {' · '}Correct answer: <span className="text-white">{lastResult.correct_answer}</span>
              </>
            )}
          </p>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        {[
          { label: 'Score', value: lastResult.score, icon: Trophy, color: 'text-amber-400' },
          {
            label: 'Accuracy',
            value: `${lastResult.accuracy_percent}%`,
            icon: Target,
            color: 'text-blue-400',
          },
          { label: 'Correct', value: `${lastResult.correct_count}/${lastResult.total_attempted}`, icon: CheckCircle2, color: 'text-emerald-400' },
          {
            label: 'Time',
            value: `${lastResult.time_taken_seconds}s`,
            icon: Clock,
            color: 'text-purple-400',
          },
        ].map((stat, i) => {
          const Icon = stat.icon;
          return (
            <div key={i} className="bg-slate-800/50 border border-slate-700/40 rounded-xl p-3 text-center">
              <Icon size={16} className={`${stat.color} mx-auto mb-1`} />
              <p className="text-sm font-semibold text-white">{stat.value}</p>
              <p className="text-xs text-slate-500">{stat.label}</p>
            </div>
          );
        })}
      </div>

      {/* Solution */}
      <div className="bg-slate-800/50 border border-slate-700/60 rounded-2xl p-6 mb-6">
        <h4 className="text-sm font-semibold text-blue-400 mb-3 uppercase tracking-wide">
          Step-by-Step Solution
        </h4>
        <div className="text-slate-200 leading-relaxed prose prose-invert prose-sm max-w-none">
          <MathRenderer content={lastResult.solution} />
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-amber-900/30 border border-amber-700/50 rounded-lg text-amber-300 text-sm flex items-center gap-2">
          <AlertTriangle size={16} />
          {error}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-4">
        <button
          onClick={nextQuestion}
          disabled={isLoading}
          className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 text-white font-medium py-3 rounded-xl transition-colors flex items-center justify-center gap-2"
        >
          {isLoading ? (
            <>
              <Loader2 size={18} className="animate-spin" />
              Loading…
            </>
          ) : (
            <>
              Next Question
              <ChevronRight size={18} />
            </>
          )}
        </button>
        <button
          onClick={endExam}
          className="px-6 py-3 text-slate-400 hover:text-red-400 border border-slate-700 hover:border-red-700/50 rounded-xl transition-colors"
        >
          End Exam
        </button>
      </div>
    </div>
  );
};

// ── Final scorecard ──────────────────────────────────────────────
const ScoreCard = () => {
  const { score, correctCount, totalAttempted, accuracyPercent, totalTimeSeconds, weakTopics, difficulty, attemptHistory, resetExam, goToSelect } =
    useExamStore();
  const navigate = useNavigate();

  const mins = Math.floor(totalTimeSeconds / 60);
  const secs = Math.round(totalTimeSeconds % 60);

  const downloadReportPdf = () => {
    const doc = new jsPDF({ unit: 'pt', format: 'a4' });
    const margin = 40;
    const pageHeight = doc.internal.pageSize.getHeight();
    const pageWidth = doc.internal.pageSize.getWidth();
    const maxWidth = pageWidth - margin * 2;
    let y = margin;

    const ensureSpace = (requiredHeight = 16) => {
      if (y + requiredHeight > pageHeight - margin) {
        doc.addPage();
        y = margin;
      }
    };

    const addText = (text, fontSize = 11, isBold = false, spacing = 16) => {
      doc.setFont('helvetica', isBold ? 'bold' : 'normal');
      doc.setFontSize(fontSize);
      const safeText = String(text ?? '').replace(/\s+/g, ' ').trim() || '-';
      const lines = doc.splitTextToSize(safeText, maxWidth);
      lines.forEach((line) => {
        ensureSpace(spacing);
        doc.text(line, margin, y);
        y += spacing;
      });
    };

    addText('Solvera - JEE Exam Report', 18, true, 22);
    addText(`Generated on: ${new Date().toLocaleString()}`, 10, false, 14);
    y += 6;

    addText('Exam Summary', 13, true, 18);
    addText(`Difficulty: ${difficulty || 'N/A'}`);
    addText(`Total Score: ${score}`);
    addText(`Accuracy: ${accuracyPercent}%`);
    addText(`Correct Answers: ${correctCount}/${totalAttempted}`);
    addText(`Total Time: ${mins}m ${secs}s`);
    addText(
      `Weak Topics: ${weakTopics.length > 0 ? weakTopics.join(', ') : 'None'}`,
    );

    y += 8;
    addText('Question-wise Details', 13, true, 18);

    if (!attemptHistory || attemptHistory.length === 0) {
      addText('No answered questions were recorded for this session.');
    } else {
      attemptHistory.forEach((entry) => {
        y += 4;
        addText(`Q${entry.questionNumber} (${entry.topic || 'general_math'})`, 12, true, 16);
        addText(`Question: ${entry.question}`);
        addText(`Your Answer: ${entry.userAnswer}`);
        addText(`Correct Answer: ${entry.correctAnswer}`);
        addText(`Result: ${entry.isCorrect ? 'Correct' : 'Incorrect'}`);
        addText(`Time Taken: ${entry.timeTakenSeconds}s`);

        if (entry.solution) {
          addText('Solution:', 11, true, 16);
          addText(entry.solution);
        }
      });
    }

    const fileDate = new Date().toISOString().slice(0, 10);
    doc.save(`jee-exam-report-${fileDate}.pdf`);
  };

  return (
    <div className="max-w-lg mx-auto text-center">
      <div className="bg-slate-800/50 border border-slate-700/60 rounded-2xl p-8">
        <Trophy size={48} className="text-amber-400 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-white mb-1">Exam Complete!</h2>
        <p className="text-slate-400 text-sm mb-6 capitalize">{difficulty} Level</p>

        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-slate-900/60 rounded-xl p-4">
            <p className="text-2xl font-bold text-white">{score}</p>
            <p className="text-xs text-slate-500">Total Score</p>
          </div>
          <div className="bg-slate-900/60 rounded-xl p-4">
            <p className="text-2xl font-bold text-white">{accuracyPercent}%</p>
            <p className="text-xs text-slate-500">Accuracy</p>
          </div>
          <div className="bg-slate-900/60 rounded-xl p-4">
            <p className="text-2xl font-bold text-white">
              {correctCount}/{totalAttempted}
            </p>
            <p className="text-xs text-slate-500">Correct</p>
          </div>
          <div className="bg-slate-900/60 rounded-xl p-4">
            <p className="text-2xl font-bold text-white">
              {mins}m {secs}s
            </p>
            <p className="text-xs text-slate-500">Total Time</p>
          </div>
        </div>

        {weakTopics.length > 0 && (
          <div className="mb-6 text-left bg-amber-900/20 border border-amber-700/40 rounded-xl p-4">
            <p className="text-sm font-medium text-amber-300 mb-2 flex items-center gap-2">
              <BarChart3 size={14} />
              Weak Topics — needs more practice
            </p>
            <div className="flex flex-wrap gap-2">
              {weakTopics.map((t) => (
                <span key={t} className="px-3 py-1 text-xs bg-amber-900/40 text-amber-200 rounded-full capitalize">
                  {t}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="flex gap-3 flex-wrap">
          <button
            onClick={downloadReportPdf}
            className="w-full sm:w-auto sm:flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-3 rounded-xl transition-colors flex items-center justify-center gap-2"
          >
            <Download size={16} />
            Download PDF
          </button>
          <button
            onClick={() => {
              resetExam();
              goToSelect();
            }}
            className="w-full sm:w-auto sm:flex-1 bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 rounded-xl transition-colors flex items-center justify-center gap-2"
          >
            <RotateCcw size={16} />
            Try Again
          </button>
          <button
            onClick={() => {
              resetExam();
              navigate('/dashboard');
            }}
            className="w-full sm:w-auto sm:flex-1 border border-slate-700 text-slate-300 hover:text-white hover:border-slate-600 font-medium py-3 rounded-xl transition-colors"
          >
            Dashboard
          </button>
        </div>
      </div>
    </div>
  );
};

// ── Loading spinner ──────────────────────────────────────────────
const LoadingView = () => (
  <div className="flex flex-col items-center justify-center py-32">
    <Loader2 size={36} className="text-blue-400 animate-spin mb-4" />
    <p className="text-slate-400">Generating question…</p>
  </div>
);

// ═══════════════════════════════════════════════════════════════════
//  Main page
// ═══════════════════════════════════════════════════════════════════
const JeeExamPage = () => {
  const { status, goToSelect } = useExamStore();

  useEffect(() => {
    // If user navigates here fresh, show the difficulty selector
    if (status === 'idle') goToSelect();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Minimal top bar */}
      <nav className="fixed top-0 inset-x-0 z-50 bg-slate-950/80 backdrop-blur-md border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-blue-600/20 rounded-lg flex items-center justify-center">
              <span className="text-blue-400 font-bold text-sm">S</span>
            </div>
            <span className="text-lg font-bold text-white">
              <span className="text-blue-400">Solv</span>era
            </span>
            <span className="ml-2 text-xs text-slate-500">/ JEE Exam Mode</span>
          </div>
        </div>
      </nav>

      <main className="pt-24 pb-16 px-6">
        {status === 'selecting' && <DifficultySelector />}
        {status === 'loading' && <LoadingView />}
        {status === 'question' && <QuestionCard />}
        {status === 'submitting' && <QuestionCard />}
        {status === 'result' && <ResultCard />}
        {status === 'ended' && <ScoreCard />}
      </main>
    </div>
  );
};

export default JeeExamPage;
