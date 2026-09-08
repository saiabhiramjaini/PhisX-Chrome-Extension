#!/usr/bin/env python3
"""End-to-end evaluation: local fixture pages → feature extraction / heuristics → prediction.

This is the same classify_url() path the Chrome extension calls over HTTP.
Browser navigation is simulated by fetching each fixture URL (HTTP 200) then
classifying that URL, matching chrome.tabs.query + POST /predict.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path
from threading import Thread

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EVAL = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "Flask API"))

import inputScript  # noqa: E402
from app import classify_url  # noqa: E402
from test_server import make_server  # noqa: E402

PORT = 8765
OUT = EVAL / "results"
FIG = EVAL / "figures"
OUT.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)


def _stub_unreproducible_infra(url: str) -> int:
    """WHOIS/Alexa/Google index cannot be honestly instantiated on localhost."""
    return -1


def resolve_url(case: dict, port: int) -> str:
    host = case.get("host", "127.0.0.1")
    return case["url_template"].format(port=port, host=host)


def main() -> None:
    inputScript.Google_Index = _stub_unreproducible_infra
    inputScript.web_traffic = _stub_unreproducible_infra

    spec = json.loads((EVAL / "test_cases.json").read_text())
    server = make_server("127.0.0.1", PORT)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.2)

    rows = []
    try:
        for case in spec["cases"]:
            url = resolve_url(case, PORT)
            http_ok = None
            if not case.get("live"):
                try:
                    with urllib.request.urlopen(url.replace("paypal.com@", "").replace("appleid.apple.com@", ""), timeout=5) as resp:
                        http_ok = resp.status
                except Exception:
                    # @-URLs are not fetchable as written; GET the path on the IP host.
                    path = "/" + "/".join(url.split("/")[3:])
                    fetch = f"http://127.0.0.1:{PORT}{path}"
                    with urllib.request.urlopen(fetch, timeout=5) as resp:
                        http_ok = resp.status
            t0 = time.perf_counter()
            result = classify_url(url)
            elapsed = time.perf_counter() - t0
            pred = result["prediction"]
            expected = case["expected"]
            rows.append({
                "id": case["id"],
                "url": url,
                "expected": expected,
                "predicted": pred,
                "correct": pred == expected,
                "latency_s": elapsed,
                "deploy_path": result.get("path"),
                "http_status": http_ok,
                "live": bool(case.get("live")),
                "instantiated_features": case["instantiated_features"],
            })
            print(f"{case['id']} {pred == expected} {elapsed:.3f}s {pred}")
    finally:
        server.shutdown()

    y_true = [1 if r["expected"].startswith("Legit") else 0 for r in rows]
    y_pred = [1 if r["predicted"].startswith("Legit") else 0 for r in rows]
    # 0 = phishing, 1 = legitimate for this matrix
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)

    payload = {
        "n": len(rows),
        "n_phishing": sum(1 for r in rows if r["expected"].startswith("Phish")),
        "n_legitimate": sum(1 for r in rows if r["expected"].startswith("Legit")),
        "accuracy": sum(r["correct"] for r in rows) / len(rows),
        "phishing_recall": tp / (tp + fn) if (tp + fn) else None,
        "false_positive_rate": fp / (fp + tn) if (fp + tn) else None,
        "confusion_matrix": {
            "order": ["phishing", "legitimate"],
            "tp_phishing": tp,
            "fn_phishing": fn,
            "fp_phishing": fp,
            "tn_legitimate": tn,
        },
        "latency_s": {
            "mean": float(np.mean([r["latency_s"] for r in rows])),
            "p50": float(np.median([r["latency_s"] for r in rows])),
            "p95": float(np.percentile([r["latency_s"] for r in rows], 95)),
            "heuristic_mean": float(np.mean([r["latency_s"] for r in rows if r["deploy_path"] == "heuristic"] or [0])),
            "model_mean": float(np.mean([r["latency_s"] for r in rows if r["deploy_path"] == "model"] or [0])),
        },
        "limitations": [
            "Google Index and Alexa rank are not instantiated on localhost; extractors return -1 as in production failure mode.",
            "WHOIS/DNS age features similarly fail closed on synthetic hosts.",
            "Extension UI was not driven by Selenium; classify_url is the identical function behind POST /predict.",
            "Automated browser/extension driving remains future work.",
        ],
        "cases": rows,
    }
    (OUT / "e2e_metrics.json").write_text(json.dumps(payload, indent=2))

    def save(fig, path: Path) -> None:
        fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(4.8, 4.2))
    cm = np.array([[tp, fn], [fp, tn]])
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks([0, 1], ["Pred phishing", "Pred legitimate"])
    ax.set_yticks([0, 1], ["True phishing", "True legitimate"])
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center")
    fig.colorbar(im, ax=ax, fraction=0.046)
    ax.set_title("Pipeline outcomes on controlled test cases (n=24)")
    save(fig, FIG / "e2e_confusion_matrix.png")

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ids = [r["id"] for r in rows]
    colors = ["#0f766e" if r["correct"] else "#b91c1c" for r in rows]
    ax.bar(ids, [r["latency_s"] * 1000 for r in rows], color=colors)
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
    ax.bar(
        [g[0] for g in groups],
        [float(np.mean(g[1]) * 1000) if g[1] else 0 for g in groups],
        color="#334155",
    )
    ax.set_ylabel("Mean latency (ms)")
    ax.set_title("Mean pipeline latency by test group")
    save(fig, FIG / "e2e_latency_by_group.png")

    print(json.dumps({k: payload[k] for k in ("n", "accuracy", "phishing_recall", "false_positive_rate", "confusion_matrix", "latency_s")}, indent=2))


if __name__ == "__main__":
    main()
