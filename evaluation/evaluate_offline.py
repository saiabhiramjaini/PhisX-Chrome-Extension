#!/usr/bin/env python3
"""Offline classifier evaluation for the dissertation results chapter."""

from __future__ import annotations

import json
import time
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "model training" / "phishing.csv"
OUT = Path(__file__).resolve().parent / "results"
FIG = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)

# Positive class = phishing (-1), matching the detection task.
POS = -1


def metrics_block(y_true, y_pred) -> dict:
    cm = confusion_matrix(y_true, y_pred, labels=[-1, 1])
    tp, fn = int(cm[0, 0]), int(cm[0, 1])
    fp, tn = int(cm[1, 0]), int(cm[1, 1])
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_phishing": float(precision_score(y_true, y_pred, pos_label=POS, zero_division=0)),
        "recall_phishing": float(recall_score(y_true, y_pred, pos_label=POS, zero_division=0)),
        "f1_phishing": float(f1_score(y_true, y_pred, pos_label=POS, zero_division=0)),
        "false_negative_rate": float(fn / (tp + fn) if (tp + fn) else 0.0),
        "false_positive_rate": float(fp / (fp + tn) if (fp + tn) else 0.0),
        "confusion_matrix": {
            "labels": ["phishing (-1)", "legitimate (1)"],
            "matrix": cm.tolist(),
            "tp_phishing": tp,
            "fn_phishing": fn,
            "fp_phishing": fp,
            "tn_legitimate": tn,
        },
    }


def main() -> None:
    df = pd.read_csv(CSV)
    X = df.iloc[:, 1:-1].values
    y = df.iloc[:, -1].values
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=0
    )

    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000),
        "K-NN": KNeighborsClassifier(),
        "SVM": SVC(),
        "Naive Bayes": GaussianNB(),
        "Decision Tree": DecisionTreeClassifier(random_state=0),
        "Random Forest": RandomForestClassifier(n_estimators=200, random_state=0),
    }

    all_metrics = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        all_metrics[name] = metrics_block(y_test, y_pred)

    lr = models["Logistic Regression"]
    rf = models["Random Forest"]
    lr_path = OUT / "logistic_regression.joblib"
    rf_path = OUT / "random_forest.joblib"
    joblib.dump(lr, lr_path)
    joblib.dump(rf, rf_path)

    reps = 30
    lr_times, rf_times = [], []
    for _ in range(reps):
        t0 = time.perf_counter()
        lr.predict(X_test)
        lr_times.append(time.perf_counter() - t0)
        t0 = time.perf_counter()
        rf.predict(X_test)
        rf_times.append(time.perf_counter() - t0)

    tradeoff = {
        "test_rows": int(len(X_test)),
        "logistic_regression": {
            "model_size_bytes": lr_path.stat().st_size,
            "mean_predict_seconds": float(np.mean(lr_times)),
            "std_predict_seconds": float(np.std(lr_times)),
            **{k: all_metrics["Logistic Regression"][k] for k in ("accuracy", "recall_phishing", "false_positive_rate")},
        },
        "random_forest": {
            "model_size_bytes": rf_path.stat().st_size,
            "mean_predict_seconds": float(np.mean(rf_times)),
            "std_predict_seconds": float(np.std(rf_times)),
            **{k: all_metrics["Random Forest"][k] for k in ("accuracy", "recall_phishing", "false_positive_rate")},
        },
    }

    payload = {
        "dataset": str(CSV),
        "n_rows": int(len(df)),
        "n_features": int(X.shape[1]),
        "split": "test_size=0.2, random_state=0, features exclude index column",
        "positive_class": "phishing encoded as -1",
        "models": all_metrics,
        "deployment_tradeoff": tradeoff,
    }
    (OUT / "offline_metrics.json").write_text(json.dumps(payload, indent=2))

    names = list(all_metrics)

    def slug(name: str) -> str:
        return name.lower().replace(" ", "_").replace("-", "_")

    def save(fig, path: Path) -> None:
        fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
        plt.close(fig)

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
        vals = [all_metrics[n][key] for n in names]
        ax.barh(names, vals, color="#334155")
        ax.set_title(title)
        ax.set_xlim(0, 1)
        ax.set_xlabel("Score")
        ax.set_ylabel("Model")
        save(fig, FIG / f"{filename}.png")

    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    for ax, (key, title, _) in zip(axes.ravel(), series[:4]):
        vals = [all_metrics[n][key] for n in names]
        ax.barh(names, vals, color="#334155")
        ax.set_title(title)
        ax.set_xlim(0, 1)
        ax.set_xlabel("Score")
    fig.suptitle("Offline model comparison on UCI test set (n=%d)" % len(y_test))
    save(fig, FIG / "offline_model_comparison.png")

    for name in names:
        cm = np.array(all_metrics[name]["confusion_matrix"]["matrix"])
        fig, ax = plt.subplots(figsize=(4.8, 4.2))
        im = ax.imshow(cm, cmap="Blues")
        ax.set_title(f"{name} confusion matrix (UCI test)")
        ax.set_xticks([0, 1], ["Pred phishing", "Pred legitimate"])
        ax.set_yticks([0, 1], ["True phishing", "True legitimate"])
        for i in range(2):
            for j in range(2):
                ax.text(j, i, str(cm[i, j]), ha="center", va="center", color="black")
        fig.colorbar(im, ax=ax, fraction=0.046)
        save(fig, FIG / f"cm_{slug(name)}.png")

    fig, axes = plt.subplots(2, 3, figsize=(12, 7))
    for ax, name in zip(axes.ravel(), names):
        cm = np.array(all_metrics[name]["confusion_matrix"]["matrix"])
        im = ax.imshow(cm, cmap="Blues")
        ax.set_title(name, fontsize=9)
        ax.set_xticks([0, 1], ["Pred phish", "Pred legit"], fontsize=7)
        ax.set_yticks([0, 1], ["True phish", "True legit"], fontsize=7)
        for i in range(2):
            for j in range(2):
                ax.text(j, i, str(cm[i, j]), ha="center", va="center", color="black")
    fig.colorbar(im, ax=axes.ravel().tolist(), fraction=0.02)
    fig.suptitle("Confusion matrices on held-out UCI test set (n=%d)" % len(y_test))
    save(fig, FIG / "offline_confusion_matrices.png")

    lr_size = tradeoff["logistic_regression"]["model_size_bytes"] / 1024
    rf_size = tradeoff["random_forest"]["model_size_bytes"] / 1024
    lr_ms = tradeoff["logistic_regression"]["mean_predict_seconds"] * 1000
    rf_ms = tradeoff["random_forest"]["mean_predict_seconds"] * 1000

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(["Logistic Regression", "Random Forest"], [lr_size, rf_size], color=["#64748b", "#0f766e"])
    ax.set_ylabel("Serialized model size (KB)")
    ax.set_title("Logistic Regression vs Random Forest model size")
    save(fig, FIG / "lr_vs_rf_model_size.png")

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(["Logistic Regression", "Random Forest"], [lr_ms, rf_ms], color=["#64748b", "#0f766e"])
    ax.set_ylabel("Mean predict time on test set (ms)")
    ax.set_title("Logistic Regression vs Random Forest inference time")
    save(fig, FIG / "lr_vs_rf_predict_time.png")

    fig, ax = plt.subplots(figsize=(7, 4))
    labels = ["Model size (KB)", "Predict time on test set (ms)"]
    x = np.arange(len(labels))
    ax.bar(x - 0.18, [lr_size, lr_ms], 0.36, label="Logistic Regression", color="#64748b")
    ax.bar(x + 0.18, [rf_size, rf_ms], 0.36, label="Random Forest", color="#0f766e")
    ax.set_xticks(x, labels)
    ax.set_ylabel("Value")
    ax.set_title("Deployment trade-off (same test split)")
    ax.legend()
    save(fig, FIG / "lr_vs_rf_tradeoff.png")

    print(json.dumps({n: {k: round(all_metrics[n][k], 4) for k in ("accuracy", "precision_phishing", "recall_phishing", "f1_phishing", "false_negative_rate", "false_positive_rate")} for n in names}, indent=2))
    print("Wrote", OUT / "offline_metrics.json")


if __name__ == "__main__":
    main()
