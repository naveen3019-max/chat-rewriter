from flask import Flask, render_template
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/rewrite', methods=['POST'])
def rewrite_all():
    data = request.json
    message = data.get("message", "")
    prompt = f"""
You are an AI assistant that helps users improve their written messages.
Given the user's message, provide three improved versions:
1. A polite version
2. A casual version
3. A positive and friendly version

Format your response like this:
Polite: <polite version>
Casual: <casual version>
Positive: <positive version>

User Message: "{message}"
"""

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        print("Gemini Raw Response:", response.text)
        return jsonify({"rewritten": response.text})
    except Exception as e:
        print("Gemini Error:", e)
        return jsonify({"rewritten": f"Error: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(debug=True)
