import { create } from 'zustand';
import api from '../api/axiosInstance';

const useExamStore = create((set, get) => ({
  // Session state
  sessionId: null,
  difficulty: null,
  status: 'idle', // idle | selecting | loading | question | submitting | result | ended
  error: null,

  // Current question
  question: null,
  questionNumber: 0,
  topic: '',
  questionStartTime: null,
  elapsedSeconds: 0,

  // Result of last submission
  lastResult: null,

  // Cumulative stats
  score: 0,
  correctCount: 0,
  totalAttempted: 0,
  accuracyPercent: 0,
  totalTimeSeconds: 0,
  weakTopics: [],
  attemptHistory: [],

  // ── Actions ────────────────────────────────────────

  startExam: async (level) => {
    set({ status: 'loading', error: null, difficulty: level });
    try {
      const res = await api.post('/exam/start', { level });
      const d = res.data;
      set({
        sessionId: d.session_id,
        question: d.question,
        questionNumber: d.question_number,
        topic: d.topic,
        score: d.score,
        correctCount: d.correct_count,
        totalAttempted: 0,
        status: 'question',
        questionStartTime: Date.now(),
        lastResult: null,
        elapsedSeconds: 0,
        attemptHistory: [],
      });
    } catch (err) {
      set({
        status: 'selecting',
        error: err.response?.data?.detail || 'Failed to start exam',
      });
    }
  },

  submitAnswer: async (answer) => {
    const { sessionId, question, topic, questionNumber } = get();
    if (!sessionId) return;
    set({ status: 'submitting', error: null });
    try {
      const res = await api.post('/exam/submit', {
        session_id: sessionId,
        answer,
      });
      const d = res.data;
      set((state) => ({
        lastResult: d,
        score: d.score,
        correctCount: d.correct_count,
        totalAttempted: d.total_attempted,
        accuracyPercent: d.accuracy_percent,
        status: 'result',
        attemptHistory: [
          ...state.attemptHistory,
          {
            questionNumber,
            question,
            topic,
            userAnswer: answer,
            correctAnswer: d.correct_answer,
            isCorrect: d.is_correct,
            timeTakenSeconds: d.time_taken_seconds,
            solution: d.solution,
          },
        ],
      }));
    } catch (err) {
      set({
        status: 'question',
        error: err.response?.data?.detail || 'Failed to submit answer',
      });
    }
  },

  nextQuestion: async () => {
    const { sessionId } = get();
    if (!sessionId) return;
    set({ status: 'loading', error: null });
    try {
      const res = await api.post('/exam/next', { session_id: sessionId });
      const d = res.data;
      set({
        question: d.question,
        questionNumber: d.question_number,
        topic: d.topic,
        score: d.score,
        correctCount: d.correct_count,
        status: 'question',
        questionStartTime: Date.now(),
        lastResult: null,
        elapsedSeconds: 0,
      });
    } catch (err) {
      set({
        status: 'result',
        error: err.response?.data?.detail || 'No more questions available',
      });
    }
  },

  endExam: async () => {
    const { sessionId } = get();
    if (!sessionId) {
      set({ status: 'idle' });
      return;
    }
    try {
      const res = await api.post(`/exam/end/${sessionId}`);
      const d = res.data;
      set({
        status: 'ended',
        score: d.score,
        correctCount: d.correct_count,
        totalAttempted: d.total_attempted,
        accuracyPercent: d.accuracy_percent,
        totalTimeSeconds: d.total_time_seconds,
        weakTopics: d.weak_topics || [],
      });
    } catch {
      set({ status: 'idle' });
    }
  },

  resetExam: () => {
    set({
      sessionId: null,
      difficulty: null,
      status: 'idle',
      error: null,
      question: null,
      questionNumber: 0,
      topic: '',
      questionStartTime: null,
      elapsedSeconds: 0,
      lastResult: null,
      score: 0,
      correctCount: 0,
      totalAttempted: 0,
      accuracyPercent: 0,
      totalTimeSeconds: 0,
      weakTopics: [],
      attemptHistory: [],
    });
  },

  setElapsed: (seconds) => set({ elapsedSeconds: seconds }),

  goToSelect: () => set({ status: 'selecting', error: null }),
}));

export default useExamStore;
