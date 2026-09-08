#!/usr/bin/env python3
"""Render individual PNGs from already-saved evaluation JSON (no retraining)."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

EVAL = Path(__file__).resolve().parent
FIG = EVAL / "figures"
FIG.mkdir(exist_ok=True)


def slug(name: str) -> str:
    return name.lower().replace(" ", "_").replace("-", "_")


def save(fig, path: Path) -> None:
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    offline = json.loads((EVAL / "results" / "offline_metrics.json").read_text())
    e2e = json.loads((EVAL / "results" / "e2e_metrics.json").read_text())
    models = offline["models"]
    names = list(models)

    series = [
        ("accuracy", "Accuracy", "offline_accuracy"),
        ("precision_phishing", "Precision (phishing)", "offline_precision_phishing"),
        ("f1_phishing", "F1 (phishing)", "offline_f1_phishing"),
        ("recall_phishing", "Recall / phishing detection rate", "offline_recall_phishing"),
        ("false_negative_rate", "False negative rate (missed phishing)", "offline_fnr"),
        ("false_positive_rate", "False positive rate", "offline_fpr"),
    ]
    for key, title, filename in series:
        fig, ax = plt.subplots(figsize=(8, 4.2))
        ax.barh(names, [models[n][key] for n in names], color="#334155")
        ax.set_title(title)
        ax.set_xlim(0, 1)
        ax.set_xlabel("Score")
        ax.set_ylabel("Model")
        save(fig, FIG / f"{filename}.png")

    for name in names:
        cm = np.array(models[name]["confusion_matrix"]["matrix"])
        fig, ax = plt.subplots(figsize=(4.8, 4.2))
        im = ax.imshow(cm, cmap="Blues")
        ax.set_title(f"{name} confusion matrix (UCI test)")
        ax.set_xticks([0, 1], ["Pred phishing", "Pred legitimate"])
        ax.set_yticks([0, 1], ["True phishing", "True legitimate"])
        for i in range(2):
            for j in range(2):
                ax.text(j, i, str(cm[i, j]), ha="center", va="center")
        fig.colorbar(im, ax=ax, fraction=0.046)
        save(fig, FIG / f"cm_{slug(name)}.png")

    t = offline["deployment_tradeoff"]
    lr_kb = t["logistic_regression"]["model_size_bytes"] / 1024
    rf_kb = t["random_forest"]["model_size_bytes"] / 1024
    lr_ms = t["logistic_regression"]["mean_predict_seconds"] * 1000
    rf_ms = t["random_forest"]["mean_predict_seconds"] * 1000

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(["Logistic Regression", "Random Forest"], [lr_kb, rf_kb], color=["#64748b", "#0f766e"])
    ax.set_ylabel("Serialized model size (KB)")
    ax.set_title("Logistic Regression vs Random Forest model size")
    save(fig, FIG / "lr_vs_rf_model_size.png")

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(["Logistic Regression", "Random Forest"], [lr_ms, rf_ms], color=["#64748b", "#0f766e"])
    ax.set_ylabel("Mean predict time on test set (ms)")
    ax.set_title("Logistic Regression vs Random Forest inference time")
    save(fig, FIG / "lr_vs_rf_predict_time.png")

    cm = e2e["confusion_matrix"]
    fig, ax = plt.subplots(figsize=(4.8, 4.2))
    mat = np.array([[cm["tp_phishing"], cm["fn_phishing"]], [cm["fp_phishing"], cm["tn_legitimate"]]])
    im = ax.imshow(mat, cmap="Blues")
    ax.set_xticks([0, 1], ["Pred phishing", "Pred legitimate"])
    ax.set_yticks([0, 1], ["True phishing", "True legitimate"])
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(mat[i, j]), ha="center", va="center")
    fig.colorbar(im, ax=ax, fraction=0.046)
    ax.set_title("Pipeline outcomes on controlled test cases (n=24)")
    save(fig, FIG / "e2e_confusion_matrix.png")

    rows = e2e["cases"]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    colors = ["#0f766e" if r["correct"] else "#b91c1c" for r in rows]
    ax.bar([r["id"] for r in rows], [r["latency_s"] * 1000 for r in rows], color=colors)
    ax.set_ylabel("Latency (ms)")
    ax.set_xlabel("Test case")
    ax.set_title("classify_url latency (green=correct, red=incorrect)")
    ax.tick_params(axis="x", rotation=45)
    save(fig, FIG / "e2e_latency.png")

    groups = [
        ("Heuristic IP/@", [r["latency_s"] for r in rows if r["deploy_path"] == "heuristic"]),
        ("Local HTML model", [r["latency_s"] for r in rows if r["deploy_path"] == "model" and not r["live"]]),
        ("Live HTTPS", [r["latency_s"] for r in rows if r["live"]]),
    ]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar([g[0] for g in groups], [float(np.mean(g[1]) * 1000) if g[1] else 0 for g in groups], color="#334155")
    ax.set_ylabel("Mean latency (ms)")
    ax.set_title("Mean pipeline latency by test group")
    save(fig, FIG / "e2e_latency_by_group.png")

    print("Wrote", len(list(FIG.glob('*.png'))), "PNGs to", FIG)


if __name__ == "__main__":
    main()
