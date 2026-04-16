import { create } from 'zustand';
import api from '../api/axiosInstance';

const useAuthStore = create((set) => ({
  user: null,
  token: localStorage.getItem('solvera_token'),
  isAuthenticated: !!localStorage.getItem('solvera_token'),
  loading: false,
  error: null,

  login: async (email, password) => {
    set({ loading: true, error: null });
    try {
      const res = await api.post('/auth/login', { email, password });
      localStorage.setItem('solvera_token', res.data.token);
      set({
        user: res.data.user,
        token: res.data.token,
        isAuthenticated: true,
        loading: false,
      });
    } catch (err) {
      set({
        loading: false,
        error: err.response?.data?.detail || 'Login failed',
      });
      throw err;
    }
  },

  signup: async (username, email, password) => {
    set({ loading: true, error: null });
    try {
      const res = await api.post('/auth/signup', { username, email, password });
      localStorage.setItem('solvera_token', res.data.token);
      set({
        user: res.data.user,
        token: res.data.token,
        isAuthenticated: true,
        loading: false,
      });
    } catch (err) {
      set({
        loading: false,
        error: err.response?.data?.detail || 'Signup failed',
      });
      throw err;
    }
  },

  logout: () => {
    localStorage.removeItem('solvera_token');
    set({ user: null, token: null, isAuthenticated: false });
  },

  fetchUser: async () => {
    try {
      const res = await api.get('/auth/me');
      set({ user: res.data, isAuthenticated: true });
    } catch {
      localStorage.removeItem('solvera_token');
      set({ user: null, isAuthenticated: false, token: null });
    }
  },

  clearError: () => set({ error: null }),
}));

export default useAuthStore;
