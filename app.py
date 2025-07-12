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
from flask_socketio import SocketIO, emit, join_room
import datetime

load_dotenv()

app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading',cors_allowed_origins="*")

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
        session["user_email"] = email
        session["phone"] = user["phone"]  # ✅ Now properly indented
        return jsonify({
            "message": "Login successful",
            "user": {
                "name": user["name"],
                "email": user["email"],
                "phone": user.get("phone", "")
            }
        })
    else:
        return jsonify({"error": "Invalid password"}), 401


@app.route('/dashboard')
def dashboard():
    if "user_email" not in session:
        return redirect(url_for("landing"))  # redirect to login
    return render_template("dashboard.html")

from flask_socketio import SocketIO, emit, join_room

socketio = SocketIO(app, cors_allowed_origins="*")

@socketio.on('join')
def handle_join(data):
    phone = data.get('phone')
    if phone:
        join_room(phone)
        print(f"User joined room: {phone}")

@socketio.on('send_message')
def handle_send_message(data):
    from_phone = data.get("from")
    to_phone = data.get("to")
    message = data.get("message")

    # Save to DB
    db.messages.insert_one({
        "from": from_phone,
        "to": to_phone,
        "message": message,
        "timestamp": datetime.datetime.utcnow()
        "deleted_for": [] 
    })

    # Emit to recipient room
    socketio.emit('receive_message', {"from": from_phone, "message": message}, room=to_phone)


@app.route('/api/messages/<target_phone>', methods=['GET'])
def get_messages(target_phone):
    current_user = get_logged_in_user()  # however you identify logged-in user
    current_phone = current_user.get('phone')

    chat = list(db.messages.find({
        "$or": [
            {"from": current_phone, "to": target_phone},
            {"from": target_phone, "to": current_phone}
        ],
         "deleted_for": { "$ne": current_phone }
    }, {"_id": 0}).sort("timestamp", 1))  # sort by time

    return jsonify({"chat": chat})

def get_logged_in_user():
    phone = session.get("phone")
    if not phone:
        return None

    return db.users.find_one({"phone": phone})



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


@app.route('/api/quick-draft', methods=['POST'])
def quick_draft():
    try:
        data = request.get_json()
        intent = data.get("intent", "").lower().strip()

        if not intent:
            return jsonify({"error": "Intent is required"}), 400

        prompt = f"""
You are an AI assistant helping users write messages.

The user wants to send a message with the following intent: "{intent}"

Generate 3 distinct message drafts that fit this intent.
Use a friendly, human-like tone. Make each draft different in style (e.g. friendly, apologetic, direct).

Only return the 3 messages. Format:
1. <Message 1>
2. <Message 2>
3. <Message 3>
"""

        response = model.generate_content(prompt)
        if not response or not response.text:
            return jsonify({"error": "AI returned no result"}), 500

        lines = response.text.strip().split("\n")
        suggestions = [line[3:].strip() for line in lines if line.strip().startswith(("1.", "2.", "3."))]

        return jsonify({"drafts": suggestions})

    except Exception as e:
        print("❌ Quick Draft Error:", e)
        return jsonify({"error": "Failed to generate drafts"}), 500



@app.route('/api/smart-reply', methods=['POST'])
def smart_reply():
    try:
        data = request.get_json()
        last_message = data.get("message", "").strip()

        if not last_message:
            return jsonify({"error": "Message is required"}), 400

        prompt = f"""
You are an AI assistant that generates smart, human-like replies.

Context: The user received the following message:
"{last_message}"

Generate 3 possible replies that are:
1. Friendly and natural
2. Slightly humorous or casual
3. A bit apologetic or thoughtful

Return only the replies like this:
1. <Reply One>
2. <Reply Two>
3. <Reply Three>
"""

        response = model.generate_content(prompt)
        if not response or not response.text:
            return jsonify({"error": "No response"}), 500

        lines = response.text.strip().split("\n")
        replies = [line[3:].strip() for line in lines if line.strip().startswith(("1.", "2.", "3."))]

        return jsonify({"replies": replies})

    except Exception as e:
        print("❌ Smart Reply Error:", e)
        return jsonify({"error": "Failed to generate smart replies"}), 500


@app.route('/api/delete-chat', methods=['POST'])
def delete_chat():
    if "phone" not in session or not request.json:
        return jsonify({"error": "Unauthorized"}), 401

    user_phone = session["phone"]
    target_phone = request.json.get("target")

    # Mark all messages between the two users as deleted for this user
    db.messages.update_many(
        {
            "$or": [
                {"from": user_phone, "to": target_phone},
                {"from": target_phone, "to": user_phone}
            ]
        },
        {"$addToSet": {"deleted_for": user_phone}}  # ✅ Only hides for current user
    )

    return jsonify({"success": True, "message": "Chat hidden for you."})



if __name__ == '__main__':
    socketio.run(app, debug=True)
