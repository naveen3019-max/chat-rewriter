from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from flask import session
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
CORS(app)
MONGO_URI = os.getenv("MONGODB_URI")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
app.secret_key = os.getenv("SECRET_KEY")

client = MongoClient(MONGO_URI)
db = client["thinkfeelshare"]
users = db["users"]


genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash')

@app.route('/')
def landing():
    return render_template('login.html')

from flask import Flask, render_template

@app.route("/register")
def serve_register():
    return render_template("Register.html")

@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone", "")
    password = data.get("password")

    if users.find_one({"email": email}):
        return jsonify({"error": "User already exists"}), 400

    hashed_password = generate_password_hash(password)
    users.insert_one({
        "name": name,
        "email": email,
        "phone": phone,
        "password": hashed_password
    })

    return jsonify({"message": "Registration successful"}), 200

@app.route('/api/login', methods=['POST'])
def login_user():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    user = users.find_one({"email": email})
    if not user:
        return jsonify({"error": "User not found"}), 404

    if check_password_hash(user["password"], password):
        session["user_email"] = email  # ✅ Set session
        return jsonify({"message": "Login successful", "user": {"name": user["name"], "email": user["email"]}})
    else:
        return jsonify({"error": "Invalid password"}), 401



@app.route('/dashboard')
def dashboard():
    if "user_email" not in session:
        return redirect(url_for("landing"))  # redirect to login
    return render_template("dashboard.html")

@app.route('/api/me')
def get_user_profile():
    if "user_email" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user = users.find_one({"email": session["user_email"]})
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "name": user.get("name"),
        "email": user.get("email"),
        "phone": user.get("phone", ""),
        "bio": user.get("bio", "")
    })

@app.route('/api/update-profile', methods=['POST'])
def update_user_profile():
    if "user_email" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    old_email = session["user_email"]
    data = request.get_json()

    updates = {
        "name": data.get("name"),
        "phone": data.get("phone"),
        "bio": data.get("bio")
    }

    new_email = data.get("email")

    if new_email and new_email != old_email:
        if users.find_one({"email": new_email}):
            return jsonify({"error": "Email already in use"}), 400
        updates["email"] = new_email
        session["user_email"] = new_email  # 🔄 Update session

    if data.get("password"):
        updates["password"] = generate_password_hash(data["password"])

    users.update_one({"email": old_email}, {"$set": updates})

    return jsonify({"success": True})


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
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)

        translated_text = response.text.strip()
        print("✅ Translated text:", translated_text)

        return jsonify({"translated": translated_text})

    except Exception as e:
        print("❌ Translation error:", e)
        return jsonify({"translated": "Error translating."})
    



@app.route('/api/story-write', methods=['POST'])
def story_write():
    try:
        data = request.get_json()
        prompt = data.get("prompt", "").strip()

        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400

        # 🧠 Gemini Prompt
        story_prompt = f"""
        Write a creative and engaging story based on the following idea:
        "{prompt}"

        The story should be between 5 to 10 sentences.
        Make it feel realistic and compelling.
        """

        response = model.generate_content(story_prompt)
        story_text = response.text.strip()

        return jsonify({ "story": story_text })

    except Exception as e:
        print("❌ Story generation failed:", e)
        return jsonify({ "error": "Story generation failed." }), 500
    


@app.route('/api/generate-content', methods=['POST'])
def generate_content():
    try:
        data = request.get_json()
        prompt = data.get("prompt", "")

        content_prompt = f"""
        Based on the following input, generate a professional, informative, and engaging piece of content:
        "{prompt}"
        Length: 4-7 sentences. Use clear and natural language.
        """

        response = model.generate_content(content_prompt)
        content_text = response.text.strip()

        return jsonify({ "content": content_text })

    except Exception as e:
        print("❌ Error generating content:", e)
        return jsonify({ "error": "Content generation failed." }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # PORT is set by Render
    app.run(host="0.0.0.0", port=port)
