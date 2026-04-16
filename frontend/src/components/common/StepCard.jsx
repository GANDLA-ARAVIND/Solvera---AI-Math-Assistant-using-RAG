import MathRenderer from '../chat/MathRenderer';
import { CheckCircle } from 'lucide-react';

const stepBorderColors = [
  'border-l-blue-500',
  'border-l-purple-500',
  'border-l-cyan-500',
  'border-l-amber-500',
  'border-l-emerald-500',
  'border-l-rose-500',
  'border-l-indigo-500',
  'border-l-teal-500',
];

const StepCard = ({ index, title, body, isFinal = false }) => {
  const borderColor = isFinal
    ? 'border-l-emerald-400'
    : stepBorderColors[index % stepBorderColors.length];

  return (
    <div
      className={`step-card ${isFinal ? 'step-card--final' : ''}`}
      style={{ animationDelay: `${index * 0.12}s` }}
    >
      <div className={`step-card-inner border-l-4 ${borderColor} rounded-xl px-4 py-3`}>
        {/* Step header */}
        <div className="flex items-center gap-2 mb-1.5">
          <span className={`step-number ${isFinal ? 'step-number--final' : ''}`}>
            {isFinal ? <CheckCircle size={12} /> : index + 1}
          </span>
          <span className={`text-xs font-semibold uppercase tracking-wide ${isFinal ? 'step-title--final' : 'step-title'}`}>
            {title}
          </span>
        </div>
        {/* Step body */}
        {body && (
          <div className={`ml-7 text-sm leading-relaxed ${isFinal ? 'step-body--final' : 'step-body'}`}>
            <MathRenderer content={body} />
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Parse markdown content looking for step patterns and render as cards.
 * Falls back to rendering the raw content if no steps are detected.
 */
const parseSteps = (content) => {
  if (!content) return null;

  // Match patterns like "Step 1:", "**Step 1:**", "### Step 1:", "1.", "1)"
  const stepRegex = /(?:^|\n)\s*(?:#{1,4}\s*)?(?:\*{0,2})\s*(?:step\s*(\d+)|(\d+)[.)]\s)[\s:.\-–—]*(?:\*{0,2})\s*(.*?)(?=\n\s*(?:#{1,4}\s*)?(?:\*{0,2})\s*(?:step\s*\d+|\d+[.)]\s)|$)/gis;

  // Also match "Final Answer" / "Answer" / "Result"
  const finalRegex = /(?:^|\n)\s*(?:#{1,4}\s*)?(?:\*{0,2})\s*(?:final\s*answer|answer|result|solution)[\s:.\-–—]*(?:\*{0,2})\s*([\s\S]*?)$/i;

  const steps = [];
  let lastIndex = 0;
  let match;

  // Extract numbered steps
  const contentNormalized = content + '\n';
  const lines = content.split('\n');

  // Simple approach: find lines that look like step headers
  let currentStep = null;
  const stepHeaderPattern = /^\s*(?:#{1,4}\s*)?(?:\*{0,2})\s*(?:step\s*(\d+)|(\d+)[.)]\s)[\s:.\-–—]*(?:\*{0,2})\s*(.*)/i;
  const finalPattern = /^\s*(?:#{1,4}\s*)?(?:\*{0,2})\s*(?:final\s*answer|answer|result|solution)[\s:.\-–—]*(?:\*{0,2})\s*(.*)/i;

  for (let i = 0; i < lines.length; i++) {
    const stepMatch = lines[i].match(stepHeaderPattern);
    const finalMatch = lines[i].match(finalPattern);

    if (stepMatch) {
      if (currentStep) {
        steps.push(currentStep);
      }
      currentStep = {
        title: stepMatch[3] || `Step ${stepMatch[1] || stepMatch[2]}`,
        body: '',
        isFinal: false,
      };
    } else if (finalMatch) {
      if (currentStep) {
        steps.push(currentStep);
      }
      currentStep = {
        title: 'Final Answer',
        body: finalMatch[1] || '',
        isFinal: true,
      };
    } else if (currentStep) {
      currentStep.body += (currentStep.body ? '\n' : '') + lines[i];
    }
  }

  if (currentStep) {
    steps.push(currentStep);
  }

  // Clean up step bodies
  steps.forEach((s) => {
    s.body = s.body.trim();
  });

  return steps.length >= 2 ? steps : null;
};

const StepCardList = ({ content }) => {
  const steps = parseSteps(content);

  if (!steps) return null;

  return (
    <div className="step-card-list space-y-2 my-2">
      {steps.map((step, i) => (
        <StepCard
          key={i}
          index={i}
          title={step.title}
          body={step.body}
          isFinal={step.isFinal}
        />
      ))}
    </div>
  );
};

export { StepCard, StepCardList, parseSteps };
export default StepCardList;
