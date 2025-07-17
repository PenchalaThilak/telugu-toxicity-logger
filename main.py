from flask import Flask, request, jsonify, render_template_string, send_file, redirect
import mysql.connector
from io import StringIO
import csv
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)

# MySQL config from environment variables
db_config = {
    "host": os.environ.get("MYSQL_HOST"),
    "port": int(os.environ.get("MYSQL_PORT", 3306)),
    "user": os.environ.get("MYSQL_USER"),
    "password": os.environ.get("MYSQL_PASSWORD"),
    "database": os.environ.get("MYSQL_DATABASE")
}

# Admin credentials
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "adminpass")


def create_table():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS toxicity_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            comment TEXT,
            translated TEXT,
            prediction VARCHAR(20),
            confidence FLOAT,
            timestamp DATETIME
        )
    """)
    conn.commit()
    conn.close()

create_table()


def check_auth(username, password):
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def authenticate():
    from flask import Response
    return Response(
        "You must login with proper credentials", 401,
        {"WWW-Authenticate": 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import request
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


@app.route("/")
def home():
    return "Welcome to Telugu Toxicity Logger API!"


@app.route("/log", methods=["POST"])
def log_entry():
    data = request.json
    comment = data.get("comment")
    translated = data.get("translated")
    prediction = data.get("prediction")
    confidence = float(data.get("confidence", 0))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO toxicity_logs (comment, translated, prediction, confidence, timestamp)
        VALUES (%s, %s, %s, %s, %s)
    """, (comment, translated, prediction, confidence, timestamp))
    conn.commit()
    conn.close()

    return jsonify({"status": "success"}), 200


@app.route("/logs", methods=["GET"])
@requires_auth
def show_logs():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT id, comment, translated, prediction, confidence, timestamp FROM toxicity_logs ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    table_html = """
    <h2>🧠 Telugu Toxicity Logs (Admin Panel)</h2>
    <a href="/download_csv">⬇️ Download as CSV</a> |
    <a href="/delete_all" onclick="return confirm('Are you sure you want to delete all logs?')">🗑️ Delete All</a>
    <table border="1" cellspacing="0" cellpadding="5">
        <tr>
            <th>ID</th>
            <th>Comment</th>
            <th>Translated</th>
            <th>Prediction</th>
            <th>Confidence (%)</th>
            <th>Timestamp</th>
        </tr>
        {% for row in rows %}
        <tr>
            <td>{{ row[0] }}</td>
            <td>{{ row[1] }}</td>
            <td>{{ row[2] }}</td>
            <td>{{ row[3] }}</td>
            <td>{{ "%.2f"|format(row[4]) }}</td>
            <td>{{ row[5] }}</td>
        </tr>
        {% endfor %}
    </table>
    """
    return render_template_string(table_html, rows=rows)


@app.route("/download_csv")
@requires_auth
def download_csv():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT id, comment, translated, prediction, confidence, timestamp FROM toxicity_logs")
    rows = cursor.fetchall()
    conn.close()

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(["ID", "Comment", "Translated", "Prediction", "Confidence", "Timestamp"])
    cw.writerows(rows)
    si.seek(0)

    return send_file(
        StringIO(si.read()),
        mimetype="text/csv",
        download_name="toxicity_logs.csv",
        as_attachment=True
    )


@app.route("/delete_all")
@requires_auth
def delete_all_logs():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM toxicity_logs")
    conn.commit()
    conn.close()
    return redirect("/logs")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
