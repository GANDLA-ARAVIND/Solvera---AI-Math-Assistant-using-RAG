/**
 * cleanMathText — convert LaTeX / math symbols into speech-friendly text.
 *
 * Only math notation is affected; normal prose passes through unchanged.
 */

const SYMBOL_MAP = [
  // ── Greek letters ───────────────────────────────────────
  [/\\alpha/g, 'alpha'],
  [/\\beta/g, 'beta'],
  [/\\gamma/g, 'gamma'],
  [/\\delta/g, 'delta'],
  [/\\theta/g, 'theta'],
  [/\\pi/g, 'pi'],
  [/\\sigma/g, 'sigma'],
  [/\\mu/g, 'mu'],
  [/\\lambda/g, 'lambda'],
  [/\\epsilon/g, 'epsilon'],
  [/\\omega/g, 'omega'],
  [/\\phi/g, 'phi'],
  [/\\psi/g, 'psi'],
  [/\\rho/g, 'rho'],
  [/\\tau/g, 'tau'],

  // ── Operators & relations ───────────────────────────────
  [/\\infty/g, 'infinity'],
  [/\\pm/g, 'plus or minus'],
  [/\\mp/g, 'minus or plus'],
  [/\\times/g, 'times'],
  [/\\cdot/g, 'times'],
  [/\\div/g, 'divided by'],
  [/\\neq/g, 'not equal to'],
  [/\\leq/g, 'less than or equal to'],
  [/\\geq/g, 'greater than or equal to'],
  [/\\approx/g, 'approximately equal to'],
  [/\\equiv/g, 'is equivalent to'],
  [/\\rightarrow/g, 'approaches'],
  [/\\to/g, 'approaches'],
  [/\\implies/g, 'implies'],
  [/\\therefore/g, 'therefore'],

  // ── Calculus ────────────────────────────────────────────
  [/\\int_?\{([^}]*)\}\^\{([^}]*)\}/g, 'the integral from $1 to $2 of'],
  [/\\int/g, 'integral of'],
  [/∫/g, 'integral of'],
  [/\\sum_?\{([^}]*)\}\^\{([^}]*)\}/g, 'the sum from $1 to $2 of'],
  [/\\sum/g, 'summation of'],
  [/∑/g, 'summation of'],
  [/\\prod/g, 'product of'],
  [/∏/g, 'product of'],
  [/\\lim_?\{([^}]*)\}/g, 'the limit as $1 of'],
  [/\\lim/g, 'the limit of'],
  [/\\,dx/g, ' with respect to x'],
  [/\\,dy/g, ' with respect to y'],
  [/\\,dt/g, ' with respect to t'],
  [/\bdx\b/g, 'with respect to x'],
  [/\bdy\b/g, 'with respect to y'],
  [/\bdt\b/g, 'with respect to t'],

  // ── Fractions & roots ───────────────────────────────────
  [/\\frac\{([^}]*)\}\{([^}]*)\}/g, '$1 over $2'],
  [/\\sqrt\[(\d+)\]\{([^}]*)\}/g, 'the $1th root of $2'],
  [/\\sqrt\{([^}]*)\}/g, 'the square root of $1'],
  [/√/g, 'square root of'],

  // ── Powers (common ones first) ──────────────────────────
  [/\^{?\s*2\s*}?/g, ' squared'],
  [/\^{?\s*3\s*}?/g, ' cubed'],
  [/\^\{([^}]+)\}/g, ' to the power of $1'],
  [/\^(\w)/g, ' to the power of $1'],

  // ── Subscripts ──────────────────────────────────────────
  [/_\{([^}]+)\}/g, ' sub $1'],
  [/_(\w)/g, ' sub $1'],

  // ── Trig / log ─────────────────────────────────────────
  [/\\sin/g, 'sine'],
  [/\\cos/g, 'cosine'],
  [/\\tan/g, 'tangent'],
  [/\\cot/g, 'cotangent'],
  [/\\sec/g, 'secant'],
  [/\\csc/g, 'cosecant'],
  [/\\arcsin/g, 'arc sine'],
  [/\\arccos/g, 'arc cosine'],
  [/\\arctan/g, 'arc tangent'],
  [/\\ln/g, 'natural log of'],
  [/\\log/g, 'log of'],
  [/\\exp/g, 'e to the power of'],

  // ── Brackets ────────────────────────────────────────────
  [/\\left\(/g, '('],
  [/\\right\)/g, ')'],
  [/\\left\[/g, '['],
  [/\\right\]/g, ']'],
  [/\\left\\\{/g, '{'],
  [/\\right\\\}/g, '}'],
  [/\\left/g, ''],
  [/\\right/g, ''],

  // ── Misc LaTeX commands ─────────────────────────────────
  [/\\text\{([^}]*)\}/g, '$1'],
  [/\\mathrm\{([^}]*)\}/g, '$1'],
  [/\\mathbf\{([^}]*)\}/g, '$1'],
  [/\\[a-zA-Z]+/g, ''],       // strip remaining unknown commands
  [/\$\$/g, ''],               // display math delimiters
  [/\$/g, ''],                 // inline math delimiters
  [/\{/g, ''],
  [/\}/g, ''],
  [/\\\\/g, ' '],              // line breaks
];

/**
 * Convert a string containing LaTeX / math symbols into readable speech text.
 * Normal English prose passes through largely unchanged.
 */
export function cleanMathText(text) {
  if (!text) return '';

  let cleaned = text;

  // Apply every substitution in order
  for (const [pattern, replacement] of SYMBOL_MAP) {
    cleaned = cleaned.replace(pattern, replacement);
  }

  // Collapse multiple spaces / newlines
  cleaned = cleaned.replace(/\n+/g, '. ').replace(/\s{2,}/g, ' ').trim();
  return cleaned;
}

/**
 * Split a solution string into numbered step objects.
 *
 * Detects patterns like:
 *   **Step 1: …**   or   ## Step 1   or   Step 1:   or   **Step 1:**
 *
 * Returns: [{ index: 1, title: "Step 1: ...", body: "..." }, …]
 */
export function splitIntoSteps(solution) {
  if (!solution) return [];

  // Match step headers: **Step N: title**, ## Step N, Step N:, etc.
  const stepPattern = /(?:^|\n)\s*(?:\*\*|##?\s*)?\s*Step\s+(\d+)\s*[:\-–—.]?\s*(.*?)(?:\*\*)?(?=\n|$)/gi;
  const matches = [...solution.matchAll(stepPattern)];

  if (matches.length === 0) {
    // No step markers found — split by double newline or headings
    const sections = solution
      .split(/\n{2,}|(?=^##\s)/m)
      .map(s => s.trim())
      .filter(s => s.length > 0);

    return sections.map((section, i) => ({
      index: i + 1,
      title: `Part ${i + 1}`,
      body: section,
    }));
  }

  const steps = [];
  for (let i = 0; i < matches.length; i++) {
    const match = matches[i];
    const stepNum = parseInt(match[1], 10);
    const title = match[2]?.trim() || '';
    const start = match.index + match[0].length;
    const end = i + 1 < matches.length ? matches[i + 1].index : solution.length;
    const body = solution.slice(start, end).trim();

    steps.push({
      index: stepNum,
      title: title || `Step ${stepNum}`,
      body,
    });
  }

  return steps;
}

export default cleanMathText;
