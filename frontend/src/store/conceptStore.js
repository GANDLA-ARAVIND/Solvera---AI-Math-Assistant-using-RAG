import { create } from 'zustand';
import api from '../api/axiosInstance';

const useConceptStore = create((set, get) => ({
  // Navigation state
  status: 'idle', // idle | topics | loading | explanation | formulas | example | practice | evaluating | result | bundle
  error: null,

  // Topic selection
  topics: {},
  selectedTopic: null,
  selectedSubtopic: null,

  // Content
  explanation: null,
  formulas: null,
  example: null,
  plotUrl: null,

  // Bundle (single-call /concept-mode)
  bundle: null,

  // Practice
  practiceQuestion: null,
  practiceHint: null,
  practiceSessionId: null,
  practiceResult: null,

  // Concept Assistant chat
  assistantOpen: false,
  assistantMessages: [],  // { role: 'user'|'assistant', content: string, data?: object }
  assistantLoading: false,

  // ── Actions ────────────────────────────────────────

  fetchTopics: async () => {
    set({ status: 'loading', error: null });
    try {
      const res = await api.get('/concept-mode/topics');
      set({ topics: res.data, status: 'topics' });
    } catch (err) {
      set({ status: 'idle', error: err.response?.data?.detail || 'Failed to load topics' });
    }
  },

  selectTopic: (topic) => {
    set({ selectedTopic: topic, selectedSubtopic: null });
  },

  selectSubtopic: (subtopic) => {
    set({ selectedSubtopic: subtopic });
  },

  // ── Single-call concept bundle (POST /concept-mode) ────────
  fetchBundle: async (topicOverride) => {
    const { selectedTopic } = get();
    const topic = topicOverride || selectedTopic;
    if (!topic) return;
    set({ status: 'loading', error: null, bundle: null });
    try {
      const res = await api.post('/concept-mode', { topic });
      set({ bundle: res.data, status: 'bundle' });
    } catch (err) {
      set({ status: 'topics', error: err.response?.data?.detail || 'Failed to load concept' });
    }
  },

  // ── Subtopic-level actions ─────────────────────────────────

  fetchExplanation: async () => {
    const { selectedTopic, selectedSubtopic } = get();
    if (!selectedTopic || !selectedSubtopic) return;
    set({ status: 'loading', error: null, explanation: null });
    try {
      const res = await api.post('/concept-mode/explain', {
        topic: selectedTopic,
        subtopic: selectedSubtopic,
      });
      set({ explanation: res.data.explanation, status: 'explanation' });
    } catch (err) {
      set({ status: 'topics', error: err.response?.data?.detail || 'Failed to load explanation' });
    }
  },

  fetchFormulas: async () => {
    const { selectedTopic, selectedSubtopic } = get();
    if (!selectedTopic || !selectedSubtopic) return;
    set({ status: 'loading', error: null, formulas: null });
    try {
      const res = await api.post('/concept-mode/formula', {
        topic: selectedTopic,
        subtopic: selectedSubtopic,
      });
      set({ formulas: res.data.formulas, status: 'formulas' });
    } catch (err) {
      set({ status: 'topics', error: err.response?.data?.detail || 'Failed to load formulas' });
    }
  },

  fetchExample: async () => {
    const { selectedTopic, selectedSubtopic } = get();
    if (!selectedTopic || !selectedSubtopic) return;
    set({ status: 'loading', error: null, example: null, plotUrl: null });
    try {
      const res = await api.post('/concept-mode/example', {
        topic: selectedTopic,
        subtopic: selectedSubtopic,
      });
      set({
        example: res.data.example,
        plotUrl: res.data.plot_url || null,
        status: 'example',
      });
    } catch (err) {
      set({ status: 'topics', error: err.response?.data?.detail || 'Failed to load example' });
    }
  },

  fetchPractice: async () => {
    const { selectedTopic, selectedSubtopic } = get();
    if (!selectedTopic || !selectedSubtopic) return;
    set({ status: 'loading', error: null, practiceQuestion: null, practiceResult: null, practiceHint: null, practiceSessionId: null });
    try {
      const res = await api.post('/concept-mode/practice', {
        topic: selectedTopic,
        subtopic: selectedSubtopic,
      });
      set({
        practiceQuestion: res.data.question,
        practiceHint: res.data.hint,
        practiceSessionId: res.data.session_id,
        status: 'practice',
      });
    } catch (err) {
      set({ status: 'topics', error: err.response?.data?.detail || 'Failed to generate question' });
    }
  },

  submitPracticeAnswer: async (answer) => {
    const { practiceSessionId } = get();
    if (!practiceSessionId) return;
    set({ status: 'evaluating', error: null });
    try {
      const res = await api.post('/concept-mode/evaluate', {
        session_id: practiceSessionId,
        answer,
      });
      set({ practiceResult: res.data, status: 'result' });
    } catch (err) {
      set({ status: 'practice', error: err.response?.data?.detail || 'Failed to evaluate answer' });
    }
  },

  // ── Concept Assistant (chat panel) ─────────────────────────

  toggleAssistant: () => {
    set((s) => ({ assistantOpen: !s.assistantOpen }));
  },

  openAssistant: () => set({ assistantOpen: true }),
  closeAssistant: () => set({ assistantOpen: false }),

  sendAssistantMessage: async (question) => {
    const { assistantMessages } = get();
    const newMessages = [...assistantMessages, { role: 'user', content: question }];
    set({ assistantMessages: newMessages, assistantLoading: true });
    try {
      const res = await api.post('/concept-assistant', { question });
      const data = res.data;
      set({
        assistantMessages: [...newMessages, { role: 'assistant', content: data.answer || '', data }],
        assistantLoading: false,
      });
    } catch (err) {
      set({
        assistantMessages: [
          ...newMessages,
          { role: 'assistant', content: 'Sorry, I could not process your question. Please try again.', data: null },
        ],
        assistantLoading: false,
      });
    }
  },

  clearAssistantMessages: () => set({ assistantMessages: [] }),

  // ── Navigation helpers ─────────────────────────────────────

  goToTopics: () => {
    set({
      status: 'topics',
      error: null,
      explanation: null,
      formulas: null,
      example: null,
      plotUrl: null,
      bundle: null,
      practiceQuestion: null,
      practiceResult: null,
      practiceHint: null,
      practiceSessionId: null,
    });
  },

  resetConcept: () => {
    set({
      status: 'idle',
      error: null,
      topics: {},
      selectedTopic: null,
      selectedSubtopic: null,
      explanation: null,
      formulas: null,
      example: null,
      plotUrl: null,
      bundle: null,
      practiceQuestion: null,
      practiceHint: null,
      practiceSessionId: null,
      practiceResult: null,
      assistantOpen: false,
      assistantMessages: [],
      assistantLoading: false,
    });
  },
}));

export default useConceptStore;
