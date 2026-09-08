# Presentation outline (copy onto slides)

Use the figures in `figures/`. Keep one claim per slide.

1. **PhisX in one sentence** — Chrome popup sends the tab URL to an API that classifies phishing vs legitimate.
2. **Blocklists vs ML** — ML complements lists for unseen sites; it is not always better.
3. **UCI data** — 11,055 rows, 30 features, phishing = −1.
4. **Offline results** — show `offline_model_comparison.png`. Call out Naive Bayes FPR 71%.
5. **Confusion matrices** — `offline_confusion_matrices.png`.
6. **Why LR is deployed** — `lr_vs_rf_model_size.png` and `lr_vs_rf_predict_time.png`: RF is more accurate; LR is ~1 KB, smaller train/test gap, used in `Phishing_Website.pkl`.
7. **Architecture** — extension → HTTPS API → recompute features → model.
8. **Privacy** — every URL can be logged; future local inference.
9. **Test fixtures** — local HTTP server; `127.0.0.1` phishing host; `localhost` legit host.
10. **Feature honesty** — WHOIS/Google/Alexa not faked; table in DISSERTATION_CORRECTIONS.md.
11. **E2E matrix** — `e2e_confusion_matrix.png` (15/15 phish, 9/9 legit on n=24).
12. **Latency** — `e2e_latency.png`; heuristics instant; live HTTPS ~7 s.
13. **Limitations** — n=24 is a protocol demo; not UCI accuracy; no Selenium popup test.
14. **Objectives recap** — dataset, models, API, extension, ethical testing.
15. **Future** — Playwright extension tests; on-device model.
