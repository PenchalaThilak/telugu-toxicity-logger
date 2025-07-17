from flask import Flask, request, jsonify, Response
from flask import render_template_string
import mysql.connector
import os
from dotenv import load_dotenv
from functools import wraps

load_dotenv()

app = Flask(__name__)

# Authentication
def check_auth(username, password):
    return username == os.getenv("ADMIN_USER") and password == os.getenv("ADMIN_PASS")

def authenticate():
    return Response(
        "Could not verify your login!\n"
        "Please provide correct credentials", 401,
        {"WWW-Authenticate": 'Basic realm="Login Required"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# MySQL DB Connection
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
        port=int(os.getenv("MYSQL_PORT", 3306))
    )

# Home route
@app.route("/")
def home():
    return "✅ Telugu Toxicity Logger is Live!"

# Add log entry
@app.route("/log", methods=["POST"])
def add_log():
    data = request.get_json()
    comment = data.get("comment", "")
    transliterated = data.get("transliterated", "")
    prediction = data.get("prediction", "")
    confidence = data.get("confidence", 0.0)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS logs (id INT AUTO_INCREMENT PRIMARY KEY, comment TEXT, transliterated TEXT, prediction VARCHAR(20), confidence FLOAT)"
        )
        cursor.execute(
            "INSERT INTO logs (comment, transliterated, prediction, confidence) VALUES (%s, %s, %s, %s)",
            (comment, transliterated, prediction, confidence)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Log entry added successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# View logs (requires login)
@app.route("/logs", methods=["GET"])
@requires_auth
def view_logs():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM logs")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Admin Logs</title>
            <style>
                table { width: 100%%; border-collapse: collapse; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #333; color: white; }
                tr:nth-child(even) { background-color: #f2f2f2; }
            </style>
        </head>
        <body>
            <h2>🧾 Telugu Toxicity Admin Logs</h2>
            <table>
                <tr><th>ID</th><th>Comment</th><th>Transliterated</th><th>Prediction</th><th>Confidence (%)</th></tr>
                {% for row in rows %}
                <tr>
                    <td>{{ row[0] }}</td>
                    <td>{{ row[1] }}</td>
                    <td>{{ row[2] }}</td>
                    <td>{{ row[3] }}</td>
                    <td>{{ "%.2f" | format(row[4]) }}</td>
                </tr>
                {% endfor %}
            </table>
        </body>
        </html>
        """
        return render_template_string(html, rows=rows)
    except Exception as e:
        return f"<h3>Error loading logs: {str(e)}</h3>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
