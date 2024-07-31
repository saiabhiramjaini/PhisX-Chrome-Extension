from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import pickle
import inputScript

app = Flask(__name__)
CORS(app) 
model = pickle.load(open('Phishing_Website.pkl', 'rb'))

@app.route('/predict', methods=['POST'])
def predict():
    try:
        url = request.json['url']
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
    app.run(debug=True)


