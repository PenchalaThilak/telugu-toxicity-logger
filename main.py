from flask import Flask, request, jsonify, render_template_string, Response, send_file
import mysql.connector
import os
from dotenv import load_dotenv
from functools import wraps
import csv
from io import StringIO
import subprocess

load_dotenv()

app = Flask(__name__)

# DB Config
db_config = {
    'host': os.getenv("MYSQL_HOST"),
    'user': os.getenv("MYSQL_USER"),
    'password': os.getenv("MYSQL_PASSWORD"),
    'database': os.getenv("MYSQL_DATABASE"),
    'port': int(os.getenv("MYSQL_PORT", 3306))
}

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

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import request, Response
        auth = request.authorization
        if not auth or auth.username != os.getenv("ADMIN_USER") or auth.password != os.getenv("ADMIN_PASS"):
            return Response('Login required', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})
        return f(*args, **kwargs)
    return decorated

@app.route("/")
def home():
    return "✅ Telugu Toxicity Logger is Running!"

@app.route("/log", methods=["POST"])
def log_entry():
    data = request.json
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO logs (comment, transliterated, prediction, confidence) VALUES (%s, %s, %s, %s)",
            (data.get("comment", ""), data.get("transliterated", ""), data.get("prediction", ""), data.get("confidence", 0))
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

    if request.method == "POST":
        if "delete_id" in request.form:
            cursor.execute("DELETE FROM logs WHERE id = %s", (request.form["delete_id"],))
            conn.commit()
        elif "comment" in request.form and request.form["comment"].strip():
            comment = request.form["comment"]
            transliterated = request.form.get("transliterated", "")
            prediction = request.form.get("prediction", "")
            confidence = float(request.form.get("confidence", 0))
            cursor.execute(
                "INSERT INTO logs (comment, transliterated, prediction, confidence) VALUES (%s, %s, %s, %s)",
                (comment, transliterated, prediction, confidence)
            )
            conn.commit()

    cursor.execute("SELECT * FROM logs")
    logs = cursor.fetchall()
    cursor.close()
    conn.close()

    if request.args.get("download") == "csv":
        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(logs[0].keys() if logs else ["ID", "Comment", "Transliterated", "Prediction", "Confidence"])
        for row in logs:
            cw.writerow(row.values())
        return Response(si.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=logs.csv"})

    return render_template_string("""
        <html>
        <head>
            <title>Telugu Toxicity Admin Logs</title>
            <style>
                body { font-family: Arial; margin: 40px; }
                table { border-collapse: collapse; width: 100%; margin-top: 20px; }
                th, td { border: 1px solid #ccc; padding: 10px; text-align: center; }
                th { background-color: #f2f2f2; color: black; }
                input { margin-right: 10px; padding: 5px; }
                button { padding: 5px 10px; }
            </style>
        </head>
        <body>
            <h2>📄 Telugu Toxicity Admin Logs</h2>

            <table>
                <tr>
                    <th>ID</th>
                    <th>Comment</th>
                    <th>Transliterated</th>
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
                    <td>{{ "%.4f"|format(row.confidence) }}</td>
                    <td>
                        <form method="post" style="display:inline;">
                            <input type="hidden" name="delete_id" value="{{ row.id }}">
                            <button type="submit">🗑️</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </table>

            <br><br>
            <form method="post">
                <input name="comment" placeholder="Comment" required>
                <input name="transliterated" placeholder="Transliterated">
                <input name="prediction" placeholder="Prediction">
                <input name="confidence" placeholder="Confidence">
                <button type="submit">➕ Add Entry</button>
            </form>

            <br>
            <form method="get">
                <button type="submit" name="download" value="csv">⬇️ Download CSV</button>
            </form>

            <br>
            <form action="/dump" method="get">
                <button type="submit">🧩 Download MySQL Dump (.sql)</button>
            </form>
        </body>
        </html>
    """, logs=logs)

@app.route("/dump")
@requires_auth
def dump_sql():
    dump_file = "/tmp/db_dump.sql"
    cmd = f"mysqldump -h {db_config['host']} -u {db_config['user']} -p{db_config['password']} {db_config['database']} > {dump_file}"
    exit_code = os.system(cmd)
    if exit_code == 0:
        return send_file(dump_file, as_attachment=True)
    return "Error creating dump", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
