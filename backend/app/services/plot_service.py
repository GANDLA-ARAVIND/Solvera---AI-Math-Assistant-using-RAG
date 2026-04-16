import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
from sympy import symbols, lambdify
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
)
import os
import uuid

PLOT_DIR = "static/plots"
os.makedirs(PLOT_DIR, exist_ok=True)


class PlotService:
    TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application,)

    def generate_plot(
        self, expression_str: str, x_range: tuple = (-10, 10), title: str = None
    ) -> dict:
        """Generate a plot for a mathematical function and save as PNG."""
        try:
            x = symbols("x")
            expr = parse_expr(expression_str, transformations=self.TRANSFORMATIONS)
            f = lambdify(x, expr, modules=["numpy"])

            x_vals = np.linspace(x_range[0], x_range[1], 500)
            y_vals = f(x_vals)

            fig, ax = plt.subplots(figsize=(8, 5))
            ax.plot(x_vals, y_vals, "#3b82f6", linewidth=2)
            ax.set_xlabel("x", fontsize=12)
            ax.set_ylabel("f(x)", fontsize=12)
            ax.set_title(title or f"f(x) = {expression_str}", fontsize=14)
            ax.grid(True, alpha=0.3)
            ax.axhline(y=0, color="gray", linewidth=0.5)
            ax.axvline(x=0, color="gray", linewidth=0.5)

            # Style
            fig.patch.set_facecolor("#1e293b")
            ax.set_facecolor("#0f172a")
            ax.tick_params(colors="#94a3b8")
            ax.xaxis.label.set_color("#94a3b8")
            ax.yaxis.label.set_color("#94a3b8")
            ax.title.set_color("#e2e8f0")
            for spine in ax.spines.values():
                spine.set_color("#334155")

            # Auto-limit y-axis to avoid infinite spikes
            finite_y = y_vals[np.isfinite(y_vals)]
            if len(finite_y) > 0:
                y_margin = (np.max(finite_y) - np.min(finite_y)) * 0.1 + 0.1
                ax.set_ylim(np.min(finite_y) - y_margin, np.max(finite_y) + y_margin)

            filename = f"{uuid.uuid4().hex}.png"
            filepath = os.path.join(PLOT_DIR, filename)
            fig.savefig(filepath, dpi=100, bbox_inches="tight")
            plt.close(fig)

            return {"success": True, "plot_url": f"/static/plots/{filename}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


plot_service = PlotService()
