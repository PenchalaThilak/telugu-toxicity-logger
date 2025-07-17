import os
from flask import Flask, request, jsonify, Response
import mysql.connector
from datetime import datetime
from dotenv import load_dotenv
from functools import wraps

load_dotenv()

app = Flask(__name__)

# MySQL config from environment variables
db_config = {
    'host': os.getenv("MYSQL_HOST"),
    'port': int(os.getenv("MYSQL_PORT")),
    'user': os.getenv("MYSQL_USER"),
    'password': os.getenv("MYSQL_PASSWORD"),
    'database': os.getenv("MYSQL_DATABASE")
}

# Create table if it doesn't exist
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
            timestamp DATETIME
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

create_table()

# Basic auth for admin
def check_auth(username, password):
    return username == os.getenv("ADMIN_USERNAME") and password == os.getenv("ADMIN_PASSWORD")

def authenticate():
    return Response(
        'Could not verify your access.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# Route to log comment
@app.route('/log', methods=['POST'])
def log_comment():
    data = request.get_json()
    comment = data.get('comment')
    translated = data.get('translated')
    prediction = data.get('prediction')
    confidence = data.get('confidence')

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute("""
        INSERT INTO toxicity_logs (comment, translated, prediction, confidence, timestamp)
        VALUES (%s, %s, %s, %s, %s)
    """, (comment, translated, prediction, confidence, timestamp))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'status': 'success'}), 200

# Admin view of all logs
@app.route('/logs', methods=['GET'])
@requires_auth
def view_logs():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM toxicity_logs")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    html = """
    <html>
    <head><title>Admin Log View</title></head>
    <body>
    <h2>Toxicity Logs</h2>
    <table border='1'>
        <tr>
            <th>ID</th>
            <th>Comment</th>
            <th>Translated</th>
            <th>Prediction</th>
            <th>Confidence (%)</th>
            <th>Timestamp</th>
        </tr>
    """
    for row in rows:
        html += "<tr>" + "".join(f"<td>{str(cell)}</td>" for cell in row) + "</tr>"
    html += "</table></body></html>"
    return html

if __name__ == '__main__':
    app.run(debug=True)
