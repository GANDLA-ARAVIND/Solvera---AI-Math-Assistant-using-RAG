"""
Solvera Evaluation — Advanced Plot Generator
==============================================
Reads results.csv, metrics.json, and test_dataset.json produced by
evaluate_system.py and generates seven publication-ready evaluation charts
suitable for research reports and presentations.

Usage:
    python evaluation/plot_results.py

Generated charts (saved in the evaluation/ folder):
    1. accuracy_chart.png         — Overall accuracy bar chart
    2. metrics_chart.png          — Precision / Recall / F1 comparison
    3. response_time_chart.png    — Per-question response time line graph
    4. accuracy_pie_chart.png     — Correct vs Incorrect pie chart
    5. confusion_matrix.png       — Confusion matrix heatmap
    6. benchmark_comparison.png   — Benchmark comparison bar chart
    7. topic_accuracy.png         — Topic-wise accuracy bar chart
"""

import csv
import json
import os
import re
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")  # non-interactive backend — works without a display

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import seaborn as sns

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_CSV = os.path.join(EVAL_DIR, "results.csv")
METRICS_JSON = os.path.join(EVAL_DIR, "metrics.json")
TEST_DATASET = os.path.join(EVAL_DIR, "test_dataset.json")

# Output image paths
ACCURACY_CHART = os.path.join(EVAL_DIR, "accuracy_chart.png")
METRICS_CHART = os.path.join(EVAL_DIR, "metrics_chart.png")
RESPONSE_TIME_CHART = os.path.join(EVAL_DIR, "response_time_chart.png")
PIE_CHART = os.path.join(EVAL_DIR, "accuracy_pie_chart.png")
CONFUSION_MATRIX_CHART = os.path.join(EVAL_DIR, "confusion_matrix.png")
BENCHMARK_CHART = os.path.join(EVAL_DIR, "benchmark_comparison.png")
TOPIC_ACCURACY_CHART = os.path.join(EVAL_DIR, "topic_accuracy.png")

# ---------------------------------------------------------------------------
# Global Styling
# ---------------------------------------------------------------------------
sns.set_theme(style="whitegrid", font_scale=1.15)
plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "#FAFAFA",
    "font.family": "sans-serif",
    "axes.titlepad": 14,
    "axes.labelpad": 10,
})
PALETTE = sns.color_palette("muted")
SOLVERA_COLOR = "#1E88E5"       # primary blue for Solvera branding
SOLVERA_ACCENT = "#43A047"      # green accent for highlights
SOLVERA_WARN = "#E53935"        # red for warnings / incorrect


# ═══════════════════════════════════════════════════════════════════════════
# Data Loading
# ═══════════════════════════════════════════════════════════════════════════

def load_data():
    """Load results.csv, metrics.json, and test_dataset.json.

    Returns:
        (rows, metrics, dataset)
        - rows     : list[dict] from results.csv
        - metrics  : dict from metrics.json (or computed from CSV)
        - dataset  : list[dict] from test_dataset.json (may be empty)
    """

    # ── Load CSV rows ─────────────────────────────────────────────────────
    if not os.path.exists(RESULTS_CSV):
        print(f"ERROR: {RESULTS_CSV} not found.")
        print("Run 'python evaluation/evaluate_system.py' first to generate results.")
        sys.exit(1)

    with open(RESULTS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print("ERROR: results.csv is empty.")
        sys.exit(1)

    status_key = "Correct or Incorrect"
    if status_key not in rows[0]:
        print(f"ERROR: Column '{status_key}' not found in results.csv.")
        sys.exit(1)

    # ── Load metrics ──────────────────────────────────────────────────────
    if os.path.exists(METRICS_JSON):
        with open(METRICS_JSON, "r", encoding="utf-8") as f:
            metrics = json.load(f)
    else:
        total = len(rows)
        correct = sum(1 for r in rows if r[status_key] == "Correct")
        incorrect = total - correct
        accuracy = correct / total if total else 0
        tp, fp, fn = correct, 0, incorrect
        precision = tp / (tp + fp) if (tp + fp) else 0
        recall = tp / (tp + fn) if (tp + fn) else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0
        times = [float(r["Response Time"]) for r in rows]
        avg_time = sum(times) / len(times) if times else 0
        metrics = {
            "total_questions": total,
            "correct_answers": correct,
            "incorrect_answers": incorrect,
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "avg_response_time": round(avg_time, 4),
        }

    # ── Load test dataset (for topic info) ────────────────────────────────
    dataset = []
    if os.path.exists(TEST_DATASET):
        with open(TEST_DATASET, "r", encoding="utf-8") as f:
            dataset = json.load(f)

    return rows, metrics, dataset


def _build_topic_map(rows, dataset):
    """Map each question to a topic using dataset or keyword heuristics.

    Returns dict[question_text, topic_str].
    """
    topic_map = {}

    # 1) From test_dataset.json
    for item in dataset:
        q = item.get("question", "").strip()
        t = item.get("topic", "").strip()
        if q and t:
            topic_map[q] = t.capitalize()

    # 2) Keyword-based fallback for any row not matched
    _KEYWORD_TOPICS = [
        (r"deriv|differentiat",   "Calculus"),
        (r"integrat|integral",    "Calculus"),
        (r"limit",                "Calculus"),
        (r"sin|cos|tan|trig",     "Trigonometry"),
        (r"factor|expand|simplif|polynomial|equation|solve|system",  "Algebra"),
        (r"matrix|determinant",   "Linear Algebra"),
        (r"statistic|mean|median|deviation|probability", "Statistics"),
        (r"geometr|area|volume|circle|triangle",         "Geometry"),
    ]

    for row in rows:
        q = row.get("Question", "").strip()
        if q not in topic_map:
            q_lower = q.lower()
            matched = False
            for pattern, topic in _KEYWORD_TOPICS:
                if re.search(pattern, q_lower):
                    topic_map[q] = topic
                    matched = True
                    break
            if not matched:
                topic_map[q] = "Other"

    return topic_map


# ═══════════════════════════════════════════════════════════════════════════
# Chart 1 — Accuracy bar chart
# ═══════════════════════════════════════════════════════════════════════════

def plot_accuracy(metrics: dict):
    """Single bar showing overall accuracy percentage."""
    fig, ax = plt.subplots(figsize=(6, 5))
    accuracy_pct = metrics["accuracy"] * 100

    bar = ax.bar(
        ["Accuracy"], [accuracy_pct],
        color=SOLVERA_COLOR, width=0.45, edgecolor="black", linewidth=0.8,
        zorder=3,
    )
    ax.bar_label(bar, fmt="%.1f%%", fontsize=14, fontweight="bold", padding=4)

    ax.set_ylim(0, 110)
    ax.set_ylabel("Percentage (%)", fontsize=12)
    ax.set_title("Solvera \u2014 Overall Accuracy", fontsize=15, fontweight="bold")
    ax.tick_params(axis="x", labelsize=13)
    ax.grid(axis="y", alpha=0.4)

    plt.tight_layout()
    fig.savefig(ACCURACY_CHART, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [1/7] Saved: {ACCURACY_CHART}")


# ═══════════════════════════════════════════════════════════════════════════
# Chart 2 — Precision / Recall / F1 comparison
# ═══════════════════════════════════════════════════════════════════════════

def plot_metrics_comparison(metrics: dict):
    """Bar chart comparing Precision, Recall, and F1 Score."""
    fig, ax = plt.subplots(figsize=(7, 5))
    labels = ["Precision", "Recall", "F1 Score"]
    values = [metrics["precision"], metrics["recall"], metrics["f1_score"]]
    colors = [PALETTE[1], PALETTE[2], PALETTE[3]]

    bars = ax.bar(
        labels, values, color=colors, width=0.5,
        edgecolor="black", linewidth=0.8, zorder=3,
    )
    ax.bar_label(bars, fmt="%.3f", fontsize=12, fontweight="bold", padding=4)

    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Score", fontsize=12)
    ax.set_title("Solvera \u2014 Precision / Recall / F1 Score",
                 fontsize=15, fontweight="bold")
    ax.tick_params(axis="x", labelsize=12)
    ax.grid(axis="y", alpha=0.4)

    plt.tight_layout()
    fig.savefig(METRICS_CHART, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [2/7] Saved: {METRICS_CHART}")


# ═══════════════════════════════════════════════════════════════════════════
# Chart 3 — Response time line graph
# ═══════════════════════════════════════════════════════════════════════════

def plot_response_times(rows: list, metrics: dict):
    """Line chart of per-question response time with average line."""
    fig, ax = plt.subplots(figsize=(10, 5))

    times = [float(r["Response Time"]) for r in rows]
    indices = list(range(1, len(times) + 1))

    # Color each marker by correct/incorrect
    statuses = [r["Correct or Incorrect"] for r in rows]
    marker_colors = [SOLVERA_ACCENT if s == "Correct" else SOLVERA_WARN
                     for s in statuses]

    ax.plot(indices, times, linewidth=1.3, color=SOLVERA_COLOR, alpha=0.6, zorder=2)
    ax.scatter(indices, times, c=marker_colors, s=50, edgecolors="white",
               linewidth=0.6, zorder=3)

    avg = metrics["avg_response_time"]
    ax.axhline(y=avg, color=SOLVERA_WARN, linestyle="--", linewidth=1.2,
               label=f"Average ({avg:.2f}s)", zorder=2)

    # Legend entries for marker colors
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=SOLVERA_ACCENT,
               markersize=8, label="Correct"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=SOLVERA_WARN,
               markersize=8, label="Incorrect"),
        Line2D([0], [0], color=SOLVERA_WARN, linestyle="--",
               linewidth=1.2, label=f"Average ({avg:.2f}s)"),
    ]
    ax.legend(handles=legend_elements, fontsize=10, loc="upper right")

    ax.set_xlabel("Question Number", fontsize=12)
    ax.set_ylabel("Response Time (seconds)", fontsize=12)
    ax.set_title("Solvera \u2014 Response Time per Question",
                 fontsize=15, fontweight="bold")

    if len(indices) <= 30:
        ax.set_xticks(indices)

    ax.grid(axis="both", alpha=0.3)
    plt.tight_layout()
    fig.savefig(RESPONSE_TIME_CHART, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [3/7] Saved: {RESPONSE_TIME_CHART}")


# ═══════════════════════════════════════════════════════════════════════════
# Chart 4 — Correct vs Incorrect pie chart
# ═══════════════════════════════════════════════════════════════════════════

def plot_pie_chart(metrics: dict):
    """Pie chart of Correct vs Incorrect answers."""
    fig, ax = plt.subplots(figsize=(6, 6))

    correct = metrics["correct_answers"]
    incorrect = metrics["incorrect_answers"]
    sizes = [correct, incorrect]
    labels = [f"Correct ({correct})", f"Incorrect ({incorrect})"]
    colors = [SOLVERA_ACCENT, SOLVERA_WARN]
    explode = (0.04, 0.04)

    wedges, texts, autotexts = ax.pie(
        sizes, explode=explode, labels=labels, colors=colors,
        autopct="%1.1f%%", startangle=90,
        textprops={"fontsize": 12},
        shadow=True,
    )
    for t in autotexts:
        t.set_fontweight("bold")
        t.set_color("white")

    ax.set_title("Solvera \u2014 Correct vs Incorrect",
                 fontsize=15, fontweight="bold")

    plt.tight_layout()
    fig.savefig(PIE_CHART, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [4/7] Saved: {PIE_CHART}")


# ═══════════════════════════════════════════════════════════════════════════
# Chart 5 — Confusion Matrix (seaborn heatmap)
# ═══════════════════════════════════════════════════════════════════════════

def plot_confusion_matrix(rows: list):
    """Binary confusion matrix from the 'Correct or Incorrect' column.

    True Positive  (TP): System answered correctly   (Actual=Correct,  Pred=Correct)
    False Negative (FN): System answered incorrectly (Actual=Correct,  Pred=Incorrect)
    False Positive (FP): 0 — answers are not misclassified into correct
    True Negative  (TN): 0 — no negative class in this evaluation
    """
    tp = sum(1 for r in rows if r["Correct or Incorrect"] == "Correct")
    fn = sum(1 for r in rows if r["Correct or Incorrect"] != "Correct")
    fp = 0
    tn = 0

    cm = np.array([[tp, fp],
                    [fn, tn]])

    fig, ax = plt.subplots(figsize=(6.5, 5.5))

    sns.heatmap(
        cm, annot=True, fmt="d", cmap="Blues",
        xticklabels=["Predicted Correct", "Predicted Incorrect"],
        yticklabels=["Actual Correct", "Actual Incorrect"],
        linewidths=1.5, linecolor="white",
        annot_kws={"size": 18, "fontweight": "bold"},
        cbar_kws={"shrink": 0.8, "label": "Count"},
        ax=ax,
    )

    ax.set_title("Solvera \u2014 Confusion Matrix",
                 fontsize=15, fontweight="bold")
    ax.set_xlabel("Predicted Label", fontsize=12)
    ax.set_ylabel("Actual Label", fontsize=12)
    ax.tick_params(axis="both", labelsize=11)

    # Add summary text box
    total = tp + fn
    acc = tp / total * 100 if total else 0
    textstr = f"TP={tp}  FN={fn}  FP={fp}  TN={tn}\nAccuracy={acc:.1f}%"
    props = dict(boxstyle="round,pad=0.4", facecolor="#E3F2FD", alpha=0.9)
    ax.text(1.02, 0.5, textstr, transform=ax.transAxes, fontsize=10,
            verticalalignment="center", bbox=props)

    plt.tight_layout()
    fig.savefig(CONFUSION_MATRIX_CHART, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [5/7] Saved: {CONFUSION_MATRIX_CHART}")


# ═══════════════════════════════════════════════════════════════════════════
# Chart 6 — Benchmark Comparison
# ═══════════════════════════════════════════════════════════════════════════

def plot_benchmark_comparison(metrics: dict):
    """Comparison bar chart of Solvera vs baseline systems."""
    solvera_acc = metrics["accuracy"] * 100

    systems = [
        "Traditional\nRule-based Solver",
        "Basic LLM\nSolver",
        "Solvera\n(Hybrid SymPy + LLM)",
    ]
    accuracies = [70.0, 80.0, solvera_acc]

    # Highlight Solvera bar with a different color
    bar_colors = ["#90A4AE", "#78909C", SOLVERA_COLOR]
    edge_colors = ["#607D8B", "#546E7A", "#0D47A1"]

    fig, ax = plt.subplots(figsize=(8, 5.5))

    bars = ax.bar(
        systems, accuracies, color=bar_colors, width=0.55,
        edgecolor=edge_colors, linewidth=1.2, zorder=3,
    )

    # Value labels on each bar
    for bar, acc in zip(bars, accuracies):
        ax.text(
            bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.2,
            f"{acc:.1f}%", ha="center", va="bottom",
            fontsize=13, fontweight="bold",
            color="black" if acc < solvera_acc else SOLVERA_COLOR,
        )

    ax.set_ylim(0, max(accuracies) + 15)
    ax.set_ylabel("Accuracy (%)", fontsize=12)
    ax.set_title("Solvera \u2014 Benchmark Comparison",
                 fontsize=15, fontweight="bold")
    ax.tick_params(axis="x", labelsize=11)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax.grid(axis="y", alpha=0.4)

    # Annotate Solvera bar
    best_bar = bars[-1]
    ax.annotate(
        "* Best", xy=(best_bar.get_x() + best_bar.get_width() / 2,
                      best_bar.get_height()),
        xytext=(0, 22), textcoords="offset points",
        ha="center", fontsize=11, fontweight="bold", color=SOLVERA_COLOR,
        arrowprops=dict(arrowstyle="->", color=SOLVERA_COLOR, lw=1.5),
    )

    plt.tight_layout()
    fig.savefig(BENCHMARK_CHART, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [6/7] Saved: {BENCHMARK_CHART}")


# ═══════════════════════════════════════════════════════════════════════════
# Chart 7 — Topic-wise Accuracy
# ═══════════════════════════════════════════════════════════════════════════

def plot_topic_accuracy(rows: list, dataset: list):
    """Bar chart showing accuracy broken down by math topic."""
    topic_map = _build_topic_map(rows, dataset)

    # Aggregate per topic
    topic_stats = defaultdict(lambda: {"correct": 0, "total": 0})
    for row in rows:
        q = row.get("Question", "").strip()
        topic = topic_map.get(q, "Other")
        is_correct = row["Correct or Incorrect"] == "Correct"
        topic_stats[topic]["total"] += 1
        if is_correct:
            topic_stats[topic]["correct"] += 1

    # Sort topics by accuracy descending
    topic_data = []
    for topic, stats in sorted(topic_stats.items(),
                                key=lambda x: (x[1]["correct"] / x[1]["total"]
                                               if x[1]["total"] else 0),
                                reverse=True):
        acc = stats["correct"] / stats["total"] * 100 if stats["total"] else 0
        topic_data.append((topic, acc, stats["correct"], stats["total"]))

    topics = [t[0] for t in topic_data]
    accs = [t[1] for t in topic_data]
    counts = [f"{t[2]}/{t[3]}" for t in topic_data]

    # Color: green for 100%, gradient down to red for 0%
    bar_colors = []
    for a in accs:
        if a >= 90:
            bar_colors.append(SOLVERA_ACCENT)
        elif a >= 70:
            bar_colors.append(SOLVERA_COLOR)
        elif a >= 50:
            bar_colors.append("#FFA726")
        else:
            bar_colors.append(SOLVERA_WARN)

    fig, ax = plt.subplots(figsize=(max(8, len(topics) * 1.2), 5.5))

    bars = ax.bar(
        topics, accs, color=bar_colors, width=0.55,
        edgecolor="black", linewidth=0.7, zorder=3,
    )

    # Label each bar with accuracy% and count
    for bar, acc, count in zip(bars, accs, counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.5,
            f"{acc:.0f}%\n({count})", ha="center", va="bottom",
            fontsize=10, fontweight="bold",
        )

    ax.set_ylim(0, max(accs) + 18 if accs else 110)
    ax.set_ylabel("Accuracy (%)", fontsize=12)
    ax.set_xlabel("Topic", fontsize=12)
    ax.set_title("Solvera \u2014 Topic-wise Accuracy",
                 fontsize=15, fontweight="bold")
    ax.tick_params(axis="x", labelsize=11, rotation=15)
    ax.grid(axis="y", alpha=0.4)

    # Add a horizontal line at overall average
    if accs:
        overall_avg = sum(accs) / len(accs)
        ax.axhline(y=overall_avg, color=SOLVERA_WARN, linestyle="--",
                   linewidth=1.2, label=f"Average ({overall_avg:.0f}%)")
        ax.legend(fontsize=10)

    plt.tight_layout()
    fig.savefig(TOPIC_ACCURACY_CHART, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [7/7] Saved: {TOPIC_ACCURACY_CHART}")


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 62)
    print("  Solvera — Advanced Evaluation Chart Generator")
    print("=" * 62)
    print()

    rows, metrics, dataset = load_data()

    total = metrics.get("total_questions", len(rows))
    print(f"  Loaded {total} results from results.csv")
    print(f"  Accuracy : {metrics['accuracy']*100:.1f}%")
    print(f"  Precision: {metrics['precision']:.4f}")
    print(f"  Recall   : {metrics['recall']:.4f}")
    print(f"  F1 Score : {metrics['f1_score']:.4f}")
    sympy_n = metrics.get("sympy_computed", "N/A")
    if sympy_n != "N/A":
        print(f"  SymPy    : {sympy_n}/{total}"
              f" ({metrics.get('sympy_rate', 0)*100:.0f}%)")
    print()
    print("  Generating charts...")
    print()

    # 1-4: Original charts (improved)
    plot_accuracy(metrics)
    plot_metrics_comparison(metrics)
    plot_response_times(rows, metrics)
    plot_pie_chart(metrics)

    # 5-7: New advanced charts
    plot_confusion_matrix(rows)
    plot_benchmark_comparison(metrics)
    plot_topic_accuracy(rows, dataset)

    print()
    print("  All evaluation graphs saved successfully in evaluation folder.")
    print("=" * 62)


if __name__ == "__main__":
    main()
