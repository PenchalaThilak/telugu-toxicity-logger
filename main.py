from flask import Flask, request, jsonify, render_template_string, Response
from dotenv import load_dotenv
import os
import mysql.connector
from functools import wraps

load_dotenv()

app = Flask(__name__)

# ✅ Connect to MySQL
db = mysql.connector.connect(
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DATABASE"),
    port=int(os.getenv("MYSQL_PORT"))
)
cursor = db.cursor()

# ✅ Create logs table if it doesn't exist
cursor.execute("""
    CREATE TABLE IF NOT EXISTS toxicity_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        comment TEXT NOT NULL,
        transliterated TEXT,
        prediction VARCHAR(20),
        confidence FLOAT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
db.commit()

# ✅ Basic Auth for admin logs view
def check_auth(username, password):
    return username == os.getenv("ADMIN_USERNAME") and password == os.getenv("ADMIN_PASSWORD")

def authenticate():
    return Response('Could not verify your access level.\nLogin required.', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# ✅ API endpoint to receive data from Hugging Face app
@app.route('/log', methods=['POST'])
def log_data():
    try:
        data = request.get_json()
        comment = data.get("comment", "")
        transliterated = data.get("transliterated", "")
        prediction = data.get("prediction", "")
        confidence = float(data.get("confidence", 0.0))

        cursor.execute("""
            INSERT INTO toxicity_logs (comment, transliterated, prediction, confidence)
            VALUES (%s, %s, %s, %s)
        """, (comment, transliterated, prediction, confidence))
        db.commit()
        return jsonify({"message": "Log saved successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ Admin logs interface
@app.route('/logs')
@requires_auth
def view_logs():
    cursor.execute("SELECT id, comment, transliterated, prediction, confidence, timestamp FROM toxicity_logs ORDER BY id DESC")
    logs = cursor.fetchall()

    cursor.execute("SELECT prediction, COUNT(*) FROM toxicity_logs GROUP BY prediction")
    pie_data = cursor.fetchall()

    html = """
    <html>
        <head>
            <title>Toxicity Logs</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        </head>
        <body>
            <h2>📋 Telugu Toxicity Logs</h2>
            <canvas id="chart" width="400" height="200"></canvas>
            <script>
                const ctx = document.getElementById('chart');
                new Chart(ctx, {
                    type: 'pie',
                    data: {
                        labels: {{ labels }},
                        datasets: [{
                            label: 'Prediction Count',
                            data: {{ counts }},
                            backgroundColor: ['#ff6384','#36a2eb','#cc65fe','#ffce56']
                        }]
                    }
                });
            </script>
            <table border="1" cellpadding="6" cellspacing="0">
                <tr>
                    <th>ID</th><th>Comment</th><th>Telugu</th><th>Prediction</th><th>Confidence</th><th>Timestamp</th>
                </tr>
                {% for row in logs %}
                <tr>
                    <td>{{ row[0] }}</td>
                    <td>{{ row[1] }}</td>
                    <td>{{ row[2] }}</td>
                    <td>{{ row[3] }}</td>
                    <td>{{ "%.2f" % row[4] }}</td>
                    <td>{{ row[5] }}</td>
                </tr>
                {% endfor %}
            </table>
        </body>
    </html>
    """
    labels = [r[0] for r in pie_data]
    counts = [r[1] for r in pie_data]
    return render_template_string(html, logs=logs, labels=labels, counts=counts)

# ✅ Home route
@app.route('/')
def home():
    return "✅ Telugu Toxicity Logger Backend is Running"

# ✅ Required for Render
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
