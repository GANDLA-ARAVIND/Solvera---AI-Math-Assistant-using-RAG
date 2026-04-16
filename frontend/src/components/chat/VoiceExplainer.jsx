import { useMemo } from 'react';
import useSpeechSynthesis from '../../hooks/useSpeechSynthesis';
import { splitIntoSteps } from '../../utils/cleanMathText';
import MathRenderer from './MathRenderer';
import { Volume2, Pause, Play, Square, Loader2, Mic } from 'lucide-react';

/**
 * VoiceExplainer — renders AI voice controls + step highlighting beneath a solution.
 *
 * Uses neural TTS (backend edge-tts) with automatic browser fallback.
 *
 * Props:
 *   solution  (string)  — the full markdown solution text
 *   question  (string)  — the original user question
 */
const VoiceExplainer = ({ solution, question }) => {
  const {
    play, pause, resume, stop,
    status, currentStepIndex, progress, voiceEngine, steps: hookSteps, isSupported,
  } = useSpeechSynthesis();

  const localSteps = useMemo(() => splitIntoSteps(solution || ''), [solution]);
  const steps = hookSteps.length > 0 ? hookSteps : localSteps;

  if (!isSupported || !solution) return null;

  const handlePlay = () => play(solution, question);

  const engineLabel = voiceEngine === 'neural' ? 'AI Voice' : voiceEngine === 'browser' ? 'Browser' : '';

  return (
    <div className="voice-explainer mt-3 pt-3 border-t border-slate-700/50">
      {/* ── Control bar ──────────────────────────────── */}
      <div className="flex items-center gap-2 mb-3">
        {status === 'idle' && (
          <button
            onClick={handlePlay}
            className="voice-btn voice-btn--play"
            title="Explain in AI voice"
          >
            <Volume2 size={14} />
            <span>AI Voice Explain</span>
          </button>
        )}

        {status === 'loading' && (
          <button
            className="voice-btn voice-btn--loading"
            disabled
            title="Generating audio…"
          >
            <Loader2 size={14} className="animate-spin" />
            <span>Generating…</span>
          </button>
        )}

        {status === 'speaking' && (
          <>
            <button
              onClick={pause}
              className="voice-btn voice-btn--pause"
              title="Pause"
            >
              <Pause size={14} />
              <span>Pause</span>
            </button>
            <button
              onClick={stop}
              className="voice-btn voice-btn--stop"
              title="Stop"
            >
              <Square size={14} />
              <span>Stop</span>
            </button>
          </>
        )}

        {status === 'paused' && (
          <>
            <button
              onClick={resume}
              className="voice-btn voice-btn--play"
              title="Resume"
            >
              <Play size={14} />
              <span>Resume</span>
            </button>
            <button
              onClick={stop}
              className="voice-btn voice-btn--stop"
              title="Stop"
            >
              <Square size={14} />
              <span>Stop</span>
            </button>
          </>
        )}

        {status !== 'idle' && status !== 'loading' && (
          <span className="text-xs text-slate-400 ml-2">
            Step {currentStepIndex + 1} / {steps.length}
          </span>
        )}

        {/* Voice engine badge */}
        {engineLabel && status !== 'idle' && (
          <span className="voice-engine-badge ml-auto">
            <Mic size={10} />
            {engineLabel}
          </span>
        )}
      </div>

      {/* ── Progress bar ─────────────────────────────── */}
      {(status === 'speaking' || status === 'paused') && (
        <div className="voice-progress-bar mb-3">
          <div className="voice-progress-fill" style={{ width: `${progress}%` }} />
        </div>
      )}

      {/* ── Step list with active highlight ───────────── */}
      {status !== 'idle' && status !== 'loading' && (
        <div className="voice-steps space-y-2">
          {steps.map((step, i) => {
            const isActive = i === currentStepIndex;
            const isDone = i < currentStepIndex;

            return (
              <div
                key={i}
                className={`voice-step rounded-lg px-3 py-2 text-sm transition-all duration-300 ${
                  isActive
                    ? 'voice-step--active'
                    : isDone
                      ? 'voice-step--done'
                      : 'voice-step--pending'
                }`}
              >
                <div className="font-semibold text-xs mb-0.5 flex items-center gap-2">
                  <span
                    className={`inline-flex items-center justify-center w-5 h-5 rounded-full text-[10px] font-bold ${
                      isActive
                        ? 'bg-blue-500 text-white'
                        : isDone
                          ? 'bg-emerald-600 text-white'
                          : 'bg-slate-600 text-slate-300'
                    }`}
                  >
                    {step.index}
                  </span>
                  <span className={isActive ? 'text-blue-300' : isDone ? 'text-emerald-400' : 'text-slate-400'}>
                    {step.title}
                  </span>
                </div>
                {isActive && step.body && (
                  <div className="mt-1 ml-7">
                    <MathRenderer content={step.body} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default VoiceExplainer;
