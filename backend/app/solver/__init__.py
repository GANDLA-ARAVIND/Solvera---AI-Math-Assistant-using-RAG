"""Hybrid solver package — SymPy-first computation with LLM explanations."""

from app.solver.query_parser import preprocess_query, extract_math_expression
from app.solver.math_type_detector import detect_math_type
from app.solver.sympy_solver import sympy_solve
from app.solver.explanation_generator import explanation_generator

__all__ = [
    "preprocess_query",
    "extract_math_expression",
    "detect_math_type",
    "sympy_solve",
    "explanation_generator",
]
