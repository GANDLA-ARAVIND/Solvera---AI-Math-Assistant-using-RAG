import json
from app.config import GOOGLE_API_KEY, GROQ_API_KEY, USE_GROQ
from app.utils.math_topics import MATH_TOPICS


class QueryClassifier:
    def __init__(self):
        self.use_groq = USE_GROQ
        if self.use_groq:
            from groq import Groq
            self.groq_client = Groq(api_key=GROQ_API_KEY)
            self.groq_model = "llama-3.3-70b-versatile"
        else:
            import google.generativeai as genai
            genai.configure(api_key=GOOGLE_API_KEY)
            self.model = genai.GenerativeModel("gemini-2.0-flash")

    def is_math_query(self, query: str) -> dict:
        """
        Classify whether a query is math-related and identify its topic.
        Returns {"is_math": bool, "confidence": float, "topic": str|None, "reason": str}
        """
        # Stage 1: Quick keyword check
        query_lower = query.lower()
        keyword_matches = {}
        for topic, info in MATH_TOPICS.items():
            matches = sum(1 for kw in info["keywords"] if kw.lower() in query_lower)
            if matches > 0:
                keyword_matches[topic] = matches

        # If strong keyword match, skip LLM call to save API usage
        if keyword_matches:
            best_topic = max(keyword_matches, key=keyword_matches.get)
            if keyword_matches[best_topic] >= 2:
                return {
                    "is_math": True,
                    "confidence": 0.95,
                    "topic": best_topic,
                    "reason": "Strong keyword match",
                }

        # Check for mathematical symbols/patterns
        math_patterns = [
            "=", "+", "-", "*", "/", "^", "√", "∫", "∑", "π",
            "x²", "x^2", "dx", "dy", ">=", "<=",
        ]
        symbol_matches = sum(1 for p in math_patterns if p in query)
        if symbol_matches >= 2:
            best_topic = (
                max(keyword_matches, key=keyword_matches.get)
                if keyword_matches
                else "algebra"
            )
            return {
                "is_math": True,
                "confidence": 0.9,
                "topic": best_topic,
                "reason": "Mathematical symbols detected",
            }

        # Stage 2: LLM classification for ambiguous queries
        try:
            prompt = f"""Classify this query. Is it a mathematics question?
Query: "{query}"

Respond in this exact JSON format only, no other text:
{{"is_math": true, "topic": "algebra", "confidence": 0.9}}

Valid topics: algebra, calculus, geometry, trigonometry, statistics, number_theory, general_math
Only classify as math if it's genuinely asking to solve, explain, or understand a mathematical concept or problem."""

            if self.use_groq:
                response = self.groq_client.chat.completions.create(
                    model=self.groq_model,
                    messages=[
                        {"role": "system", "content": "You are a math query classifier. Respond only with JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.1,
                    max_tokens=100,
                )
                text = response.choices[0].message.content.strip()
            else:
                response = self.model.generate_content(prompt)
                text = response.text.strip()

            # Clean markdown code block if present
            text = text.replace("```json", "").replace("```", "").strip()
            result = json.loads(text)

            return {
                "is_math": result.get("is_math", False),
                "confidence": result.get("confidence", 0.8),
                "topic": result.get("topic") if result.get("is_math") else None,
                "reason": "LLM classification",
            }
        except Exception:
            # Fallback: if we had any keyword matches, treat as math
            if keyword_matches:
                return {
                    "is_math": True,
                    "confidence": 0.6,
                    "topic": max(keyword_matches, key=keyword_matches.get),
                    "reason": "Keyword fallback",
                }
            return {
                "is_math": False,
                "confidence": 0.7,
                "topic": None,
                "reason": "Could not classify",
            }


query_classifier = QueryClassifier()
