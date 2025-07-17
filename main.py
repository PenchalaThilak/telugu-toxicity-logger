import os
from flask import Flask, request, jsonify, render_template_string, Response
from functools import wraps
import mysql.connector
from datetime import datetime
import csv
from io import StringIO

app = Flask(__name__)

# Load MySQL and Admin credentials from environment variables
db_config = {
    'host': os.environ.get("MYSQL_HOST"),
    'user': os.environ.get("MYSQL_USER"),
    'password': os.environ.get("MYSQL_PASSWORD"),
    'database': os.environ.get("MYSQL_DATABASE"),
    'port': int(os.environ.get("MYSQL_PORT", 3306))
}

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "1234")

# Create the logs table if it doesn't exist
def create_table():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS toxicity_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            comment TEXT,
            translated TEXT,
            prediction VARCHAR(50),
            confidence FLOAT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

create_table()

# Basic auth for admin logs
def check_auth(username, password):
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def authenticate():
    return Response('Login Required', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route("/log", methods=["POST"])
def log_data():
    data = request.json
    comment = data.get("comment", "")
    translated = data.get("translated", "")
    prediction = data.get("prediction", "")
    confidence = float(data.get("confidence", 0))

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO toxicity_logs (comment, translated, prediction, confidence)
        VALUES (%s, %s, %s, %s)
    """, (comment, translated, prediction, confidence))
    conn.commit()
    conn.close()
    return jsonify({"message": "Logged successfully"}), 200

@app.route("/logs")
@requires_auth
def show_logs():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT id, comment, translated, prediction, confidence, timestamp FROM toxicity_logs")
    rows = cursor.fetchall()
    conn.close()

    # Pie chart data
    toxic_count = sum(1 for row in rows if row[3].lower() == "toxic")
    non_toxic_count = len(rows) - toxic_count

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Toxicity Logs</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
        <h2>🧾 Toxicity Log Table</h2>
        <table border="1" cellpadding="8">
            <tr>
                <th>ID</th>
                <th>Comment</th>
                <th>Translated</th>
                <th>Prediction</th>
                <th>Confidence (%)</th>
                <th>Timestamp</th>
                <th>Action</th>
            </tr>
            {% for row in rows %}
            <tr>
                <td>{{row[0]}}</td>
                <td>{{row[1]}}</td>
                <td>{{row[2]}}</td>
                <td>{{row[3]}}</td>
                <td>{{'%.2f'|format(row[4])}}</td>
                <td>{{row[5]}}</td>
                <td><form method="post" action="/delete/{{row[0]}}" style="display:inline;">
                    <button type="submit">Delete</button>
                </form></td>
            </tr>
            {% endfor %}
        </table>
        <br>
        <a href="/download" target="_blank"><button>📥 Download CSV</button></a>

        <h3>📊 Toxicity Pie Chart</h3>
        <canvas id="toxicityChart" width="400" height="400"></canvas>
        <script>
            const ctx = document.getElementById('toxicityChart').getContext('2d');
            new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: ['Toxic', 'Non-Toxic'],
                    datasets: [{
                        label: 'Comments',
                        data: [{{ toxic }}, {{ non_toxic }}],
                        backgroundColor: ['#FF5733', '#28B463']
                    }]
                }
            });
        </script>
    </body>
    </html>
    """
    return render_template_string(html, rows=rows, toxic=toxic_count, non_toxic=non_toxic_count)

@app.route("/delete/<int:log_id>", methods=["POST"])
@requires_auth
def delete_log(log_id):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM toxicity_logs WHERE id = %s", (log_id,))
    conn.commit()
    conn.close()
    return "Deleted! <a href='/logs'>Go back</a>"

@app.route("/download")
@requires_auth
def download_logs():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT id, comment, translated, prediction, confidence, timestamp FROM toxicity_logs")
    rows = cursor.fetchall()
    conn.close()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Comment', 'Translated Text', 'Prediction', 'Confidence (%)', 'Timestamp'])
    for row in rows:
        writer.writerow(row)

    output.seek(0)
    return Response(output, mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=toxicity_logs.csv"})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
