"""
TTS Service — AI-powered Text-to-Speech for math solutions.

Uses Microsoft Edge neural TTS (edge-tts) for high-quality natural voice.
No API key required.

Key design:
  • Plain text only — NO SSML (edge-tts reads SSML tags literally).
  • Indian teaching style: "Let us solve...", "Which gives us...", pauses (. …)
  • Math symbols → spoken words: x² → "x squared", ∫ → "integral of"
  • 1-second gaps via sentence-ending periods after every equation.

Public API:
    clean_math_text(text)                    → speech-friendly string
    generate_teaching_text(question, soln)   → full narration
    generate_voice(question, solution)       → {"audio_url": ..., "steps": [...]}
"""

import re
import os
import uuid
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
#  Configuration
# ═══════════════════════════════════════════════════════════════════════════
TTS_OUTPUT_DIR = Path("static/tts")
TTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TTS_VOICE = os.getenv("TTS_VOICE", "en-IN-NeerjaNeural")
TTS_RATE  = os.getenv("TTS_RATE",  "-10%")       # slower for math clarity
TTS_PITCH = os.getenv("TTS_PITCH", "+0Hz")


# ═══════════════════════════════════════════════════════════════════════════
#  1.  clean_math_text — LaTeX / Unicode → spoken English
# ═══════════════════════════════════════════════════════════════════════════

# Order matters — longer / more-specific patterns first.
_MATH_SUBSTITUTIONS: list[tuple[str, str, bool]] = [
    # (pattern, replacement, is_regex)

    # ── Unicode superscript digits ─────────────────────────
    ("⁰", " to the power of 0", False),
    ("¹", " to the power of 1", False),
    ("²", " squared", False),
    ("³", " cubed", False),
    ("⁴", " to the power of 4", False),
    ("⁵", " to the power of 5", False),
    ("⁶", " to the power of 6", False),
    ("⁷", " to the power of 7", False),
    ("⁸", " to the power of 8", False),
    ("⁹", " to the power of 9", False),
    ("ⁿ", " to the power of n", False),

    # ── Unicode subscript digits ───────────────────────────
    ("₀", " sub 0", False), ("₁", " sub 1", False),
    ("₂", " sub 2", False), ("₃", " sub 3", False),
    ("₄", " sub 4", False), ("₅", " sub 5", False),
    ("₆", " sub 6", False), ("₇", " sub 7", False),
    ("₈", " sub 8", False), ("₉", " sub 9", False),

    # ── Greek letters (LaTeX) ──────────────────────────────
    ("\\alpha",   "alpha",   False),
    ("\\beta",    "beta",    False),
    ("\\gamma",   "gamma",   False),
    ("\\delta",   "delta",   False),
    ("\\theta",   "theta",   False),
    ("\\pi",      "pi",      False),
    ("\\sigma",   "sigma",   False),
    ("\\mu",      "mu",      False),
    ("\\lambda",  "lambda",  False),
    ("\\epsilon", "epsilon", False),
    ("\\omega",   "omega",   False),
    ("\\phi",     "phi",     False),
    ("\\psi",     "psi",     False),
    ("\\rho",     "rho",     False),
    ("\\tau",     "tau",     False),

    # ── Greek letters (Unicode) ────────────────────────────
    ("α", "alpha", False), ("β", "beta", False),
    ("γ", "gamma", False), ("δ", "delta", False),
    ("θ", "theta", False), ("π", "pi", False),
    ("σ", "sigma", False), ("μ", "mu", False),
    ("λ", "lambda", False), ("ε", "epsilon", False),
    ("ω", "omega", False), ("φ", "phi", False),

    # ── Operators & relations ──────────────────────────────
    ("\\infty",       "infinity",                    False),
    ("∞",             "infinity",                    False),
    ("\\pm",          " plus or minus ",             False),
    ("±",             " plus or minus ",             False),
    ("\\mp",          " minus or plus ",             False),
    ("\\times",       " times ",                     False),
    ("×",             " times ",                     False),
    ("\\cdot",        " times ",                     False),
    ("·",             " times ",                     False),
    ("\\div",         " divided by ",                False),
    ("÷",             " divided by ",                False),
    ("\\neq",         " is not equal to ",           False),
    ("≠",             " is not equal to ",           False),
    ("\\leq",         " is less than or equal to ",  False),
    ("≤",             " is less than or equal to ",  False),
    ("\\geq",         " is greater than or equal to ", False),
    ("≥",             " is greater than or equal to ", False),
    ("\\approx",      " is approximately ",          False),
    ("≈",             " is approximately ",          False),
    ("\\equiv",       " is equivalent to ",          False),
    ("\\rightarrow",  " approaches ",                False),
    ("\\to",          " approaches ",                False),
    ("→",             " approaches ",                False),
    ("\\implies",     " which implies. ",            False),
    ("⟹",            " which implies. ",            False),
    ("\\therefore",   " therefore. ",                False),
    ("∴",             " therefore. ",                False),

    # ── Calculus (regex — complex patterns first) ──────────
    (r"\\int_\{([^}]*)\}\^\{([^}]*)\}", r" the integral from \1 to \2 of. ", True),
    (r"\\int",   " integral of ",   True),
    ("∫",        " integral of ",   False),
    (r"\\sum_\{([^}]*)\}\^\{([^}]*)\}", r" the summation from \1 to \2 of. ", True),
    (r"\\sum",   " summation of ",  True),
    ("∑",        " summation of ",  False),
    (r"\\prod",  " product of ",    True),
    ("∏",        " product of ",    False),
    (r"\\lim_\{([^}]*)\}", r" the limit as \1 of. ", True),
    (r"\\lim",   " the limit of ",  True),
    (r"\\partial", "partial ",      True),
    ("∂",        "partial ",        False),

    # ── Derivatives (specific before general fractions) ────
    (r"\\frac\{d\^(\d+)([^}]*)\}\{d([^}]*)\^(\d+)\}",
        r" the \1 order derivative of \2 with respect to \3. ", True),
    (r"\\frac\{d([^}]*)\}\{d([^}]*)\}", r" d \1 by d \2. ", True),
    ("dy/dx",    " d y by d x. ",   False),
    ("dx/dt",    " d x by d t. ",   False),
    ("d/dx",     " d by d x of ",   False),

    # ── dx, dy, dt (after derivative patterns) ─────────────
    ("\\,dx", " d x ", False),
    ("\\,dy", " d y ", False),
    ("\\,dt", " d t ", False),

    # ── Fractions & roots ──────────────────────────────────
    (r"\\frac\{([^}]*)\}\{([^}]*)\}", r" \1 over \2. ", True),
    (r"\\sqrt\[(\d+)\]\{([^}]*)\}",   r" the \1th root of \2. ", True),
    (r"\\sqrt\{([^}]*)\}",            r" the square root of \1. ", True),
    ("√",        " square root of ", False),

    # ── Powers (LaTeX ^) ───────────────────────────────────
    (r"\^\{\s*2\s*\}",      " squared",              True),
    (r"\^\{\s*3\s*\}",      " cubed",                True),
    (r"\^\{([^}]+)\}",      r" to the power of \1",  True),
    (r"\^2(?![0-9])",       " squared",              True),
    (r"\^3(?![0-9])",       " cubed",                True),
    (r"\^([0-9]+)",         r" to the power of \1",  True),
    (r"\^([a-zA-Z])",       r" to the power of \1",  True),

    # ── Subscripts ─────────────────────────────────────────
    (r"_\{([^}]+)\}", r" sub \1 ",   True),
    (r"_([0-9])",     r" sub \1 ",   True),
    (r"_([a-zA-Z])",  r" sub \1 ",   True),

    # ── Trig / log (LaTeX) ─────────────────────────────────
    (r"\\arcsin",  " arc sine of ",          True),
    (r"\\arccos",  " arc cosine of ",        True),
    (r"\\arctan",  " arc tangent of ",       True),
    (r"\\sinh",    " hyperbolic sine of ",   True),
    (r"\\cosh",    " hyperbolic cosine of ", True),
    (r"\\tanh",    " hyperbolic tangent of ",True),
    (r"\\sin",     " sine ",                 True),
    (r"\\cos",     " cosine ",               True),
    (r"\\tan",     " tangent ",              True),
    (r"\\cot",     " cotangent ",            True),
    (r"\\sec",     " secant ",               True),
    (r"\\csc",     " cosecant ",             True),
    (r"\\ln",      " natural log of ",       True),
    (r"\\log",     " log of ",               True),
    (r"\\exp",     " e to the power of ",    True),

    # ── Brackets ───────────────────────────────────────────
    ("\\left(",  " (", False),
    ("\\right)", ") ", False),
    ("\\left[",  " [", False),
    ("\\right]", "] ", False),
    ("\\left",   "",   False),
    ("\\right",  "",   False),

    # ── Text / format commands ─────────────────────────────
    (r"\\text\{([^}]*)\}",    r"\1", True),
    (r"\\mathrm\{([^}]*)\}",  r"\1", True),
    (r"\\mathbf\{([^}]*)\}",  r"\1", True),
    (r"\\textbf\{([^}]*)\}",  r"\1", True),
    (r"\\quad",               "  ",  True),
    (r"\\qquad",              "  ",  True),
]

# Patterns to strip after main substitutions
_STRIP_PATTERNS = [
    (r"\\[a-zA-Z]+",      ""),       # remaining unknown LaTeX commands
    (r"\$\$",              ""),       # display math delimiters $$
    (r"\$",                ""),       # inline math $
    (r"[{}]",              ""),       # leftover braces
    (r"\\\\",              " "),      # LaTeX line breaks
    (r"\*\*",              ""),       # markdown bold **
    (r"#{1,6}\s*",         ""),       # markdown headings
    (r"---+",              ""),       # horizontal rules
    (r"`[^`]*`",           ""),       # inline code
    (r"\|",                ""),       # table pipes
]


def clean_math_text(text: str) -> str:
    """Convert LaTeX / math symbols to clear spoken English with pauses."""
    if not text:
        return ""

    cleaned = text

    # 1. Main math substitutions
    for pattern, replacement, is_regex in _MATH_SUBSTITUTIONS:
        if is_regex:
            cleaned = re.sub(pattern, replacement, cleaned)
        else:
            cleaned = cleaned.replace(pattern, replacement)

    # 2. Strip leftover markup
    for pattern, replacement in _STRIP_PATTERNS:
        cleaned = re.sub(pattern, replacement, cleaned)

    # 3. Handle = sign → pause, "equals", pause
    cleaned = re.sub(r"\s*=\s*", " . equals . ", cleaned)

    # 4. Handle + and -
    cleaned = re.sub(r"\s*\+\s*", " plus ", cleaned)
    cleaned = re.sub(r"(?<=\w)\s*-\s*(?=\w)", " minus ", cleaned)

    # 5. Handle * (multiplication between terms)
    cleaned = re.sub(r"(?<=\w)\s*\*\s*(?=\w)", " times ", cleaned)

    # 6. Clean up any remaining raw ^ (would be read as "caret")
    cleaned = re.sub(r"\^", " to the power of ", cleaned)

    # 7. Clean up remaining raw _ not part of words
    cleaned = re.sub(r"(?<!\w)_(?!\w)", " ", cleaned)

    # 8. Collapse multiple periods into one pause
    cleaned = re.sub(r"\.(\s*\.)+", ".", cleaned)

    # 9. Collapse whitespace and newlines
    cleaned = re.sub(r"\n+", ". ", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)

    # 10. Remove leading/trailing periods and whitespace
    cleaned = cleaned.strip(". ")

    return cleaned


# ═══════════════════════════════════════════════════════════════════════════
#  2.  split_into_steps — parse solution into step objects
# ═══════════════════════════════════════════════════════════════════════════
def split_into_steps(solution: str) -> list[dict]:
    """Split a markdown solution into ordered step dicts."""
    if not solution:
        return []

    step_pattern = re.compile(
        r"(?:^|\n)\s*(?:\*\*|##?\s*)?\s*Step\s+(\d+)\s*[:\-–—.]?\s*(.*?)(?:\*\*)?(?=\n|$)",
        re.IGNORECASE,
    )
    matches = list(step_pattern.finditer(solution))

    if not matches:
        sections = [s.strip() for s in re.split(r"\n{2,}", solution) if s.strip()]
        return [{"index": i + 1, "title": f"Part {i + 1}", "body": s}
                for i, s in enumerate(sections)]

    steps = []
    for i, match in enumerate(matches):
        step_num = int(match.group(1))
        title = (match.group(2) or "").strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(solution)
        body = solution[start:end].strip()
        steps.append({
            "index": step_num,
            "title": title or f"Step {step_num}",
            "body": body,
        })

    return steps


# ═══════════════════════════════════════════════════════════════════════════
#  3.  generate_teaching_text — Indian teacher narration style
# ═══════════════════════════════════════════════════════════════════════════

# Transition phrases between steps — natural Indian teaching flow
_STEP_INTRO = [
    "Let us begin with the first step.",
    "Now, moving on to the next step.",
    "Good. Now let us continue.",
    "Alright. Next we will do the following.",
    "Now pay attention to this step.",
    "So, continuing further.",
    "Let us now apply this.",
    "Moving ahead.",
    "Now the next important step.",
    "Almost there. Let us proceed.",
    "Right. Now see what happens next.",
    "Now observe carefully.",
]


def generate_teaching_text(question: str | None, solution: str) -> tuple[str, list[dict]]:
    """Build a complete teacher-style narration as plain text.

    Returns (narration_text, steps_list).
    """
    parts: list[str] = []

    # ── Introduction: read the question first ──
    if question and question.strip():
        clean_q = clean_math_text(question)
        parts.append(f"Let us solve this question. The question is. {clean_q}.")
        parts.append("Now let us solve this step by step.")
    else:
        parts.append("Let us solve this step by step.")

    # ── Parse steps ──
    steps = split_into_steps(solution)

    if not steps:
        # No step markers — just read the whole solution
        plain = clean_math_text(solution)
        parts.append(plain)
        parts.append(". And that is the complete solution.")
        return _finalize_narration(parts), []

    # ── Build narration for each step ──
    for i, step in enumerate(steps):
        # Transition phrase
        intro = _STEP_INTRO[i % len(_STEP_INTRO)]
        parts.append(intro)

        # Step header
        title_clean = clean_math_text(step["title"])
        parts.append(f"Step {step['index']}. {title_clean}.")

        # Step body — convert and add pauses
        body_clean = clean_math_text(step["body"])
        body_clean = _add_teaching_pauses(body_clean)
        parts.append(body_clean + ".")

    # ── Final answer section ──
    final_match = re.search(
        r"(?:##?\s*)?(?:\*\*)?Final\s+Answer\s*(?:\*\*)?[:\s]*(.*?)(?:\n##|\n\*\*|\Z)",
        solution,
        re.IGNORECASE | re.DOTALL,
    )
    if final_match:
        answer_text = clean_math_text(final_match.group(1).strip())
        if answer_text:
            parts.append(
                f"Therefore. The final answer is. {answer_text}."
            )

    parts.append("And that completes our solution.")

    return _finalize_narration(parts), steps


def _finalize_narration(parts: list[str]) -> str:
    """Join parts and clean up the final narration text."""
    narration = " ".join(parts)
    # Clean double periods
    narration = re.sub(r"\.(\s*\.)+", ".", narration)
    # Clean excessive spaces
    narration = re.sub(r"\s{2,}", " ", narration)
    return narration.strip()


def _add_teaching_pauses(text: str) -> str:
    """Insert natural pauses for a teaching feel.

    Edge-tts pauses at periods (≈0.7s), so we use ". " as pause markers.
    """
    # After "equals <result>" add a pause
    text = re.sub(r"(equals\s*\.\s*)(\S[^.]{0,80}?)(\s|$)",
                  r"\1 \2. \3", text)

    # After key teaching phrases, add a pause
    for phrase in ["therefore", "which gives us", "we get", "we have",
                   "we obtain", "this becomes", "this gives",
                   "substituting", "simplifying", "applying"]:
        text = re.sub(
            rf"({phrase})\s*",
            rf"\1. ",
            text,
            flags=re.IGNORECASE,
        )

    return text


# ═══════════════════════════════════════════════════════════════════════════
#  4.  generate_voice — produce MP3 (plain text, NO SSML)
# ═══════════════════════════════════════════════════════════════════════════
async def generate_voice(solution_text: str, question: str | None = None) -> dict:
    """Generate MP3 audio from a math solution using edge-tts.

    Uses plain text mode — edge-tts naturally pauses at periods.
    NO SSML is used (edge-tts reads XML tags literally).
    """
    if not solution_text or not solution_text.strip():
        return {"success": False, "error": "Empty solution text"}

    narration, steps = generate_teaching_text(question, solution_text)

    try:
        import edge_tts

        filename = f"tts_{uuid.uuid4().hex[:12]}.mp3"
        output_path = TTS_OUTPUT_DIR / filename

        communicate = edge_tts.Communicate(
            text=narration,
            voice=TTS_VOICE,
            rate=TTS_RATE,
            pitch=TTS_PITCH,
        )
        await communicate.save(str(output_path))

        logger.info("TTS generated: %s (%d steps, %d chars)",
                     filename, len(steps), len(narration))

        return {
            "success": True,
            "audio_url": f"/static/tts/{filename}",
            "steps": [{"index": s["index"], "title": s["title"]} for s in steps],
            "voice": TTS_VOICE,
            "total_steps": len(steps),
        }

    except ImportError:
        logger.error("edge-tts not installed. Run: pip install edge-tts")
        return await _fallback_gtts(narration, steps)
    except Exception as e:
        logger.error("edge-tts failed: %s", e)
        return await _fallback_gtts(narration, steps)


async def _fallback_gtts(narration: str, steps: list[dict]) -> dict:
    """Fallback to gTTS if edge-tts is unavailable."""
    try:
        from gtts import gTTS

        filename = f"tts_{uuid.uuid4().hex[:12]}.mp3"
        output_path = TTS_OUTPUT_DIR / filename

        tts = gTTS(text=narration, lang="en", tld="co.in")
        tts.save(str(output_path))

        logger.info("Fallback gTTS audio: %s", filename)
        return {
            "success": True,
            "audio_url": f"/static/tts/{filename}",
            "steps": [{"index": s["index"], "title": s["title"]} for s in steps],
            "voice": "gTTS-fallback",
            "total_steps": len(steps),
        }
    except Exception as e:
        logger.error("gTTS also failed: %s", e)
        return {
            "success": False,
            "error": f"All TTS engines failed: {str(e)}",
            "fallback_to_browser": True,
        }


# ═══════════════════════════════════════════════════════════════════════════
#  5.  Cleanup old audio files
# ═══════════════════════════════════════════════════════════════════════════
def cleanup_old_audio(max_age_seconds: int = 3600):
    """Delete TTS audio files older than max_age_seconds."""
    import time
    now = time.time()
    count = 0
    for f in TTS_OUTPUT_DIR.glob("tts_*.mp3"):
        if now - f.stat().st_mtime > max_age_seconds:
            f.unlink(missing_ok=True)
            count += 1
    if count:
        logger.info("Cleaned up %d old TTS audio files", count)
