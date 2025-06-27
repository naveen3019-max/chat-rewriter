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


@app.route('/api/autocorrect', methods=['POST'])
def autocorrect():
    data = request.json
    message = data.get("message", "")

    prompt = f"""
You are a helpful assistant. Correct the grammar and punctuation of the following message, but keep the meaning and tone.

Message: "{message}"
Corrected:
"""

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        return jsonify({"corrected": response.text.strip()})
    except Exception as e:
        print("Gemini error:", e)
        return jsonify({"corrected": message})  # fallback: original


@app.route('/api/translate', methods=['POST'])
def translate():
    data = request.json
    message = data.get("message", "")
    language = data.get("language", "Spanish")

    prompt = f"""
Translate the following message into {language}.
Only return the translated version. Do not explain or repeat the original.

Message: {message}
"""

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)

        translated_text = response.text.strip()
        print("✅ Translated text:", translated_text)

        return jsonify({"translated": translated_text})

    except Exception as e:
        print("❌ Translation error:", e)
        return jsonify({"translated": "Error translating."})


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
