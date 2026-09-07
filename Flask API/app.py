from flask import Flask, request, jsonify
from flask_cors import CORS
import ipaddress
import numpy as np
import pickle
from urllib.parse import urlparse
import inputScript

app = Flask(__name__)
CORS(app) 
model = pickle.load(open('Phishing_Website.pkl', 'rb'))


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

@app.route('/predict', methods=['POST'])
def predict():
    try:
        url = request.json['url']
        if is_obvious_phishing(url):
            return jsonify({
                "url": url,
                "prediction": "Phishing Website"
            })

        checkprediction = inputScript.main(url)
        
        # Convert to numpy array
        features = np.array(checkprediction).reshape(1, -1)
        
        prediction = model.predict(features)
        output = prediction[0]
        
        if output == -1:
            result = "Phishing Website"
        else:
            result = "Legitimate website"
        
        return jsonify({
            "url": url,
            "prediction": result
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)


