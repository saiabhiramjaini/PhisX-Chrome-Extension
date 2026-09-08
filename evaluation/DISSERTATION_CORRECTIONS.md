# PhisX dissertation and presentation corrections

Paste these sections into the report and slides. Numbers come from `evaluation/results/` generated on 8 Sep 2026 (`python evaluation/evaluate_offline.py` and `python evaluation/evaluate_e2e.py`). Figures are in `evaluation/figures/`.

Insert figures:

- `evaluation/figures/offline_model_comparison.png`
- `evaluation/figures/offline_confusion_matrices.png`
- `evaluation/figures/lr_vs_rf_tradeoff.png`
- `evaluation/figures/e2e_confusion_matrix.png`
- `evaluation/figures/e2e_latency.png`

---

## Literature review (soften wording)

Do **not** write that machine learning is always superior to static blocklists.

Replace with: blocklists remain effective against **known** phishing URLs and domains. Their limitation is delay and coverage for **previously unseen** sites. Supervised classifiers are therefore best described as a **complement**: they attempt to generalise from URL and page features to sites that are not yet listed. PhisX is motivated by that complementary role, not by replacing Safe Browsing or vendor feeds.

---

## Ethics form

The dissertation uses the **UCI Phishing Websites** dataset (11,055 labelled instances, 30 features). The ethics form must not answer “No” to use of existing datasets. Align the form with the approved application: **Yes — existing public dataset (UCI)**. No personal browsing logs were collected for training. End-to-end tests used **locally hosted fixture pages** plus three well-known public homepages (Wikipedia, Google, GitHub), not live criminal phishing kits.

---

## Privacy of the deployed architecture

The Chrome extension sends the **active tab URL** to a prediction API (`POST /predict`). In the AWS deployment that means a server operator **can observe browsing destinations** even if URL strings are not written to a database: they appear in application logs, reverse-proxy logs, TLS termination logs, and memory during feature extraction (the extractor may **fetch the page**, WHOIS, and related resources).

Mitigations that must be stated:

- Transport: HTTPS on the public API (local development uses HTTP to `127.0.0.1`).
- Data minimisation: the JSON body is `{ "url": ... }` only; no cookies, HTML, or credentials from the page are uploaded by the extension itself.
- Retention: production should disable verbose access logs of full URLs or set a short retention; this must be configured on the host, not assumed.
- Residual risk: feature extraction still **contacts the target website** from the server, so the user’s visit can be correlated in time.

Future work: **on-device inference** (bundle the model in the extension or a native host) so URLs never leave the browser. That trades privacy for the inability to run WHOIS/page fetches in the same way, unless a local extractor is used.

---

## Why UCI features are not “just a URL string”

The UCI Phishing Websites dataset encodes 30 attributes in {−1, 0, 1}. Only some are lexical properties of the URL. The deployed API (`Flask API/inputScript.py`) **recomputes** each attribute from a live URL. Generated tests therefore had to **instantiate** a subset of those properties; infrastructure features cannot be faked honestly on localhost.

| UCI feature | What it describes | How the API recomputes it | How the controlled test instantiated it |
| --- | --- | --- | --- |
| having_IP | IP used as hostname | Parse hostname / regex | Phishing cases use `127.0.0.1` |
| URL_Length | Length thresholds 54 / 75 | `len(url)` | Long paths on P03 |
| Shortining_Service | Known shortener hosts | Regex on URL | Not used in local fixtures (would short-circuit heuristics) |
| having_At_Symbol | `@` in URL | Regex | P09–P10 `user@host` URLs |
| double_slash_redirecting | Extra `//` in path | Scan after index 8 | Not varied |
| Prefix_Suffix | Hyphen in domain | `tldextract` | Not used as the primary factor (IP/HTML used instead) |
| having_Sub_Domain | Dots in subdomain | `tldextract` | localhost vs none |
| SSLfinal_State | Valid HTTPS | HTTPS + `requests` verify | Local fixtures are **all HTTP** (−1), held constant; L07–L09 are live HTTPS |
| Domain_registeration_length, age_of_domain, Abnormal_URL | WHOIS | `python-whois` | Cannot instantiate on localhost; extractor returns −1 |
| Favicon, port, Request_URL, URL_of_Anchor, Links_in_tags, Submitting_to_email, on_mouseover, RightClick, Iframe, Links_pointing_to_page | Page HTML / network | Fetch page, BeautifulSoup | Phishing HTML: iframe, mailto, foreign anchors, external img; legit HTML: same-origin links, no iframe |
| SFH, popUpWidnow, Page_Rank | Stubs in code | Constant −1 / 1 | Documented limitation |
| Redirect | `requests` history | GET URL | Local 200, no redirect chain |
| DNSRecord, web_traffic, Google_Index, Statistical_report | DNS / Alexa / Google | Network | **Not instantiated** in local eval; Google Index and Alexa stubbed to −1 for reproducibility (Alexa data API is defunct; Google search is unstable) |

**Implication:** the 91.72% Logistic Regression (and 96.97% Random Forest) accuracies are measured in the **UCI feature space** (precomputed columns). The extension test measures the **extractor + heuristics + LR pickle** on synthetic pages. Those are related but not identical experiments. Alejandro’s warning applies: do not claim the UCI accuracy *is* the extension accuracy.

---

## Offline model evaluation (Chapter 4)

Dataset: UCI Phishing Websites, *n* = 11,055, 30 features after dropping the index column. Split: 80/20, `random_state=0`, test *n* = 2,211. Positive class = phishing (−1).

| Algorithm | Accuracy | Precision (phish) | Recall (phish) | F1 (phish) | FNR | FPR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Logistic Regression | 91.72% | 92.35% | 89.35% | 90.83% | 10.65% | 6.27% |
| K-NN | 94.35% | 95.50% | 92.01% | 93.72% | 7.99% | 3.68% |
| SVM | 94.08% | 94.91% | 92.01% | 93.44% | 7.99% | 4.18% |
| Naive Bayes | 61.51% | 54.37% | 100% | 70.44% | 0% | 71.09% |
| Decision Tree | 96.29% | 96.88% | 94.97% | 95.92% | 5.03% | 2.59% |
| Random Forest | 96.97% | 98.27% | 95.07% | 96.64% | 4.93% | 1.42% |

Logistic Regression confusion matrix (test): TP 906, FN 108, FP 75, TN 1122.

Random Forest confusion matrix (test): TP 964, FN 50, FP 17, TN 1180.

Naive Bayes’s perfect phishing recall is not useful: it flags most legitimate sites (FPR 71%). Accuracy alone would hide that.

### Logistic Regression vs Random Forest (quantitative)

Same test set, 30 timed `predict` calls:

| | Logistic Regression | Random Forest |
| --- | ---: | ---: |
| Accuracy | 91.72% | 96.97% |
| Phishing recall | 89.35% | 95.07% |
| FPR | 6.27% | 1.42% |
| Serialized size | 1.1 KB | 20.0 MB |
| Mean predict time (2,211 rows) | 0.31 ms | 43.9 ms |

Random Forest is stronger on detection quality. Logistic Regression is ~18,000× smaller and ~140× faster on a batch of 2,211 rows. Train vs test gap is **1.46 pp** for LR vs **2.06 pp** for unconstrained RF (5-fold CV 92.28% vs 96.92%). PhisX **deploys Logistic Regression** (`Phishing_Website.pkl`): the API already spends seconds on page/WHOIS fetches, so forest accuracy is not required for a first deployed prototype, and LR is easier to justify against overfitting. RF remains the comparison model in Chapter 4; it is **not** the pickle served by `/predict`.

---

## Controlled test environment

Architecture:

```
Chrome (unpacked PhisX)  →  POST /predict (Flask)  →  heuristics and/or inputScript + pickle
                                      ↑
                         local HTTP fixtures :8765
                         127.0.0.1  = phishing host (IP)
                         localhost  = legitimate / HTML-contrast host
```

Protocol (repeatable):

1. `python evaluation/test_server.py` is started from `evaluate_e2e.py` on `127.0.0.1:8765`.
2. Each case in `evaluation/test_cases.json` is fetched (HTTP 200) then passed to `classify_url()`, the same function as the Flask route the extension calls.
3. Expected labels are assigned a priori (IP/`@` lexical phishing; phishing HTML vs clean library HTML; three live HTTPS homepages).
4. No live criminal phishing sites were used.

Automation: this run is **scripted API/pipeline evaluation**, not Selenium driving the popup. Limitation / future work: Playwright with `--load-extension` to click the toolbar icon and screenshot the popup.

---

## End-to-end pipeline results

24 cases: 15 phishing, 9 legitimate.

| | Predicted phishing | Predicted legitimate |
| --- | ---: | ---: |
| True phishing | 15 | 0 |
| True legitimate | 0 | 9 |

Accuracy 100%, phishing recall 100%, FPR 0% **on this fixture set**.

Latency: heuristic cases ~0.03 ms; local model cases ~40–120 ms; live HTTPS Wikipedia/Google/GitHub ~6.8–8.4 s (page fetch + WHOIS). Mean 0.95 s, median 37 ms, p95 ~7.1 s.

**Do not present 100% as the system accuracy.** Ten phishing cases are IP/`@` heuristics by construction; local HTML contrast is a small handmade sample; live pages are famous legitimate sites. The result shows the **deployed path works end-to-end** and that lexical high-precision rules fire, not that the extractor matches UCI’s 96.97% in the wild.

Success examples: P01 (`http://127.0.0.1:8765/phish/paypal-login`) heuristic IP; L07 Wikipedia HTTPS model path.

Failure modes to discuss even if none occurred here: HTTP legitimate intranet sites look like UCI “bad SSL”; Google_Index/WHOIS noise; shorteners always heuristic-phishing (may include legitimate `bit.ly`).

---

## Conclusions mapped to objectives

1. **Select a labelled URL dataset** — Achieved: UCI Phishing Websites, documented ethics use.
2. **Train and compare classifiers** — Achieved: six models with precision/recall/F1/FNR/FPR, not accuracy only. RF highest quality; **LR deployed**; NB unsuitable despite 100% recall.
3. **Serve the model via an API** — Achieved: Flask `/predict` with CORS; local and previously AWS-hosted.
4. **Chrome extension real-time check** — Partially achieved: extension sends the tab URL and renders the API label. Systematic **UI automation** of the popup is not done; pipeline evaluation of 24 controlled cases is.
5. **Protect users without using live phishing crimeware** — Achieved for evaluation via local HTTP fixtures.

---

## Presentation story (required slide order)

1. Problem and complementary role vs blocklists  
2. UCI dataset and feature types (lexical vs page vs infrastructure)  
3. Offline comparison table + confusion matrices  
4. RF vs LR size/time/quality → deployment choice  
5. Architecture: extension → API → extractor  
6. Privacy: URL leaves the browser  
7. Controlled fixtures (IP vs localhost, HTML templates)  
8. E2E confusion matrix + latency bar chart  
9. Success/failure examples and limitations  
10. Conclusions vs objectives + future on-device inference  

---

## How to regenerate numbers

```bash
cd "Flask API"
source myenv/bin/activate
pip install -r requirements.txt
pip install matplotlib
python ../evaluation/evaluate_offline.py
python ../evaluation/evaluate_e2e.py
```
