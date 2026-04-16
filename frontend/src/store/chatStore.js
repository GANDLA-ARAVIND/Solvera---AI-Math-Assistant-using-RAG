import { create } from 'zustand';
import api from '../api/axiosInstance';

const useChatStore = create((set, get) => ({
  messages: [],
  isLoading: false,
  currentTopic: null,
  pdfContext: null,   // stored PDF text from backend
  pdfFileName: null,  // name of the uploaded PDF

  sendQuery: async (query) => {
    // If a PDF is loaded, route to PDF Q&A instead
    if (get().pdfContext) {
      return get().askPdfQuestion(query);
    }
    const userMsg = {
      role: 'user',
      content: query,
      timestamp: new Date().toISOString(),
    };
    set((s) => ({ messages: [...s.messages, userMsg], isLoading: true }));

    try {
      // Build conversation history from recent messages for multi-turn context
      const recentMessages = get()
        .messages.filter((m) => !m.isError && !m.isNonMath)
        .slice(-6)
        .map((m) => ({
          role: m.role,
          content:
            m.role === 'assistant' && m.content.length > 500
              ? m.content.slice(0, 500) + '...'
              : m.content,
        }));

      const res = await api.post('/solve/', {
        query,
        conversation_history:
          recentMessages.length > 0 ? recentMessages : undefined,
      });
      const data = res.data;

      if (!data.success) {
        const errMsg = {
          role: 'assistant',
          content: data.message || 'Could not process your query.',
          isError: !data.error?.includes('non_math'),
          isNonMath: data.error === 'non_math_query',
          timestamp: new Date().toISOString(),
        };
        set((s) => ({ messages: [...s.messages, errMsg], isLoading: false }));
        return;
      }

      const assistantMsg = {
        role: 'assistant',
        content: data.solution,
        metadata: {
          query: query,
          topic: data.topic,
          difficulty: data.difficulty,
          validation: data.validation,
          rag_sources: data.rag_sources,
          history_id: data.history_id,
          plot_url: data.plot_url,
          follow_up_suggestions: data.follow_up_suggestions,
          reasoning_plan: data.reasoning_plan,
          math_type: data.math_type,
        },
        timestamp: new Date().toISOString(),
      };
      set((s) => ({
        messages: [...s.messages, assistantMsg],
        isLoading: false,
        currentTopic: data.topic,
      }));
    } catch (err) {
      const message =
        err.response?.status === 429
          ? 'Too many requests. Please wait a moment and try again.'
          : 'Something went wrong. Please try again.';
      const errMsg = {
        role: 'assistant',
        content: message,
        isError: true,
        timestamp: new Date().toISOString(),
      };
      set((s) => ({ messages: [...s.messages, errMsg], isLoading: false }));
    }
  },

  sendImage: async (file) => {
    const userMsg = {
      role: 'user',
      content: 'Uploaded an image for math extraction',
      imagePreview: URL.createObjectURL(file),
      timestamp: new Date().toISOString(),
    };
    set((s) => ({ messages: [...s.messages, userMsg], isLoading: true }));

    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await api.post('/ocr/solve', formData);

      const extraction = res.data.extraction || res.data;
      const solution = res.data.solution;

      if (!extraction?.success) {
        const detail = extraction?.error_detail
          ? `\n\nDetails: ${extraction.error_detail}`
          : '';
        const errMsg = {
          role: 'assistant',
          content:
            (extraction?.message ||
              'Failed to process the image. Please try again with a clearer photo.') +
            detail,
          isError: true,
          timestamp: new Date().toISOString(),
        };
        set((s) => ({ messages: [...s.messages, errMsg], isLoading: false }));
        return;
      }

      // Show extraction result
      const extractMsg = {
        role: 'assistant',
        content: `**Extracted from image:**\n\n${extraction.extracted_text}`,
        isExtraction: true,
        timestamp: new Date().toISOString(),
      };

      const messages = [extractMsg];

      // Show solution if successful
      if (solution?.success) {
        messages.push({
          role: 'assistant',
          content: solution.solution,
          metadata: {
            topic: solution.topic,
            difficulty: solution.difficulty,
            validation: solution.validation,
            rag_sources: solution.rag_sources,
            history_id: solution.history_id,
            plot_url: solution.plot_url,
            follow_up_suggestions: solution.follow_up_suggestions,
          },
          timestamp: new Date().toISOString(),
        });
      } else if (solution?.message) {
        messages.push({
          role: 'assistant',
          content: solution.message,
          isNonMath: solution.error === 'non_math_query',
          timestamp: new Date().toISOString(),
        });
      }

      set((s) => ({
        messages: [...s.messages, ...messages],
        isLoading: false,
      }));
    } catch (err) {
      const errMsg = {
        role: 'assistant',
        content:
          'Failed to process the image. Please try again with a clearer photo.',
        isError: true,
        timestamp: new Date().toISOString(),
      };
      set((s) => ({ messages: [...s.messages, errMsg], isLoading: false }));
    }
  },

  clearChat: () => set({ messages: [], currentTopic: null, pdfContext: null, pdfFileName: null }),

  // ── PDF Upload & Q&A ─────────────────────────────────────────────
  sendPdf: async (file) => {
    const userMsg = {
      role: 'user',
      content: `📄 Uploaded PDF: **${file.name}**`,
      isPdf: true,
      timestamp: new Date().toISOString(),
    };
    set((s) => ({ messages: [...s.messages, userMsg], isLoading: true }));

    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await api.post('/pdf/upload', formData);
      const data = res.data;

      if (!data.success) {
        const errMsg = {
          role: 'assistant',
          content: data.detail || 'Failed to process the PDF.',
          isError: true,
          timestamp: new Date().toISOString(),
        };
        set((s) => ({ messages: [...s.messages, errMsg], isLoading: false }));
        return;
      }

      // Store PDF context for follow-up Q&A
      set({ pdfContext: true, pdfFileName: file.name });

      const analysisMsg = {
        role: 'assistant',
        content: data.analysis,
        isPdfAnalysis: true,
        metadata: {
          filename: data.filename,
          pages: data.pages,
        },
        timestamp: new Date().toISOString(),
      };
      set((s) => ({ messages: [...s.messages, analysisMsg], isLoading: false }));
    } catch (err) {
      const message =
        err.response?.data?.detail ||
        'Failed to process the PDF. Please try again.';
      const errMsg = {
        role: 'assistant',
        content: message,
        isError: true,
        timestamp: new Date().toISOString(),
      };
      set((s) => ({ messages: [...s.messages, errMsg], isLoading: false }));
    }
  },

  askPdfQuestion: async (question) => {
    const userMsg = {
      role: 'user',
      content: question,
      timestamp: new Date().toISOString(),
    };
    set((s) => ({ messages: [...s.messages, userMsg], isLoading: true }));

    try {
      // Build conversation history for multi-turn PDF Q&A
      const history = get()
        .messages.filter((m) => !m.isError)
        .slice(-8)
        .map((m) => ({
          role: m.role,
          content:
            m.content.length > 500 ? m.content.slice(0, 500) + '...' : m.content,
        }));

      const res = await api.post('/pdf/ask', {
        question,
        conversation_history: history.length > 0 ? history : undefined,
      });
      const data = res.data;

      if (!data.success) {
        const errMsg = {
          role: 'assistant',
          content: data.message || 'Could not answer the question.',
          isError: true,
          timestamp: new Date().toISOString(),
        };
        set((s) => ({ messages: [...s.messages, errMsg], isLoading: false }));
        return;
      }

      const answerMsg = {
        role: 'assistant',
        content: data.answer,
        isPdfAnswer: true,
        timestamp: new Date().toISOString(),
      };
      set((s) => ({ messages: [...s.messages, answerMsg], isLoading: false }));
    } catch (err) {
      const message =
        err.response?.data?.detail ||
        'Failed to answer. Please try again.';
      const errMsg = {
        role: 'assistant',
        content: message,
        isError: true,
        timestamp: new Date().toISOString(),
      };
      set((s) => ({ messages: [...s.messages, errMsg], isLoading: false }));
    }
  },

  clearPdf: async () => {
    try {
      await api.delete('/pdf/clear');
    } catch (_) {
      // ignore
    }
    set({ pdfContext: null, pdfFileName: null });
  },
}));

export default useChatStore;
