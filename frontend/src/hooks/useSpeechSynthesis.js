import { useState, useEffect, useRef, useCallback } from 'react';
import { cleanMathText, splitIntoSteps } from '../utils/cleanMathText';
import api from '../api/axiosInstance';

/**
 * useSpeechSynthesis — custom hook for AI-powered voice explanation.
 *
 * Uses backend neural TTS (Microsoft Edge / gTTS) as primary engine.
 * Falls back to browser Web Speech API if the backend is unavailable.
 *
 * Provides:
 *   play / pause / resume / stop controls
 *   currentStepIndex   (for UI highlighting)
 *   status: 'idle' | 'loading' | 'speaking' | 'paused'
 *   progress            0–100 audio progress
 *   voiceEngine         'neural' | 'browser' | null
 *   isSupported          always true (browser fallback exists)
 */
const useSpeechSynthesis = () => {
  const [status, setStatus] = useState('idle');
  const [currentStepIndex, setCurrentStepIndex] = useState(-1);
  const [progress, setProgress] = useState(0);
  const [voiceEngine, setVoiceEngine] = useState(null);
  const [steps, setSteps] = useState([]);
  const isSupported = true; // always true — we have browser fallback

  const audioRef = useRef(null);
  const stepsRef = useRef([]);
  const cancelledRef = useRef(false);
  const utteranceRef = useRef(null);

  // ── Cleanup on unmount ────────────────────────────────
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.removeAttribute('src');
        audioRef.current = null;
      }
      window.speechSynthesis?.cancel();
    };
  }, []);

  // ── Estimate which step is active based on audio progress ──
  const updateStepFromProgress = useCallback((currentTime, duration) => {
    const totalSteps = stepsRef.current.length;
    if (totalSteps === 0 || duration === 0) return;

    const pct = currentTime / duration;
    const stepIdx = Math.min(Math.floor(pct * totalSteps), totalSteps - 1);
    setCurrentStepIndex(stepIdx);
    setProgress(Math.round(pct * 100));
  }, []);

  // ── Neural TTS via backend API ────────────────────────
  const playNeural = useCallback(async (solutionText, questionText) => {
    setStatus('loading');
    setVoiceEngine('neural');

    try {
      const { data } = await api.post('/tts/explain', {
        solution: solutionText,
        question: questionText || null,
      });

      if (!data.success || !data.audio_url) {
        throw new Error(data.error || 'TTS generation failed');
      }

      // Build full URL for the audio file
      const API_BASE = import.meta.env.VITE_API_URL || '';
      const audioUrl = `${API_BASE}${data.audio_url}`;

      const audio = new Audio(audioUrl);
      audioRef.current = audio;
      stepsRef.current = data.steps || [];
      setSteps(data.steps || []);

      audio.ontimeupdate = () => {
        if (audio.duration) {
          updateStepFromProgress(audio.currentTime, audio.duration);
        }
      };

      audio.onended = () => {
        setStatus('idle');
        setCurrentStepIndex(-1);
        setProgress(0);
      };

      audio.onerror = () => {
        console.warn('Audio playback failed, falling back to browser TTS');
        playBrowser(solutionText);
      };

      await audio.play();
      setStatus('speaking');
      return true;
    } catch (err) {
      console.warn('Neural TTS failed, falling back to browser:', err.message);
      return false;
    }
  }, [updateStepFromProgress]);

  // ── Browser fallback (Web Speech API) ─────────────────
  const speakTextBrowser = useCallback((text) => {
    return new Promise((resolve) => {
      if (!('speechSynthesis' in window)) { resolve(); return; }

      const utt = new SpeechSynthesisUtterance(text);
      utt.rate = 0.9;
      utt.pitch = 1;
      utt.lang = 'en-IN';

      utt.onend = () => resolve();
      utt.onerror = () => resolve();

      utteranceRef.current = utt;
      window.speechSynthesis.speak(utt);
    });
  }, []);

  const playBrowser = useCallback(async (solutionText) => {
    setVoiceEngine('browser');
    setStatus('speaking');
    cancelledRef.current = false;

    const parsed = splitIntoSteps(solutionText);
    stepsRef.current = parsed;
    setSteps(parsed);

    for (let i = 0; i < parsed.length; i++) {
      if (cancelledRef.current) break;

      setCurrentStepIndex(i);
      setProgress(Math.round(((i + 1) / parsed.length) * 100));

      const speech = cleanMathText(
        `Step ${parsed[i].index}: ${parsed[i].title}. ${parsed[i].body}`
      );
      await speakTextBrowser(speech);

      if (i < parsed.length - 1 && !cancelledRef.current) {
        await new Promise((r) => setTimeout(r, 1200));
      }
    }

    if (!cancelledRef.current) {
      setStatus('idle');
      setCurrentStepIndex(-1);
      setProgress(0);
    }
  }, [speakTextBrowser]);

  // ── Public: PLAY ──────────────────────────────────────
  const play = useCallback(async (solutionText, questionText) => {
    if (!solutionText) return;

    // Stop anything currently playing
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.removeAttribute('src');
      audioRef.current = null;
    }
    window.speechSynthesis?.cancel();
    cancelledRef.current = false;

    // Try neural TTS first, fall back to browser
    const ok = await playNeural(solutionText, questionText);
    if (!ok) {
      await playBrowser(solutionText);
    }
  }, [playNeural, playBrowser]);

  // ── Public: PAUSE ─────────────────────────────────────
  const pause = useCallback(() => {
    if (voiceEngine === 'neural' && audioRef.current) {
      audioRef.current.pause();
    } else {
      window.speechSynthesis?.pause();
    }
    setStatus('paused');
  }, [voiceEngine]);

  // ── Public: RESUME ────────────────────────────────────
  const resume = useCallback(() => {
    if (voiceEngine === 'neural' && audioRef.current) {
      audioRef.current.play();
    } else {
      window.speechSynthesis?.resume();
    }
    setStatus('speaking');
  }, [voiceEngine]);

  // ── Public: STOP ──────────────────────────────────────
  const stop = useCallback(() => {
    cancelledRef.current = true;

    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.removeAttribute('src');
      audioRef.current = null;
    }
    window.speechSynthesis?.cancel();

    setStatus('idle');
    setCurrentStepIndex(-1);
    setProgress(0);
  }, []);

  return {
    play,
    pause,
    resume,
    stop,
    status,
    currentStepIndex,
    progress,
    voiceEngine,
    steps,
    isSupported,
  };
};

export default useSpeechSynthesis;
