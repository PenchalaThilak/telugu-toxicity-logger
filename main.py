from flask import Flask, request, jsonify, render_template_string, Response
from dotenv import load_dotenv
import mysql.connector
import os
from functools import wraps

load_dotenv()

app = Flask(__name__)

# Database connection
db = mysql.connector.connect(
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DATABASE"),
    port=int(os.getenv("MYSQL_PORT", 3306))
)
cursor = db.cursor()

# Create table if not exists
def create_table():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS toxicity_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            comment TEXT NOT NULL,
            transliterated TEXT,
            prediction VARCHAR(50),
            confidence FLOAT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.commit()

create_table()

# Basic Auth for logs view
def check_auth(username, password):
    return username == os.getenv("ADMIN_USERNAME") and password == os.getenv("ADMIN_PASSWORD")

def authenticate():
    return Response("Authentication required", 401, {"WWW-Authenticate": 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# API to receive logs
@app.route('/log', methods=['POST'])
def log_data():
    data = request.get_json()
    comment = data.get("comment")
    transliterated = data.get("transliterated")
    prediction = data.get("prediction")
    confidence = data.get("confidence")

    cursor.execute("""
        INSERT INTO toxicity_logs (comment, transliterated, prediction, confidence)
        VALUES (%s, %s, %s, %s)
    """, (comment, transliterated, prediction, confidence))
    db.commit()

    return jsonify({"status": "success"}), 200

# Admin dashboard
@app.route('/logs')
@requires_auth
def view_logs():
    cursor.execute("SELECT id, comment, transliterated, prediction, confidence, timestamp FROM toxicity_logs ORDER BY timestamp DESC")
    rows = cursor.fetchall()

    cursor.execute("SELECT prediction, COUNT(*) FROM toxicity_logs GROUP BY prediction")
    pie_data = cursor.fetchall()

    html_template = """
    <html>
        <head>
            <title>Toxicity Logs</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        </head>
        <body>
            <h2 style="text-align:center;">🧾 Telugu Toxicity Logs</h2>
            <canvas id="pieChart" width="400" height="200"></canvas>
            <script>
                const data = {
                    labels: {{ labels }},
                    datasets: [{
                        label: 'Prediction Distribution',
                        data: {{ counts }},
                        backgroundColor: ['#ff6384', '#36a2eb', '#ffce56', '#2ecc71', '#8e44ad']
                    }]
                };
                new Chart(document.getElementById('pieChart'), {
                    type: 'pie',
                    data: data
                });
            </script>
            <table border="1" cellpadding="6" style="margin-top:20px; width:100%;">
                <tr>
                    <th>ID</th><th>Comment</th><th>Translated Text</th><th>Prediction</th><th>Confidence (%)</th><th>Timestamp</th>
                </tr>
                {% for row in rows %}
                <tr>
                    <td>{{ row[0] }}</td>
                    <td>{{ row[1] }}</td>
                    <td>{{ row[2] }}</td>
                    <td>{{ row[3] }}</td>
                    <td>{{ "%.2f" | format(row[4]) }}</td>
                    <td>{{ row[5] }}</td>
                </tr>
                {% endfor %}
            </table>
        </body>
    </html>
    """
    labels = [row[0] for row in pie_data]
    counts = [row[1] for row in pie_data]
    return render_template_string(html_template, rows=rows, labels=labels, counts=counts)

# Health check
@app.route('/')
def home():
    return "✅ Telugu Toxicity Logger Backend is Running!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
