import re


def fix_latex_formatting(text: str) -> str:
    """Fix common LaTeX formatting issues in LLM output."""
    # Fix unmatched dollar signs
    # Count single $ signs (not $$)
    single_dollar_count = len(re.findall(r'(?<!\$)\$(?!\$)', text))
    if single_dollar_count % 2 != 0:
        # Try to fix by finding the last unmatched $ and removing it
        text = re.sub(r'\$\s*$', '', text)

    # Fix \frac without braces: \frac ab -> \frac{a}{b}
    text = re.sub(r'\\frac\s+(\w)\s+(\w)', r'\\frac{\1}{\2}', text)

    # Ensure display math blocks have proper newlines
    text = re.sub(r'([^\n])\$\$', r'\1\n$$', text)
    text = re.sub(r'\$\$([^\n])', r'$$\n\1', text)

    return text


def extract_final_answer(solution_text: str) -> str | None:
    """Extract the final answer from a formatted solution."""
    # Look for ## Final Answer section
    match = re.search(
        r'(?:##\s*Final\s*Answer|Final\s*Answer)[:\s]*\$?\$?(.*?)\$?\$?\s*(?:##|$)',
        solution_text,
        re.MULTILINE | re.IGNORECASE | re.DOTALL,
    )
    if match:
        answer = match.group(1).strip()
        # Clean LaTeX wrappers
        answer = re.sub(r'^\$+|\$+$', '', answer).strip()
        return answer if answer else None

    # Fallback: look for "answer is" or "= " at end
    match = re.search(
        r'(?:answer\s+is|result\s+is|therefore)[:\s]*\$?\$?(.*?)\$?\$?\s*$',
        solution_text,
        re.MULTILINE | re.IGNORECASE,
    )
    if match:
        return match.group(1).strip() or None

    return None
