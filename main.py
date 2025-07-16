from flask import Flask, request, jsonify
import sqlite3
import os

app = Flask(__name__)
DB_PATH = "toxicity_logs.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            comment TEXT,
            transliterated TEXT,
            prediction TEXT,
            confidence REAL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def home():
    return "✅ Toxicity Logger API on Render is Running!"

@app.route("/log", methods=["POST"])
def log_comment():
    data = request.json
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO comments (comment, transliterated, prediction, confidence)
            VALUES (?, ?, ?, ?)
        ''', (data["comment"], data["transliterated"], data["prediction"], data["confidence"]))
        conn.commit()
        conn.close()
        return jsonify({"message": "Logged ✅"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/logs", methods=["GET"])
def get_logs():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT comment, transliterated, prediction, confidence FROM comments")
    rows = c.fetchall()
    conn.close()
    return jsonify(rows)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
