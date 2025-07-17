from flask import Flask, request, jsonify, render_template_string, Response
import mysql.connector
import os
from dotenv import load_dotenv
from functools import wraps
import csv
from io import StringIO

load_dotenv()

app = Flask(__name__)

# ✅ Database config with utf8mb4 charset
db_config = {
    'host': os.getenv("MYSQL_HOST"),
    'user': os.getenv("MYSQL_USER"),
    'password': os.getenv("MYSQL_PASSWORD"),
    'database': os.getenv("MYSQL_DATABASE"),
    'port': int(os.getenv("MYSQL_PORT", 3306)),
    'charset': 'utf8mb4'
}

# ✅ Ensure logs table exists
def init_db():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            comment TEXT,
            transliterated TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
            prediction VARCHAR(20),
            confidence FLOAT
        ) CHARACTER SET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    conn.commit()
    cursor.close()
    conn.close()

init_db()

# ✅ Basic auth decorator
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.username != os.getenv("ADMIN_USER") or auth.password != os.getenv("ADMIN_PASS"):
            return Response(
                'Could not verify your access level.\n'
                'You have to login with proper credentials',
                401,
                {'WWW-Authenticate': 'Basic realm="Login Required"'}
            )
        return f(*args, **kwargs)
    return decorated

@app.route("/")
def home():
    return "✅ Telugu Toxicity Logger Backend is Live!"

@app.route("/log", methods=["POST"])
def log_entry():
    data = request.json
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO logs (comment, transliterated, prediction, confidence) VALUES (%s, %s, %s, %s)",
            (data["comment"], data["transliterated"], data["prediction"], data["confidence"])
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/logs", methods=["GET", "POST"])
@requires_auth
def view_logs():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    # Delete entry
    if request.method == "POST" and "delete_id" in request.form:
        cursor.execute("DELETE FROM logs WHERE id = %s", (request.form["delete_id"],))
        conn.commit()

    # Add new entry
    if request.method == "POST" and "comment" in request.form:
        comment = request.form["comment"]
        transliterated = request.form["transliterated"]
        prediction = request.form["prediction"]
        confidence = request.form["confidence"]
        cursor.execute(
            "INSERT INTO logs (comment, transliterated, prediction, confidence) VALUES (%s, %s, %s, %s)",
            (comment, transliterated, prediction, confidence)
        )
        conn.commit()

    cursor.execute("SELECT * FROM logs")
    logs = cursor.fetchall()
    cursor.close()
    conn.close()

    # Download as CSV
    if request.args.get("download") == "csv":
        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(logs[0].keys())
        for row in logs:
            cw.writerow(row.values())
        return Response(si.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=logs.csv"})

    return render_template_string("""
        <html>
        <head>
            <title>🧾 Telugu Toxicity Admin Logs</title>
            <style>
                body { font-family: Arial; padding: 20px; }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ccc; padding: 10px; text-align: center; }
                th { background-color: #f2f2f2; color: black; }
                input { margin: 5px; padding: 5px; }
                button { padding: 6px 12px; font-weight: bold; }
            </style>
        </head>
        <body>
            <h2>📋 Telugu Toxicity Admin Logs</h2>
            <form method="post">
                <input name="comment" placeholder="Comment">
                <input name="transliterated" placeholder="Transliterated Telugu">
                <input name="prediction" placeholder="Prediction">
                <input name="confidence" placeholder="Confidence">
                <button type="submit">➕ Add Entry</button>
            </form><br>

            <form method="get">
                <button type="submit" name="download" value="csv">⬇️ Download as CSV</button>
            </form><br>

            <p>👉 You can download your full database manually from [https://www.freesqldatabase.com/phpMyAdmin](https://www.freesqldatabase.com/phpMyAdmin)</p>

            <table>
                <tr>
                    <th>ID</th>
                    <th>Comment</th>
                    <th>Translated Text</th>
                    <th>Prediction</th>
                    <th>Confidence (%)</th>
                    <th>Action</th>
                </tr>
                {% for row in logs %}
                <tr>
                    <td>{{ row.id }}</td>
                    <td>{{ row.comment }}</td>
                    <td>{{ row.transliterated }}</td>
                    <td>{{ row.prediction }}</td>
                    <td>{{ row.confidence }}</td>
                    <td>
                        <form method="post" style="display:inline;">
                            <input type="hidden" name="delete_id" value="{{ row.id }}">
                            <button type="submit">🗑️ Delete</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </body>
        </html>
    """, logs=logs)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
