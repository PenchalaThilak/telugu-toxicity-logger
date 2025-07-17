import os
import mysql.connector
from flask import Flask, request, jsonify, render_template_string, send_file, redirect
from datetime import datetime
import csv
import io

app = Flask(__name__)

# MySQL config from environment variables
db_config = {
    "host": os.environ.get("MYSQL_HOST"),
    "user": os.environ.get("MYSQL_USER"),
    "password": os.environ.get("MYSQL_PASSWORD"),
    "database": os.environ.get("MYSQL_DATABASE"),
    "port": int(os.environ.get("MYSQL_PORT", 3306))
}

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

# Create table if it doesn't exist
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
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

create_table()

# Save a new comment entry
@app.route('/log', methods=['POST'])
def log_entry():
    data = request.json
    comment = data.get("comment")
    translated = data.get("translated")
    prediction = data.get("prediction")
    confidence = float(data.get("confidence", 0))

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO toxicity_logs (comment, translated, prediction, confidence)
        VALUES (%s, %s, %s, %s)
    """, (comment, translated, prediction, confidence))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"}), 200

# View logs (protected)
@app.route('/logs', methods=['GET'])
def view_logs():
    password = request.args.get("password", "")
    if password != ADMIN_PASSWORD:
        return redirect("/unauthorized")

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM toxicity_logs ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()

    html = """
    <h2 style="text-align:center;">Telugu Toxicity Logs</h2>
    <p style="text-align:center;"><a href='/download-csv?password={{password}}'>📥 Download as CSV</a></p>
    <table border="1" style="width:100%;border-collapse:collapse;text-align:center;">
    <tr><th>ID</th><th>Comment</th><th>Translated</th><th>Prediction</th><th>Confidence (%)</th><th>Timestamp</th></tr>
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
    return render_template_string(html, rows=rows, password=password)

@app.route('/unauthorized')
def unauthorized():
    return "<h3>Unauthorized. Add ?password=yourpass to URL.</h3>"

# Download CSV of logs
@app.route('/download-csv')
def download_csv():
    password = request.args.get("password", "")
    if password != ADMIN_PASSWORD:
        return redirect("/unauthorized")

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM toxicity_logs ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Comment', 'Translated', 'Prediction', 'Confidence', 'Timestamp'])
    for row in rows:
        writer.writerow(row)

    output.seek(0)
    return send_file(io.BytesIO(output.read().encode()), download_name="toxicity_logs.csv", as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
