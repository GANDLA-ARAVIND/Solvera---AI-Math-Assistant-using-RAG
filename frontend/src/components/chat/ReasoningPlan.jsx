import { useState } from 'react';
import { Brain, ChevronDown, ChevronUp } from 'lucide-react';

const stepColors = [
  'reasoning-step--blue',
  'reasoning-step--purple',
  'reasoning-step--cyan',
  'reasoning-step--amber',
  'reasoning-step--emerald',
  'reasoning-step--rose',
];

const ReasoningPlan = ({ steps, mathType }) => {
  const [expanded, setExpanded] = useState(false);

  if (!steps || steps.length === 0) return null;

  return (
    <div className="reasoning-plan mb-3">
      <button
        onClick={() => setExpanded(!expanded)}
        className="reasoning-plan-toggle"
      >
        <div className="flex items-center gap-2">
          <Brain size={14} className="reasoning-plan-icon" />
          <span className="text-xs font-semibold uppercase tracking-wider">
            Agent Reasoning Plan
          </span>
          {mathType && (
            <span className="reasoning-plan-type">
              {mathType.replace(/_/g, ' ')}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1 text-xs opacity-70">
          <span>{steps.length} steps</span>
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>
      </button>

      {expanded && (
        <div className="reasoning-plan-steps">
          {steps.map((s, i) => (
            <div
              key={s.step || i}
              className={`reasoning-step ${stepColors[i % stepColors.length]}`}
              style={{ animationDelay: `${i * 0.08}s` }}
            >
              <div className="reasoning-step-number">
                {s.step || i + 1}
              </div>
              <div className="reasoning-step-content">
                <div className="reasoning-step-title">{s.title}</div>
                {s.description && (
                  <div className="reasoning-step-desc">{s.description}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ReasoningPlan;
