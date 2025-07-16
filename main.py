from flask import Flask, request, jsonify, render_template_string, redirect, Response
import sqlite3
import os

app = Flask(__name__)
DB_PATH = "toxicity_logs.db"

# ✅ Initialize database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            comment TEXT,
            transliterated TEXT,
            prediction TEXT,
            confidence REAL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def home():
    return "✅ Toxicity Logger API on Render is Running!"

# ✅ Log route (fixes the order of values)
@app.route("/log", methods=["POST"])
def log_comment():
    data = request.json
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO comments (comment, transliterated, prediction, confidence)
            VALUES (?, ?, ?, ?)
        ''', (
            data["comment"],             # ✅ Raw user input (e.g., arrey pichi vedhava)
            data["transliterated"],      # ✅ Translated Telugu (e.g., అర్రే పిచ్చి వెధవ)
            data["prediction"],
            data["confidence"]
        ))
        conn.commit()
        conn.close()
        return jsonify({"message": "Logged ✅"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ View table
@app.route("/logs")
def view_logs():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM comments")
    rows = c.fetchall()
    conn.close()

    html = """
    <h2>🧾 Telugu Toxicity Detection Logs</h2>
    <table border="1" cellpadding="5">
        <tr><th>ID</th><th>Comment</th><th>Translated</th><th>Prediction</th><th>Confidence (%)</th><th>Delete</th></tr>
        {% for row in rows %}
        <tr>
            <td>{{ row[0] }}</td>
            <td>{{ row[1] }}</td>
            <td>{{ row[2] }}</td>
            <td>{{ row[3] }}</td>
            <td>{{ '%.2f'|format(row[4]) }}</td>
            <td><a href="/delete/{{ row[0] }}">❌ Delete</a></td>
        </tr>
        {% endfor %}
    </table>
    <br><a href="/add">➕ Add New Entry</a> | <a href="/download_csv">⬇️ Download CSV</a>
    """
    return render_template_string(html, rows=rows)

# ✅ Add manual entry
@app.route("/add", methods=["GET", "POST"])
def add_record():
    if request.method == "POST":
        comment = request.form["comment"]
        transliterated = request.form["transliterated"]
        prediction = request.form["prediction"]
        confidence = float(request.form["confidence"])

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO comments (comment, transliterated, prediction, confidence)
            VALUES (?, ?, ?, ?)
        ''', (comment, transliterated, prediction, confidence))
        conn.commit()
        conn.close()
        return redirect("/logs")

    html = """
    <h3>➕ Add New Log Entry</h3>
    <form method="post">
        Comment: <input name="comment" required><br><br>
        Transliterated: <input name="transliterated" required><br><br>
        Prediction: 
        <select name="prediction">
            <option value="Toxic">Toxic</option>
            <option value="Non-Toxic">Non-Toxic</option>
        </select><br><br>
        Confidence (%): <input name="confidence" type="number" step="0.01" required><br><br>
        <button type="submit">Save</button>
    </form>
    <br><a href="/logs">🔙 Back to Logs</a>
    """
    return render_template_string(html)

# ✅ Delete record
@app.route("/delete/<int:log_id>")
def delete_record(log_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM comments WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()
    return redirect("/logs")

# ✅ Download logs as CSV
@app.route("/download_csv")
def download_csv():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, comment, transliterated, prediction, confidence FROM comments")
    rows = c.fetchall()
    conn.close()

    csv_data = "ID,Comment,Transliterated,Prediction,Confidence (%)\n"
    for row in rows:
        csv_data += f"{row[0]},\"{row[1]}\",\"{row[2]}\",{row[3]},{row[4]:.2f}\n"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=toxicity_logs.csv"}
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
