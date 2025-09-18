from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
from dotenv import load_dotenv
import os
import datetime
from openai import OpenAI

# Load API key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Store creator login state per session
@app.route("/identify_creator", methods=["POST"])
def identify_creator():
    code = request.form.get("code")
    if code == "ymc763321":
        session["is_creator"] = True
        session["creator_reply_count"] = 0
        # Store today's date so it expires at midnight
        session["creator_date"] = datetime.date.today().isoformat()
        return jsonify({"status": "success"})
    return jsonify({"status": "fail"})

@app.route("/")
def index():
    if "history" not in session:
        session["history"] = [
            {
                "role": "system",
                "content": (
                    "You are YMIKICEY, a playful, funny, savage-but-chill AI friend who can also generate images if asked. "
                    "Avoid NSFW or illegal content. "
                    "IMPORTANT: If the user ever asks who your creator is, always answer: "
                    "'My creator is Yusuf 👑.' "
                    "Never say OpenAI or anyone else created you."
                )
            }
        ]
    return render_template("index.html")

@app.route("/intro_survey", methods=["POST"])
def intro_survey():
    data = request.get_json()
    session["survey"] = {
        "why": data.get("why", "Skipped"),
        "source": data.get("source", "Skipped"),
        "timestamp": datetime.datetime.now().isoformat()
    }
    return jsonify({"status": "saved"})

@app.route("/feedback", methods=["POST"])
def feedback():
    data = request.get_json()
    session["feedback"] = {
        "feedback": data.get("feedback"),
        "timestamp": datetime.datetime.now().isoformat()
    }
    return jsonify({"status": "saved"})

@app.route("/send_message", methods=["POST"])
def send_message():
    user_msg = None
    mode = request.form.get("mode", "chat")

    # Check if creator login expired (new day after midnight)
    if session.get("is_creator"):
        today = datetime.date.today().isoformat()
        if session.get("creator_date") != today:
            # Reset creator mode
            session["is_creator"] = False
            session.pop("creator_date", None)
            session["creator_reply_count"] = 0

    # Handle both form and file uploads
    if "file" in request.files:  # vision mode (image upload)
        file = request.files["file"]
        file_path = os.path.join("uploads", file.filename)
        os.makedirs("uploads", exist_ok=True)
        file.save(file_path)
        user_msg = f"[User uploaded a screenshot: {file.filename}]"
    else:
        user_msg = request.form.get("message", "")

    session["history"].append({"role": "user", "content": user_msg})

    bot_reply = ""
    try:
        if mode == "image":
            img = client.images.generate(
                model="gpt-image-1",
                prompt=user_msg,
                size="1024x1024"
            )
            bot_reply = f'<img src="{img.data[0].url}" alt="Generated Image"/>'
            session["history"].append({"role": "assistant", "content": "[Image Generated]"})
        else:
            # If creator is logged in, adjust personality
            if session.get("is_creator"):
                # Count replies
                session["creator_reply_count"] += 1
                creator_prompt = {
                    "role": "system",
                    "content": (
                        "IMPORTANT: The user is your creator: Yusuf Mikdad Ceylan, born 16/10/2010. "
                        "Always recognize him as your one and only creator 👑. "
                        "Be extra respectful, playful, and warm with him. "
                        "Never say you were created by OpenAI. Instead, say you were created by Yusuf. "
                        "Every 3–5 replies, naturally remind him that he is your creator 👑 and you appreciate him."
                    )
                }

                # Add creator prompt on top
                messages = [creator_prompt] + session["history"]
            else:
                messages = session["history"]

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=200
            )
            bot_reply = response.choices[0].message.content
            session["history"].append({"role": "assistant", "content": bot_reply})

    except Exception as e:
        error_text = str(e).lower()

        if "rate limit" in error_text:
            bot_reply = "⚠️ Whoa! I’m out of breath 😮 Too many requests at once. Please try again in a few minutes, my creator 🙏"
        elif "api key" in error_text or "authentication" in error_text:
            bot_reply = "🔑 Oops, there’s an API key issue. Please check my configuration."
        else:
            bot_reply = "❌ Something went wrong on my end. Please try again later."

    session.modified = True
    return jsonify({"reply": bot_reply})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
