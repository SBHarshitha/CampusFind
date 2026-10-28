from flask import Flask, request
from streamlit import image
from werkzeug.utils import secure_filename
import sqlite3
import os

app = Flask(__name__)

app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def init_db():
    conn = sqlite3.connect("campusfind.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT NOT NULL,
            category TEXT NOT NULL,
            location TEXT NOT NULL,
            status TEXT NOT NULL,
image TEXT
        )
    """)
    cursor = conn.execute("PRAGMA table_info(reports)")
    columns = [column[1] for column in cursor.fetchall()]

    if "image" not in columns:
            conn.execute("ALTER TABLE reports ADD COLUMN image TEXT")
    conn.commit()
    conn.close()


def get_reports(search="", status="All"):
    conn = sqlite3.connect("campusfind.db")
    cursor = conn.cursor()

    query = """
        SELECT id, item, category, location, status
        FROM reports
        WHERE (item LIKE ? OR category LIKE ? OR location LIKE ?)
    """
    keyword = f"%{search}%"
    params = [keyword, keyword, keyword]

    if status in ["Lost", "Found"]:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY id DESC"

    cursor.execute(query, params)
    reports = cursor.fetchall()
    conn.close()

    return reports


init_db()


@app.route("/", methods=["GET", "POST"])
def home():
    message = ""

    if request.method == "POST":
        item = request.form.get("item", "").strip()
        category = request.form.get("category", "").strip()
        location = request.form.get("location", "").strip()
        status = request.form.get("status", "")
        image = request.files.get("image")
        image_filename = ""

        if image and image.filename:
            image_filename = secure_filename(image.filename)
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], image_filename))
        if item and category and location and status in ["Lost", "Found"]:
            conn = sqlite3.connect("campusfind.db")
            conn.execute(
                    """
                    INSERT INTO reports
                    (item, category, location, status, image)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (item, category, location, status, image_filename)
                )
            conn.commit()
            conn.close()

            message = "Report saved successfully!"

    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "All")
    reports = get_reports(search, status_filter)

    report_html = ""

    for report in reports:
        image_html = ""
        if report[5]:
          image_html = f'<img src="/uploads/{report[5]}" width="150" alt="Item photo">'
        report_html += f"""
        <div>
            <h3>{report[1]}</h3>
            <p>Category: {report[2]}</p>
            <p>Location: {report[3]}</p>
            <p>Status: {report[4]}</p>
            <hr>
        </div>
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
    <title>CampusFind</title>

    <link rel="stylesheet"
      href="/static/style.css">
</head>
    <body><
        <h1>🎓 CampusFind</h1>
        <h2>Lost something? Let's help you find it!</h2>

        <h2>Submit a Report</h2>

        <form method="POST" enctype="multipart/form-data">
            <label>Item Name:</label><br>
            <input type="text" name="item" required><br><br>

            <label>Category:</label><br>
            <input type="text" name="category" required><br><br>

            <label>Location:</label><br>
            <input type="text" name="location" required><br><br>

            <label>Report Type:</label><br>
            <select name="status">
                <option value="Lost">Lost</option>
                <option value="Found">Found</option>
            </select><br><br>
            <label>Upload Item Photo:</label>
<input type="file" name="image" accept="image/*">

            <button type="submit">Submit Report</button>
        </form>

        <p>{message}</p>

        <h2>Search Reports</h2>

        <h2>Search and Filter Reports</h2>

<form method="GET">
    <input
        type="text"
        name="search"
        placeholder="Search item, category, or location"
        value="{search}"
    >

    <select name="status">
        <option value="All" {"selected" if status_filter == "All" else ""}>All Items</option>
        <option value="Lost" {"selected" if status_filter == "Lost" else ""}>Lost Only</option>
        <option value="Found" {"selected" if status_filter == "Found" else ""}>Found Only</option>
    </select>

    <button type="submit">Search</button>
    <a href="/">Show All</a>
</form>

        <h2>Lost and Found Reports</h2>

        {report_html if report_html else "<p>No matching reports found.</p>"}

    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(debug=True)