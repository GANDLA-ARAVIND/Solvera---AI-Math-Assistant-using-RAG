import { create } from 'zustand';
import api from '../api/axiosInstance';

const useHistoryStore = create((set) => ({
  entries: [],
  selectedEntry: null,
  loading: false,

  fetchHistory: async () => {
    set({ loading: true });
    try {
      const res = await api.get('/history/');
      set({ entries: res.data, loading: false });
    } catch {
      set({ loading: false });
    }
  },

  fetchDetail: async (id) => {
    set({ loading: true });
    try {
      const res = await api.get(`/history/${id}`);
      set({ selectedEntry: res.data, loading: false });
    } catch {
      set({ loading: false });
    }
  },

  deleteEntry: async (id) => {
    try {
      await api.delete(`/history/${id}`);
      set((s) => ({
        entries: s.entries.filter((e) => e.id !== id),
        selectedEntry: s.selectedEntry?.id === id ? null : s.selectedEntry,
      }));
    } catch {
      // ignore
    }
  },

  clearSelected: () => set({ selectedEntry: null }),
}));

export default useHistoryStore;
