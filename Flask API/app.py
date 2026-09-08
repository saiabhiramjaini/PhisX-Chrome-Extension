from flask import Flask, request, jsonify
from flask_cors import CORS
import ipaddress
import numpy as np
import pickle
from pathlib import Path
from urllib.parse import urlparse
import inputScript

app = Flask(__name__)
CORS(app)

ROOT = Path(__file__).resolve().parent
model = pickle.load(open(ROOT / "Phishing_Website.pkl", "rb"))


def is_obvious_phishing(url):
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if parsed.username or "@" in (parsed.netloc or ""):
        return True
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        pass
    if inputScript.Shortining_Service(url) == -1:
        return True
    return False

def classify_url(url):
    if is_obvious_phishing(url):
        return {
            "url": url,
            "prediction": "Phishing Website",
            "path": "heuristic",
        }

    checkprediction = inputScript.main(url)
    features = np.array(checkprediction).reshape(1, -1)
    output = model.predict(features)[0]
    result = "Phishing Website" if output == -1 else "Legitimate website"
    return {
        "url": url,
        "prediction": result,
        "path": "model",
    }


@app.route('/predict', methods=['POST'])
def predict():
    try:
        url = request.json['url']
        return jsonify(classify_url(url))
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)


