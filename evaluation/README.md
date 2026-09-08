# Evaluation

Regenerates the dissertation figures and JSON.

```bash
cd "../Flask API"
source myenv/bin/activate
pip install matplotlib
python ../evaluation/evaluate_offline.py
python ../evaluation/evaluate_e2e.py
```

- `test_cases.json` — labelled fixtures and which UCI properties they instantiate
- `test_server.py` — HTTP server on port 8765
- `results/` — metrics JSON
- `figures/` — PNGs for Chapter 4 and slides
- `DISSERTATION_CORRECTIONS.md` — text to paste into the report
- `PRESENTATION_OUTLINE.md` — slide order
