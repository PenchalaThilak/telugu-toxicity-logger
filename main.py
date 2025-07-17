from flask import Flask, request, jsonify, render_template_string, redirect, url_for, send_file
import mysql.connector
import os
from datetime import datetime
import csv
from io import StringIO

app = Flask(__name__)

# MySQL DB connection (values from Render env)
db_config = {
    'host': os.environ.get('MYSQL_HOST'),
    'port': int(os.environ.get('MYSQL_PORT', 3306)),
    'user': os.environ.get('MYSQL_USER'),
    'password': os.environ.get('MYSQL_PASSWORD'),
    'database': os.environ.get('MYSQL_DATABASE')
}

# Ensure table exists
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

# API to receive data from Hugging Face
@app.route('/add_log', methods=['POST'])
def add_log():
    data = request.json
    comment = data.get("comment")
    translated = data.get("translated")
    prediction = data.get("prediction")
    confidence = data.get("confidence")
    timestamp = datetime.now()

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO toxicity_logs (comment, translated, prediction, confidence, timestamp)
        VALUES (%s, %s, %s, %s, %s)
    """, (comment, translated, prediction, confidence, timestamp))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"}), 200

# Admin dashboard with table and pie chart
@app.route('/logs')
def view_logs():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM toxicity_logs ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    # Count for pie chart
    toxic = sum(1 for row in rows if row['prediction'] == 'Toxic')
    nontoxic = sum(1 for row in rows if row['prediction'] == 'Non-Toxic')

    html = """
    <html>
    <head>
        <title>Toxicity Logs</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
        <h2>Toxicity Logs (MySQL)</h2>
        <a href="/download_csv">Download CSV</a>
        <table border="1" cellspacing="0" cellpadding="5">
            <tr><th>ID</th><th>Comment</th><th>Translated</th><th>Prediction</th><th>Confidence (%)</th><th>Timestamp</th><th>Delete</th></tr>
            {% for row in rows %}
            <tr>
                <td>{{ row.id }}</td>
                <td>{{ row.comment }}</td>
                <td>{{ row.translated }}</td>
                <td>{{ row.prediction }}</td>
                <td>{{ "%.2f"|format(row.confidence) }}</td>
                <td>{{ row.timestamp }}</td>
                <td><a href="{{ url_for('delete_log', log_id=row.id) }}">Delete</a></td>
            </tr>
            {% endfor %}
        </table>
        <h3>Prediction Summary</h3>
        <canvas id="chart" width="300" height="300"></canvas>
        <script>
        const ctx = document.getElementById('chart').getContext('2d');
        new Chart(ctx, {
            type: 'pie',
            data: {
                labels: ['Toxic', 'Non-Toxic'],
                datasets: [{
                    label: 'Prediction Distribution',
                    data: [{{ toxic }}, {{ nontoxic }}],
                    backgroundColor: ['#e74c3c', '#2ecc71']
                }]
            }
        });
        </script>
    </body>
    </html>
    """
    return render_template_string(html, rows=rows, toxic=toxic, nontoxic=nontoxic)

# Delete log
@app.route('/delete/<int:log_id>')
def delete_log(log_id):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM toxicity_logs WHERE id = %s", (log_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('view_logs'))

# Download CSV
@app.route('/download_csv')
def download_csv():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM toxicity_logs ORDER BY id DESC")
    rows = cursor.fetchall()
    headers = [i[0] for i in cursor.description]
    conn.close()

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(headers)
    writer.writerows(rows)
    output = si.getvalue()

    return send_file(
        StringIO(output),
        mimetype='text/csv',
        download_name='toxicity_logs.csv',
        as_attachment=True
    )

@app.route('/')
def index():
    return "✅ Telugu Toxicity Logger Flask API (MySQL Connected)"

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8000)
