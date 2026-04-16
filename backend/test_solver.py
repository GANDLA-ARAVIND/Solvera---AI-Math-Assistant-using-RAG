"""Quick test for the new solver modules."""
import sys
sys.path.insert(0, ".")

from app.solver.query_parser import preprocess_query, extract_math_expression
from app.solver.math_type_detector import detect_math_type
from app.solver.sympy_solver import sympy_solve

# Test query preprocessing
print("=== Query Preprocessing ===")
print(preprocess_query("integrate x^2 + 3x"))
print(preprocess_query("find the derivative of sin(x) * cos(x)"))

# Test expression extraction
print("\n=== Expression Extraction ===")
r = extract_math_expression("Solve x^2 - 5x + 6 = 0")
print(f"Equation: {r}")

r = extract_math_expression("Integrate x^2")
print(f"Integral: {r}")

r = extract_math_expression("Find the derivative of x^3 + 2x^2 - 5x + 1")
print(f"Derivative: {r}")

r = extract_math_expression("Simplify sin^2(x) + cos^2(x)")
print(f"Simplify: {r}")

# Test math type detection
print("\n=== Math Type Detection ===")
questions = [
    "Solve x^2 - 5x + 6 = 0",
    "Integrate x^2",
    "Find the derivative of sin(x) * cos(x)",
    "Find the limit of sin(x)/x as x approaches 0",
    "Simplify sin^2(x) + cos^2(x)",
    "Factor x^2 + 7x + 12",
    "Expand (a + b)^3",
    "Find the second derivative of x^4 - 3x^2 + 2x",
    "Find the integral of cos(x) from 0 to pi/2",
    "Solve the system of equations: x + y = 10, x - y = 4",
]
for q in questions:
    result = detect_math_type(q)
    print(f"  {q}")
    print(f"    -> type={result['type']}, confidence={result['confidence']:.2f}")

# Test SymPy solver
print("\n=== SymPy Solver ===")
test_cases = [
    ("Solve x^2 - 5x + 6 = 0", "equation"),
    ("Integrate x^2", "integration"),
    ("Find the derivative of x^3 + 2x^2 - 5x + 1", "derivative"),
    ("Simplify sin^2(x) + cos^2(x)", "simplification"),
    ("Factor x^2 + 7x + 12", "factoring"),
    ("Expand (a + b)^3", "expansion"),
    ("Find the limit of sin(x)/x as x approaches 0", "limit"),
    ("Find the derivative of sin(x) * cos(x)", "derivative"),
    ("Find the second derivative of x^4 - 3x^2 + 2x", "second_derivative"),
    ("Integrate sin(x)", "integration"),
    ("Integrate 1/x", "integration"),
    ("Solve 2x + 3 = 11", "equation"),
    ("Find the integral of cos(x) from 0 to pi/2", "definite_integral"),
    ("Solve 3x - 7 = 2x + 5", "equation"),
    ("Simplify (x^2 - 9) / (x - 3)", "simplification"),
    ("Solve x^3 - 6x^2 + 11x - 6 = 0", "equation"),
    ("Differentiate x*e^x with respect to x", "derivative"),
    ("Integrate e^x", "integration"),
    ("Integrate 2x + 3", "integration"),
    ("Find the derivative of e^(2x)", "derivative"),
    ("Find the derivative of ln(x^2 + 1)", "derivative"),
    ("Find the limit of (x^2 - 1)/(x - 1) as x approaches 1", "limit"),
    ("Simplify tan(x) * cos(x)", "simplification"),
]

correct = 0
total = len(test_cases)
for question, expected_type in test_cases:
    parsed = extract_math_expression(question)
    detected = detect_math_type(question)
    result = sympy_solve(detected["type"], parsed)
    status = "OK" if result["success"] else "FAIL"
    if result["success"]:
        correct += 1
    print(f"  [{status}] {question}")
    print(f"       type={detected['type']}, answer={result.get('result_str', 'N/A')}")

print(f"\n=== Results: {correct}/{total} solved ({correct/total*100:.0f}%) ===")
